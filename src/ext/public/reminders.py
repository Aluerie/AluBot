# Copyright (C) 2020-present, Irene Adler 💜 (@Aluerie).
# Licensed under MPL-2.0, see the LICENSE file for details.
"""Reminders.

* ``/remind set`` (the autocomplete shows how the time is understood), one-off or repeating ("every friday 18:00"),
  in the channel or in DMs; the confirmation has buttons to edit or delete it.
* "Remind me about this" in the message context menu reminds about that message.
* The reminder arrives as a reply to the message it was set from, says if it's late, and has buttons to snooze it;
  repeating ones also to skip the next time, pause or stop. Reminders missed while the bot was offline arrive
  as one message per person and channel. All buttons keep working after restarts.
* ``/remind list`` shows your reminders with a delete (or resume) button each and an edit menu.
* ``/timestamp`` turns a time into Discord timestamps; "Convert times" in the message context menu finds the times
  in a message ("18:00 MSK", "3pm EST") and shows them in everybody's own timezone.
"""

from __future__ import annotations

import asyncio
import collections
import datetime as dt
import enum
import re
import textwrap
from typing import TYPE_CHECKING, Any, Final, NotRequired, Self, TypedDict, override

import discord
from discord import app_commands, ui
from loguru import logger

from core import Cog, LayoutView, Modal
from shared import clock, errors, scheduler
from shared.scheduler import UTC, Job, WallTime, recurrence, to_wall_time
from shared.timeparse import ParsedTime, describe_rule, parse_time
from utils import const, prompts
lazy from utils.times import TimeTransformer

if TYPE_CHECKING:
    from core import Bot, Interaction

__all__ = ("Reminders",)


KIND: Final = "reminder"
MAX_TEXT_LENGTH: Final = 1500
MAX_LIST_TEXT_LENGTH: Final = 120
"""Reminder texts are shortened to this in lists."""
MAX_REMINDERS_PER_USER: Final = 50
"""Limit for everyone but the bot owner."""
LATE_AFTER: Final = dt.timedelta(minutes=5)
"""Reminders later than this say so (e.g. the bot was offline at the time), and are bundled with other late ones."""
DEFAULT_TEXT: Final = "…"
REMINDERS_PER_PAGE: Final = 8
"""Reminders per page of `/remind list`: a layout holds 40 components, and a reminder takes 3."""
SNOOZE_PRESETS: Final = (("10m", "10 min"), ("1h", "1 hour"), ("1d", "1 day"))
MAX_CONVERTED_TIMES: Final = 10
MAX_BUNDLE_LENGTH: Final = 4000


class ReminderData(TypedDict, closed=True):
    """Data of a reminder job; its author is the job's `user_id`."""

    text: str
    channel_id: int
    message_id: int | None
    """The message the reminder replies to when it arrives."""
    dm: NotRequired[bool]
    """Deliver it in the author's DMs instead of the channel."""


class Repeat(enum.Enum):
    """Repeat presets for `/remind set`; the values are RRULEs evaluated on the author's clocks.

    Any other repeat can be typed in `when`: "every friday 18:00", "every 2 weeks on monday".
    """

    never = "never"  # Discord needs non-empty choice values
    daily = "FREQ=DAILY"
    weekdays = "FREQ=WEEKLY;BYDAY=MO,TU,WE,TH,FR"
    weekly = "FREQ=WEEKLY"
    monthly = "FREQ=MONTHLY"
    yearly = "FREQ=YEARLY"

    @property
    def rule(self) -> str | None:
        """The RRULE, or `None` for `never`."""
        return None if self is Repeat.never else self.value


def repeat_label(rule: str | None) -> str:
    """Describe a reminder's repeat for users: "🔁 every Mon and Thu", or nothing for one-off reminders."""
    return "" if rule is None else f"🔁 {describe_rule(rule)}"


def message_url(guild_id: int | None, channel_id: int, message_id: int) -> str:
    """Make a link to a message; DM messages live under "@me"."""
    return f"https://discord.com/channels/{guild_id or '@me'}/{channel_id}/{message_id}"


def shorten(text: str, width: int = MAX_LIST_TEXT_LENGTH) -> str:
    """Shorten the text of a reminder to one line."""
    return textwrap.shorten(text, width=width, placeholder="…") or DEFAULT_TEXT


async def user_timezone(interaction: Interaction) -> str | None:
    """Get the timezone that the user has set with ``/timezone set``, if any."""
    return await interaction.client.tz_manager.get_timezone(interaction.user.id)


def next_after_skip(job: Job[ReminderData]) -> WallTime | None:
    """Find the occurrence after the next one of a repeating reminder, on its clocks; `None` if there is none."""
    if job.rule is None:
        return None
    local = recurrence.next_occurrence(job.rule, current=job.when.local, after=job.when.local)
    return None if local is None else WallTime(local, job.when.timezone)


# --- BUTTONS ----------------------------------------------------------------------------------------------------------
# Dynamic items: their state lives in the `custom_id`, so they keep working after the bot restarts.


class ReminderButton(discord.ui.DynamicItem[discord.ui.Button[Any]], template=r"$^"):
    """Base for the reminder buttons: answers `BadUserInputError`s to the user instead of failing silently.

    The subclasses' custom IDs are ``reminder:<action>:<job_id>:<author_id>`` (snoozes: ``<duration>`` for the job).
    """

    def __init__(
        self,
        action: str,
        target: int | str,
        author_id: int,
        *,
        label: str,
        emoji: str,
        style: discord.ButtonStyle = discord.ButtonStyle.secondary,
    ) -> None:
        custom_id = f"reminder:{action}:{target}:{author_id}"
        super().__init__(discord.ui.Button(label=label, emoji=emoji, style=style, custom_id=custom_id))
        self.author_id: int = author_id

    async def run(self, interaction: Interaction) -> None:
        """Run the button's action."""
        raise NotImplementedError

    @override
    async def callback(self, interaction: Interaction) -> None:
        if interaction.user.id != self.author_id:
            await interaction.response.send_message("This is not your reminder.", ephemeral=True)
            return
        try:
            await self.run(interaction)
        except errors.BadUserInputError as exc:
            if interaction.response.is_done():
                await interaction.followup.send(str(exc), ephemeral=True)
            else:
                await interaction.response.send_message(str(exc), ephemeral=True)

    @staticmethod
    async def get_job(interaction: Interaction, job_id: int, author_id: int) -> Job[ReminderData]:
        """Get the author's reminder, or explain that it's over."""
        job: Job[ReminderData] | None = await interaction.client.scheduler.get(job_id, kind=KIND, user_id=author_id)
        if job is None:
            msg = "This reminder is already over."
            raise errors.BadUserInputError(msg)
        return job


class JobButton(ReminderButton, template=r"$^"):
    """A reminder button about one job: its ID is in the custom ID."""

    action: str = ""
    label: str = ""
    emoji: str = ""
    style: discord.ButtonStyle = discord.ButtonStyle.secondary

    def __init__(self, job_id: int, author_id: int, *, label: str | None = None, emoji: str | None = None) -> None:
        super().__init__(
            self.action, job_id, author_id, label=label or self.label, emoji=emoji or self.emoji, style=self.style
        )
        self.job_id: int = job_id

    @override
    @classmethod
    async def from_custom_id(cls, interaction: Interaction, item: Any, match: re.Match[str], /) -> Self:
        return cls(int(match["job_id"]), int(match["author_id"]))


class EditButton(JobButton, template=r"reminder:edit:(?P<job_id>\d+):(?P<author_id>\d+)"):
    """Open a form to change the reminder's time or text."""

    action, label, emoji = "edit", "Edit", "✏️"

    @override
    async def run(self, interaction: Interaction) -> None:
        job = await self.get_job(interaction, self.job_id, self.author_id)
        await interaction.response.send_modal(EditModal(job))


class DeleteButton(JobButton, template=r"reminder:delete:(?P<job_id>\d+):(?P<author_id>\d+)"):
    """Delete the reminder (or stop a repeating one)."""

    action, label, emoji, style = "delete", "Delete", "🗑️", discord.ButtonStyle.red

    @override
    async def run(self, interaction: Interaction) -> None:
        deleted = await interaction.client.scheduler.delete(self.job_id, kind=KIND, user_id=self.author_id)
        if deleted is None:
            msg = "This reminder is already over."
            raise errors.BadUserInputError(msg)
        await interaction.response.send_message(f"Deleted the reminder #{self.job_id}.", ephemeral=True)


class SkipButton(JobButton, template=r"reminder:skip:(?P<job_id>\d+):(?P<author_id>\d+)"):
    """Skip the next time of a repeating reminder."""

    action, label, emoji = "skip", "Skip next", "⏭️"

    @override
    async def run(self, interaction: Interaction) -> None:
        job = await self.get_job(interaction, self.job_id, self.author_id)
        if (after := next_after_skip(job)) is None:
            msg = "This reminder doesn't repeat after its next time, delete it instead."
            raise errors.BadUserInputError(msg)
        updated = await interaction.client.scheduler.update(job.id, kind=KIND, user_id=self.author_id, when=after)
        if updated is None:
            msg = "This reminder is arriving right now, try again in a moment."
            raise errors.BadUserInputError(msg)
        await interaction.response.send_message(
            f"⏭️ Skipped {clock.discord(job.due_at, 'f')}. Next time: {clock.discord(updated.due_at, 'f', 'R')}.",
            ephemeral=True,
        )


class PauseButton(JobButton, template=r"reminder:pause:(?P<job_id>\d+):(?P<author_id>\d+)"):
    """Pause a (repeating) reminder until it's resumed."""

    action, label, emoji = "pause", "Pause", "⏸️"

    @override
    async def run(self, interaction: Interaction) -> None:
        paused = await interaction.client.scheduler.pause(self.job_id, kind=KIND, user_id=self.author_id)
        if paused is None:
            msg = "This reminder is already over (or arriving right now)."
            raise errors.BadUserInputError(msg)
        view = discord.ui.View(timeout=None).add_item(ResumeButton(self.job_id, self.author_id))
        await interaction.response.send_message(
            f"⏸️ Paused the reminder #{self.job_id}. Resume it here or in `/remind list`.", view=view, ephemeral=True
        )


class ResumeButton(JobButton, template=r"reminder:resume:(?P<job_id>\d+):(?P<author_id>\d+)"):
    """Resume a paused reminder."""

    action, label, emoji, style = "resume", "Resume", "▶️", discord.ButtonStyle.green

    @override
    async def run(self, interaction: Interaction) -> None:
        resumed = await interaction.client.scheduler.resume(self.job_id, kind=KIND, user_id=self.author_id)
        if resumed is None:
            msg = "This reminder is already over."
            raise errors.BadUserInputError(msg)
        await interaction.response.send_message(
            f"▶️ Resumed the reminder #{self.job_id}: next {clock.discord(resumed.fire_at, 'f', 'R')}.",
            ephemeral=True,
        )


class SnoozeButton(ReminderButton, template=r"reminder:snooze:(?P<duration>\w+):(?P<author_id>\d+)"):
    """Remind again later about an arrived reminder.

    The text is read from the reminder's message itself, so this works however old the message is.
    ``duration`` "custom" opens a form for the time.
    """

    def __init__(self, duration: str, author_id: int, *, label: str | None = None) -> None:
        emoji = "💤" if duration != "custom" else "⏰"
        super().__init__("snooze", duration, author_id, label=label or duration, emoji=emoji)
        self.duration: str = duration

    @override
    @classmethod
    async def from_custom_id(cls, interaction: Interaction, item: Any, match: re.Match[str], /) -> Self:
        return cls(match["duration"], int(match["author_id"]))

    @override
    async def run(self, interaction: Interaction) -> None:
        if self.duration == "custom":
            await interaction.response.send_modal(SnoozeModal())
            return
        timezone = await user_timezone(interaction) or UTC
        parsed = parse_time(self.duration, now=interaction.created_at, timezone=timezone)
        await snooze(interaction, parsed)


async def snooze(interaction: Interaction, parsed: ParsedTime) -> None:
    """Set a new reminder with the text of the arrived reminder that the interaction's message is."""
    message = interaction.message
    assert message is not None
    text = message.embeds[0].description if message.embeds else None
    data: ReminderData = {
        "text": text or DEFAULT_TEXT,
        "channel_id": message.channel.id,
        "message_id": message.id,  # the snoozed reminder replies to this one
    }
    job = await interaction.client.scheduler.schedule(
        KIND, parsed.when, data=data, user_id=interaction.user.id, guild_id=interaction.guild_id
    )
    await interaction.response.send_message(
        f"💤 Snoozed: reminder #{job.id} {clock.discord(job.due_at, 'R')}.", ephemeral=True
    )


BUTTON_CLASSES: Final = (EditButton, DeleteButton, SkipButton, PauseButton, ResumeButton, SnoozeButton)


# --- MODALS -----------------------------------------------------------------------------------------------------------


class SnoozeModal(Modal, title="Snooze"):
    """Ask for how long to snooze an arrived reminder."""

    when = discord.ui.TextInput(label="When", placeholder="10m, 2h, tomorrow 9am, friday...", min_length=1)

    @override
    async def on_submit(self, interaction: Interaction) -> None:
        timezone = await user_timezone(interaction) or UTC
        await snooze(interaction, parse_time(self.when.value, now=interaction.created_at, timezone=timezone))


class EditModal(Modal, title="Edit reminder"):
    """Change the time (or the repeat) and/or the text of a reminder."""

    when = discord.ui.TextInput(label="New time (leave empty to keep it)", required=False, max_length=100)
    text = discord.ui.TextInput(label="Text", style=discord.TextStyle.long, max_length=MAX_TEXT_LENGTH)

    def __init__(self, job: Job[ReminderData]) -> None:
        super().__init__()
        self.job: Job[ReminderData] = job
        self.text.default = job.data["text"]
        now = f"Now: {job.due_at:%Y-%m-%d %H:%M} UTC"
        self.when.placeholder = f"{now}, {describe_rule(job.rule)}" if job.rule is not None else now

    @override
    async def on_submit(self, interaction: Interaction) -> None:
        cog = interaction.client.get_cog("Reminders")
        assert isinstance(cog, Reminders)
        timezone = await user_timezone(interaction) or UTC
        parsed = parse_time(self.when.value, now=interaction.created_at, timezone=timezone) if self.when.value else None
        await cog.edit_reminder(interaction, self.job.id, parsed=parsed, text=self.text.value or DEFAULT_TEXT)


class RemindMeModal(Modal, title="Remind me about this"):
    """Ask when to remind about a message (from the message context menu)."""

    when = discord.ui.TextInput(
        label="When", placeholder="1h, tomorrow 9am, eow, every friday 18:00...", max_length=100
    )
    text = discord.ui.TextInput(
        label="Note (optional)", style=discord.TextStyle.long, required=False, max_length=MAX_TEXT_LENGTH
    )

    def __init__(self, message: discord.Message) -> None:
        super().__init__()
        self.target: discord.Message = message

    @override
    async def on_submit(self, interaction: Interaction) -> None:
        cog = interaction.client.get_cog("Reminders")
        assert isinstance(cog, Reminders)
        timezone = await user_timezone(interaction) or UTC
        parsed = parse_time(self.when.value, now=interaction.created_at, timezone=timezone)
        text = self.text.value or f"About {self.target.jump_url}"
        await cog.create_reminder(
            interaction, parsed, text, channel_id=self.target.channel.id, message_id=self.target.id, ephemeral=True
        )


# --- AUTOCOMPLETE -----------------------------------------------------------------------------------------------------


class ReminderIdTransformer(app_commands.Transformer):
    """Option for one of the user's reminders: the autocomplete lists them with their time and text."""

    @property
    @override
    def type(self) -> discord.AppCommandOptionType:
        return discord.AppCommandOptionType.integer

    @override
    async def transform(self, interaction: Interaction, value: int) -> int:  # ty: ignore[invalid-method-override]
        return int(value)

    @override
    async def autocomplete(self, interaction: Interaction, value: int | str) -> list[app_commands.Choice[int]]:  # ty: ignore[invalid-method-override]
        jobs: list[Job[ReminderData]] = await interaction.client.scheduler.fetch(KIND, user_id=interaction.user.id)
        query = str(value).lower().lstrip("#")
        choices: list[app_commands.Choice[int]] = []
        now = clock.utcnow()
        for job in jobs:
            text = job.data["text"]
            if query and query not in str(job.id) and query not in text.lower():
                continue
            relative = clock.human_datetime_diff(job.fire_at, relative_to=now, max_units=1)
            paused = "⏸️ paused · " if job.is_paused else ""
            name = f"#{job.id} · {paused}in {relative} · {repeat_label(job.rule)} {shorten(text, 60)}"
            choices.append(app_commands.Choice(name=" ".join(name.split())[:100], value=job.id))
            if len(choices) == 25:
                break
        return choices


# --- LIST -------------------------------------------------------------------------------------------------------------


class PageButton(ui.Button["ReminderListView"]):
    """◀️ / ▶️ under `/remind list`."""

    def __init__(self, emoji: str, step: int, *, disabled: bool) -> None:
        super().__init__(emoji=emoji, disabled=disabled)
        self.step: int = step

    @override
    async def callback(self, interaction: Interaction) -> None:
        assert self.view is not None
        await self.view.turn(interaction, self.step)


class EditSelect(ui.Select["ReminderListView"]):
    """Show "✏️ Edit a reminder…" under `/remind list`: picking one opens the edit form."""

    def __init__(self, jobs: list[Job[ReminderData]]) -> None:
        options = [
            discord.SelectOption(label=f"#{job.id} · {shorten(job.data['text'], 80)}"[:100], value=str(job.id))
            for job in jobs
        ]
        super().__init__(placeholder="✏️ Edit a reminder…", options=options)

    @override
    async def callback(self, interaction: Interaction) -> None:
        job_id = int(self.values[0])
        job: Job[ReminderData] | None = await interaction.client.scheduler.get(
            job_id, kind=KIND, user_id=interaction.user.id
        )
        if job is None:
            await interaction.response.send_message("This reminder is already over.", ephemeral=True)
            return
        await interaction.response.send_modal(EditModal(job))


class ReminderListView(LayoutView):
    """``/remind list``: the user's reminders a page at a time, with a delete (or resume) button each.

    A menu under them edits one. The delete and resume buttons are the same dynamic items as elsewhere,
    so they keep working after restarts.
    """

    def __init__(self, user: discord.User | discord.Member, jobs: list[Job[ReminderData]]) -> None:
        super().__init__(author_id=user.id, timeout=300)
        self.user: discord.User | discord.Member = user
        self.jobs: list[Job[ReminderData]] = jobs
        self.page: int = 0
        self.build()

    @property
    def page_count(self) -> int:
        """How many pages the reminders take (at least one, which may be empty)."""
        return max(1, -(-len(self.jobs) // REMINDERS_PER_PAGE))

    def build(self) -> None:
        """Lay out the current page."""
        self.clear_items()
        title = f"## ⏰ {self.user.display_name}'s reminders"
        if self.page_count > 1:
            title += f" · page {self.page + 1}/{self.page_count}"
        container = ui.Container[Self](accent_colour=getattr(self.user, "colour", None) or const.Palette.purple_500)
        container.add_item(ui.TextDisplay(title))

        start = self.page * REMINDERS_PER_PAGE
        page_jobs = self.jobs[start : start + REMINDERS_PER_PAGE]
        for job in page_jobs:
            state = "⏸️ paused · " if job.is_paused else ""
            dm = " 📩" if job.data.get("dm", False) else ""
            text = (
                f"**#{job.id}** · {state}{clock.discord(job.fire_at, 'f', 'R')} {repeat_label(job.rule)}{dm}\n"
                f"-# {shorten(job.data['text'])}"
            )
            button_class = ResumeButton if job.is_paused else DeleteButton
            # a `DynamicItem` works as an accessory, it's only typed for both view kinds instead of `LayoutView`
            container.add_item(ui.Section(text, accessory=button_class(job.id, self.user.id)))
        if not self.jobs:
            container.add_item(ui.TextDisplay("You don't have any reminders. Set one with `/remind set`."))
        self.add_item(container)

        if page_jobs:
            self.add_item(ui.ActionRow[ReminderListView](EditSelect(page_jobs)))
        if self.page_count > 1:
            previous = PageButton("◀️", -1, disabled=self.page == 0)
            following = PageButton("▶️", 1, disabled=self.page == self.page_count - 1)
            self.add_item(ui.ActionRow[ReminderListView](previous, following))

    async def turn(self, interaction: Interaction, step: int) -> None:
        """Move by `step` pages and redraw."""
        self.page = min(max(self.page + step, 0), self.page_count - 1)
        self.build()
        await interaction.response.edit_message(view=self, allowed_mentions=discord.AllowedMentions.none())


# --- CONVERTING TIMES -------------------------------------------------------------------------------------------------

_TIME_IN_TEXT: Final = re.compile(
    r"""
    (?:\b(?:today|tomorrow|tonight|(?:mon|tue|wed|thu|fri|sat|sun)[a-z]*)\s+(?:at\s+)?|\b\d{4}-\d{2}-\d{2}[\sT])?
    \b\d{1,2}(?::\d{2})?(?:\s*(?:am|pm))?
    (?:\s*(?:utc|gmt)\s*[+-]\s*\d{1,2}|\s+[a-z]+/[a-z_]+|\s+[a-z]{2,5})?
    """,
    re.IGNORECASE | re.VERBOSE,
)


def find_times(text: str, *, now: dt.datetime, timezone: str) -> list[tuple[str, ParsedTime]]:
    """Find the clock times in a message ("18:00 MSK", "3pm EST", "tomorrow 9am") and understand each.

    Only things that are clearly times count: with minutes, am/pm or a timezone, not a bare number.
    A word after a time is tried as its timezone, and dropped if it isn't one.
    """
    found: list[tuple[str, ParsedTime]] = []
    for match in _TIME_IN_TEXT.finditer(text):
        candidate = match.group(0).strip()
        if not re.search(r":\d|am|pm|utc|gmt|/|\s[a-z]{2,5}$", candidate, re.IGNORECASE):
            continue
        for attempt in (candidate, candidate.rsplit(maxsplit=1)[0]):
            try:
                parsed = parse_time(attempt, now=now, timezone=timezone)
            except errors.BadUserInputError:
                continue
            if parsed.rule is None:
                found.append((attempt, parsed))
            break
        if len(found) == MAX_CONVERTED_TIMES:
            break
    return found


# --- COG --------------------------------------------------------------------------------------------------------------


class Reminders(Cog):
    """Remind yourself of something at some time."""

    def __init__(self, bot: Bot) -> None:
        super().__init__(bot)
        self.remind_me_menu: app_commands.ContextMenu = app_commands.ContextMenu(
            name="Remind me about this", callback=self.remind_me_about_message
        )
        self.convert_menu: app_commands.ContextMenu = app_commands.ContextMenu(
            name="Convert times", callback=self.convert_times
        )
        self._bundled: set[int] = set()
        """Late reminders already delivered inside another reminder's bundle, whose own handler has nothing to send."""
        self._bundle_locks: collections.defaultdict[tuple[int, int, bool], asyncio.Lock] = collections.defaultdict(
            asyncio.Lock
        )

    @override
    async def cog_load(self) -> None:
        self.bot.add_dynamic_items(*BUTTON_CLASSES)
        self.bot.tree.add_command(self.remind_me_menu)
        self.bot.tree.add_command(self.convert_menu)
        await super().cog_load()

    @override
    async def cog_unload(self) -> None:
        self.bot.remove_dynamic_items(*BUTTON_CLASSES)
        self.bot.tree.remove_command(self.remind_me_menu.name, type=self.remind_me_menu.type)
        self.bot.tree.remove_command(self.convert_menu.name, type=self.convert_menu.type)
        await super().cog_unload()

    remind_group = app_commands.Group(name="remind", description="Reminders that ping you when the time comes.")

    # --- CREATING -----------------------------------------------------------------------------------------------------

    async def create_reminder(
        self,
        interaction: Interaction,
        parsed: ParsedTime,
        text: str,
        *,
        repeat: Repeat = Repeat.never,
        channel_id: int | None = None,
        message_id: int | None = None,
        dm: bool = False,
        ephemeral: bool = False,
    ) -> None:
        """Create a reminder and confirm it with the buttons.

        Parameters
        ----------
        interaction
            The interaction to respond to.
        parsed
            When to remind (with a rule for repeats typed in like "every friday 18:00").
        text
            What to remind of.
        repeat
            A repeat preset; can't be combined with a repeat typed in `parsed`.
        channel_id
            Channel to remind in. Defaults to the interaction's.
        message_id
            Message to reply to when the reminder arrives. Defaults to the confirmation message.
        dm
            Deliver the reminder in the user's DMs.
        ephemeral
            Whether only the user sees the confirmation.
        """
        user = interaction.user
        if len(text) > MAX_TEXT_LENGTH:
            msg = f"Reminders must be at most {MAX_TEXT_LENGTH} characters long."
            raise errors.BadUserInputError(msg)
        is_owner = await self.bot.is_owner(user)  # ty: ignore[invalid-argument-type]
        if not is_owner and await self.bot.scheduler.count(KIND, user_id=user.id) >= MAX_REMINDERS_PER_USER:
            msg = f"You have {MAX_REMINDERS_PER_USER} reminders already, please delete some first."
            raise errors.BadUserInputError(msg)

        rule = parsed.rule
        if repeat is not Repeat.never:
            if rule is not None and rule != repeat.rule:
                msg = 'Pick the repeat either in "when" (like "every friday 18:00") or in "repeat", not both.'
                raise errors.BadUserInputError(msg)
            rule = repeat.rule

        timezone = await user_timezone(interaction)
        when = parsed.when
        if rule is not None and when.is_absolute and not rule.startswith("FREQ=HOURLY"):
            # repeats follow the user's clocks: "every day" at the same local time, even across DST
            when = to_wall_time(parsed.moment, timezone or UTC)

        channel_id = channel_id or interaction.channel_id
        assert channel_id is not None
        data: ReminderData = {"text": text, "channel_id": channel_id, "message_id": message_id}
        if dm:
            data["dm"] = True
        job = await self.bot.scheduler.schedule(
            KIND, when, data=data, user_id=user.id, guild_id=interaction.guild_id, rule=rule
        )

        embed = await self.confirmation_embed(job, user, hint_timezone=timezone is None)
        view = discord.ui.View(timeout=None)
        view.add_item(EditButton(job.id, user.id)).add_item(DeleteButton(job.id, user.id))
        await interaction.response.send_message(embed=embed, view=view, ephemeral=ephemeral)

        if message_id is None:
            # the reminder replies to the confirmation when it arrives, so the context is right above it
            response = await interaction.original_response()
            await self.bot.scheduler.update(job.id, kind=KIND, data={**data, "message_id": response.id})

    async def confirmation_embed(
        self, job: Job[ReminderData], user: discord.User | discord.Member, *, hint_timezone: bool
    ) -> discord.Embed:
        """Embed that confirms a new or changed reminder."""
        embed = discord.Embed(
            color=getattr(user, "color", None) or const.Palette.purple_500,
            description=job.data["text"],
        ).set_author(name=f"Reminder #{job.id} for {user.display_name}", icon_url=user.display_avatar.url)
        embed.add_field(name="When", value=clock.discord(job.fire_at, "F", "R"))
        if job.rule is not None:
            embed.add_field(name="Repeats", value=repeat_label(job.rule))
        if job.data.get("dm", False):
            embed.add_field(name="Where", value="📩 in your DMs")
        if hint_timezone:
            mention = await self.bot.tree.find_mention_for("timezone set") or "`/timezone set`"
            embed.add_field(
                name="P.S.", value=f"Times are read in UTC for you. Set your timezone with {mention}.", inline=False
            )
        return embed

    @remind_group.command(name="set")
    @app_commands.checks.cooldown(5, 60.0, key=lambda interaction: interaction.user.id)
    async def remind_set(
        self,
        interaction: Interaction,
        when: app_commands.Transform[ParsedTime, TimeTransformer],
        text: app_commands.Range[str, 1, MAX_TEXT_LENGTH] = DEFAULT_TEXT,
        repeat: Repeat = Repeat.never,
        dm: bool = False,  # ruff: ignore[boolean-type-hint-positional-argument, boolean-default-value-positional-argument]
    ) -> None:
        """Set a reminder: I'll ping you when the time comes.

        Parameters
        ----------
        when
            "2h30m", "tomorrow 9am", "friday 18:00 MSK", "every mon and thu 20:00"... The suggestion shows how
            I read it.
        text
            What to remind you of.
        repeat
            Repeat the reminder at the same time on your clocks (or type the repeat in "when": "every friday 18:00").
        dm
            Remind you in DMs instead of this channel.
        """
        await self.create_reminder(interaction, when, text, repeat=repeat, dm=dm)

    async def remind_me_about_message(self, interaction: Interaction, message: discord.Message) -> None:
        """Message context menu: remind about this message."""
        await interaction.response.send_modal(RemindMeModal(message))

    # --- MANAGING -----------------------------------------------------------------------------------------------------

    @remind_group.command(name="list")
    async def remind_list(self, interaction: Interaction) -> None:
        """Show your reminders, with buttons to delete or resume them and a menu to edit one."""
        jobs: list[Job[ReminderData]] = await self.bot.scheduler.fetch(KIND, user_id=interaction.user.id)
        view = ReminderListView(interaction.user, jobs)
        # ephemeral: the user sees their list, the rest of the channel doesn't see what they're reminded of
        await interaction.response.send_message(
            view=view, ephemeral=True, allowed_mentions=discord.AllowedMentions.none()
        )
        view.message = await interaction.original_response()

    async def edit_reminder(
        self,
        interaction: Interaction,
        job_id: int,
        *,
        parsed: ParsedTime | None = None,
        text: str | None = None,
        repeat: Repeat | None = None,
    ) -> None:
        """Change a reminder of the user and show it.

        Parameters
        ----------
        interaction
            The interaction to respond to.
        job_id
            ID of the reminder.
        parsed
            New time, if any; a typed repeat ("every friday 18:00") replaces the reminder's repeat.
        text
            New text, if any.
        repeat
            New repeat preset, if any.
        """
        jobs = self.bot.scheduler
        job: Job[ReminderData] | None = await jobs.get(job_id, kind=KIND, user_id=interaction.user.id)
        if job is None:
            msg = f"You don't have a reminder #{job_id}."
            raise errors.BadUserInputError(msg)

        changes: dict[str, Any] = {}
        if text is not None:
            changes["data"] = {**job.data, "text": text}
        if repeat is not None:
            changes["rule"] = repeat.rule
        if parsed is not None:
            changes["when"] = parsed.when
            if parsed.rule is not None:
                changes["rule"] = parsed.rule
        rule = changes.get("rule", job.rule)
        if rule is not None and not rule.startswith("FREQ=HOURLY"):
            # repeating reminders follow the user's clocks
            when: WallTime = changes.get("when", job.when)
            if when.is_absolute:
                changes["when"] = to_wall_time(when.to_utc(), await user_timezone(interaction) or UTC)

        updated: Job[ReminderData] | None = await jobs.update(job.id, kind=KIND, user_id=interaction.user.id, **changes)
        if updated is None:
            msg = "This reminder is arriving right now, too late to change it."
            raise errors.BadUserInputError(msg)
        embed = await self.confirmation_embed(updated, interaction.user, hint_timezone=False)
        await interaction.response.send_message(content="Reminder changed:", embed=embed, ephemeral=True)

    @remind_group.command(name="edit")
    async def remind_edit(
        self,
        interaction: Interaction,
        reminder: app_commands.Transform[int, ReminderIdTransformer],
        when: app_commands.Transform[ParsedTime, TimeTransformer] | None = None,
        text: app_commands.Range[str, 1, MAX_TEXT_LENGTH] | None = None,
        repeat: Repeat | None = None,
    ) -> None:
        """Change one of your reminders.

        Parameters
        ----------
        reminder
            The reminder to change.
        when
            New time; a repeat like "every friday 18:00" also replaces the repeat.
        text
            New text.
        repeat
            New repeat; "never" stops repeating.
        """
        await self.edit_reminder(interaction, reminder, parsed=when, text=text, repeat=repeat)

    @remind_group.command(name="delete")
    async def remind_delete(
        self, interaction: Interaction, reminder: app_commands.Transform[int, ReminderIdTransformer]
    ) -> None:
        """Delete one of your reminders.

        Parameters
        ----------
        reminder
            The reminder to delete.
        """
        deleted = await self.bot.scheduler.delete(reminder, kind=KIND, user_id=interaction.user.id)
        if deleted is None:
            msg = f"You don't have a reminder #{reminder}."
            raise errors.BadUserInputError(msg)
        await interaction.response.send_message(
            f"Deleted the reminder #{reminder}: {shorten(deleted.data['text'])}", ephemeral=True
        )

    @remind_group.command(name="clear")
    async def remind_clear(self, interaction: Interaction) -> None:
        """Delete all your reminders."""
        total = await self.bot.scheduler.count(KIND, user_id=interaction.user.id)
        if total == 0:
            await interaction.response.send_message("You don't have any reminders.", ephemeral=True)
            return
        embed = discord.Embed(
            color=const.Palette.red_500,
            description=f"Delete all your {total} reminders? This can't be undone.",
        )
        if not await prompts.confirm(interaction, embed=embed, ephemeral=True):
            return
        deleted = await self.bot.scheduler.delete_where(KIND, user_id=interaction.user.id)
        await interaction.followup.send(f"Deleted {len(deleted)} reminders.", ephemeral=True)

    # --- TIMESTAMPS ---------------------------------------------------------------------------------------------------

    @app_commands.command(name="timestamp")
    async def timestamp(
        self, interaction: Interaction, when: app_commands.Transform[ParsedTime, TimeTransformer]
    ) -> None:
        """Turn a time into Discord timestamps, which show it to everyone in their own timezone.

        Parameters
        ----------
        when
            "friday 18:00", "in 3 hours", "2026-12-31 23:00"... The suggestion shows how I read it.
        """
        seconds = int(when.moment.timestamp())
        lines = [f"<t:{seconds}:{style}> `<t:{seconds}:{style}>`" for style in ("F", "f", "D", "t", "R")]
        await interaction.response.send_message("\n".join(lines), ephemeral=True)

    async def convert_times(self, interaction: Interaction, message: discord.Message) -> None:
        """Message context menu: show the times in the message ("18:00 MSK") in everybody's own timezone.

        Times without a timezone are read in the message author's timezone (``/timezone set``), UTC if they have none.
        """
        author_timezone = await self.bot.tz_manager.get_timezone(message.author.id)
        found = find_times(message.content, now=message.created_at, timezone=author_timezone or UTC)
        if not found:
            content = (
                "I found no times in this message. I understand things like `18:00`, `3pm EST`, `tomorrow 9am MSK`."
            )
        else:
            lines = [
                f"`{text}` → {clock.discord(parsed.moment, 'F')} ({clock.discord(parsed.moment, 'R')})"
                for text, parsed in found
            ]
            if author_timezone is None and any(parsed.when.timezone == UTC for _, parsed in found):
                lines.append(
                    f"-# Times without a timezone are read as UTC: {message.author.display_name} hasn't set one."
                )
            content = "\n".join(lines)
        await interaction.response.send_message(content, ephemeral=True)

    # --- ARRIVING -----------------------------------------------------------------------------------------------------

    @scheduler.handler(KIND, retry_delay=dt.timedelta(seconds=30))
    async def send_reminder(self, job: Job[ReminderData]) -> None:
        """Deliver a reminder: a reply to its message, or a DM if it's a DM reminder or the channel is unusable.

        Late reminders of the same person and place (e.g. after downtime) go out together, as one message.
        """
        author_id = job.user_id or 0
        if job.lateness <= LATE_AFTER:
            await self.deliver_one(job, late=False)
            return

        key = (author_id, job.data["channel_id"], bool(job.data.get("dm", False)))
        async with self._bundle_locks[key]:
            if job.id in self._bundled:
                # an earlier late reminder took this one along: done (a repeating one moves on by itself)
                self._bundled.discard(job.id)
                return
            now = self.bot.scheduler.now()
            others: list[Job[ReminderData]] = [
                other
                for other in await self.bot.scheduler.fetch(KIND, user_id=author_id)
                if other.id != job.id
                and other.claimed_at is not None  # claimed by this process, waiting for its turn
                and other.fire_at <= now - LATE_AFTER
                and (other.data["channel_id"], bool(other.data.get("dm", False))) == key[1:]
            ]
            if not others:
                await self.deliver_one(job, late=True)
                return
            await self.deliver_bundle([job, *others])
            self._bundled.update(other.id for other in others)

    def reminder_embed(self, job: Job[ReminderData], *, late: bool) -> discord.Embed:
        """Build the embed of an arriving reminder (its description is the text, which snoozing reads back)."""
        embed = discord.Embed(
            color=const.Palette.red_500 if late else const.Palette.purple_500, description=job.data["text"]
        )
        embed.set_author(name=f"⏰ Reminder #{job.id}")
        embed.add_field(name="Set", value=clock.discord(job.created_at, "R"))
        if job.rule is not None:
            embed.add_field(name="Repeats", value=repeat_label(job.rule))
        if late:
            embed.add_field(
                name="Sorry, I'm late",
                value=f"It was due {clock.discord(job.due_at, 'R')}, but I was offline.",
                inline=False,
            )
        return embed

    async def deliver_one(self, job: Job[ReminderData], *, late: bool) -> None:
        """Deliver one reminder, with its snooze (and repeat) buttons."""
        author_id = job.user_id or 0
        data = job.data
        view = discord.ui.View(timeout=None)
        for duration, label in SNOOZE_PRESETS:
            view.add_item(SnoozeButton(duration, author_id, label=label))
        view.add_item(SnoozeButton("custom", author_id, label="Later..."))
        if job.rule is not None:
            view.add_item(SkipButton(job.id, author_id))
            view.add_item(PauseButton(job.id, author_id))
            view.add_item(DeleteButton(job.id, author_id, label="Stop repeating", emoji="🛑"))
        if data["message_id"] is not None:
            url = message_url(job.guild_id, data["channel_id"], data["message_id"])
            view.add_item(discord.ui.Button(label="Original message", url=url))
        await self.deliver(job, embed=self.reminder_embed(job, late=late), view=view)

    async def deliver_bundle(self, jobs: list[Job[ReminderData]]) -> None:
        """Deliver several late reminders of one person and place as one message."""
        lines = [
            f"**#{job.id}** · due {clock.discord(job.due_at, 'R')} {repeat_label(job.rule)}\n"
            f"{shorten(job.data['text'], 300)}"
            for job in sorted(jobs, key=lambda job: job.due_at)
        ]
        description = "\n\n".join(lines)
        if len(description) > MAX_BUNDLE_LENGTH:
            description = description[: MAX_BUNDLE_LENGTH - 1] + "…"
        embed = discord.Embed(color=const.Palette.red_500, description=description).set_author(
            name=f"⏰ {len(jobs)} reminders arrived late: I was offline, sorry"
        )
        await self.deliver(jobs[0], embed=embed, view=None)

    async def deliver(self, job: Job[ReminderData], *, embed: discord.Embed, view: discord.ui.View | None) -> None:
        """Send a reminder message: in the author's DMs for DM reminders, else as a reply in the channel.

        A channel that's gone or closed falls back to DMs; if DMs are closed too there's nowhere to deliver it, which
        retrying won't change, so it's only logged. Other errors (Discord being down) raise, so the job is retried.
        """
        author_id = job.user_id or 0
        data = job.data
        # the text is typed by users but sent by the bot: only the author may ever be pinged by it
        mentions = discord.AllowedMentions(everyone=False, roles=False, users=[discord.Object(author_id)])
        send_kwargs: dict[str, Any] = {"embed": embed, "allowed_mentions": mentions}
        if view is not None:
            send_kwargs["view"] = view

        if not data.get("dm", False):
            try:
                channel = self.bot.get_channel(data["channel_id"]) or await self.bot.fetch_channel(data["channel_id"])
                assert isinstance(channel, discord.abc.Messageable)
                reference = None
                if data["message_id"] is not None:
                    reference = discord.MessageReference(
                        message_id=data["message_id"], channel_id=data["channel_id"], fail_if_not_exists=False
                    )
                await channel.send(f"<@{author_id}>", reference=reference, **send_kwargs)
            except discord.Forbidden, discord.NotFound, AssertionError:
                logger.info("Reminder {}: channel {} is unusable, sending a DM.", job.id, data["channel_id"])
            else:
                return

        try:
            user = self.bot.get_user(author_id) or await self.bot.fetch_user(author_id)
            await user.send(**send_kwargs)
        except discord.Forbidden, discord.NotFound:
            logger.warning("Reminder {}: neither channel {} nor DMs of {} work.", job.id, data["channel_id"], author_id)


async def setup(bot: Bot) -> None:
    """Load the extension (discord.py entry point)."""
    await bot.add_cog(Reminders(bot))
