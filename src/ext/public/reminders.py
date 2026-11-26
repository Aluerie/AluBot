# Copyright (C) 2020-present, Irene Adler 💜 (@Aluerie).
# Licensed under MPL-2.0, see the LICENSE file for details.
"""Reminders.

* ``/remind set`` (the autocomplete shows how the time is understood), optionally repeating;
  the confirmation has buttons to join the reminder (🔔), edit it or delete it.
* "Remind me about this" in the message context menu reminds about that message.
* The reminder arrives as a reply to the message it was set from, says if it's late,
  and has buttons to snooze it (or to stop a repeating one). All buttons keep working after restarts.
* ``/timestamp`` turns a time into Discord timestamps, to paste so everyone sees it in their own timezone.
"""

from __future__ import annotations

import datetime as dt
import enum
import textwrap
from typing import TYPE_CHECKING, Any, Final, Self, TypedDict, override
lazy import re

import discord
from discord import app_commands, ui
from loguru import logger

from core import Cog, LayoutView, Modal
from shared import clock, errors, scheduler
from shared.scheduler import UTC, Job, WallTime, to_wall_time
from shared.timeparse import ParsedTime, parse_time
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
MAX_MENTIONS: Final = 25
"""How many people can join a reminder with 🔔."""
LATE_AFTER: Final = dt.timedelta(minutes=5)
"""Reminders later than this say so (e.g. the bot was offline at the time)."""
DEFAULT_TEXT: Final = "…"
REMINDERS_PER_PAGE: Final = 8
"""Reminders per page of `/remind list`: a layout holds 40 components, and a reminder takes 3."""
SNOOZE_PRESETS: Final = (("10m", "10 min"), ("1h", "1 hour"), ("1d", "1 day"))


class ReminderData(TypedDict, closed=True):
    """Data of a reminder job; its author is the job's `user_id`."""

    text: str
    channel_id: int
    message_id: int | None
    """The message the reminder replies to when it arrives."""
    mentions: list[int]
    """Other people who joined the reminder with 🔔."""


class Repeat(enum.Enum):
    """How a reminder repeats; the values are RRULEs evaluated on the author's clocks."""

    never = "never"  # Discord needs non-empty choice values
    daily = "FREQ=DAILY"
    weekdays = "FREQ=WEEKLY;BYDAY=MO,TU,WE,TH,FR"
    weekly = "FREQ=WEEKLY"
    monthly = "FREQ=MONTHLY"
    yearly = "FREQ=YEARLY"

    @classmethod
    def from_rule(cls, rule: str | None) -> Repeat:
        """Get the repeat of a job's rule (`never` for no rule)."""
        return next((repeat for repeat in cls if repeat.value == rule), Repeat.never)

    @property
    def rule(self) -> str | None:
        """The RRULE, or `None` for `never`."""
        return None if self is Repeat.never else self.value

    @property
    def label(self) -> str:
        """What users see, e.g. "🔁 every weekday"."""
        return "" if self is Repeat.never else f"🔁 {self.name.replace('weekdays', 'every weekday')}"


def message_url(guild_id: int | None, channel_id: int, message_id: int) -> str:
    """Make a link to a message; DM messages live under "@me"."""
    return f"https://discord.com/channels/{guild_id or '@me'}/{channel_id}/{message_id}"


def shorten(text: str, width: int = MAX_LIST_TEXT_LENGTH) -> str:
    """Shorten the text of a reminder to one line."""
    return textwrap.shorten(text, width=width, placeholder="…") or DEFAULT_TEXT


async def user_timezone(interaction: Interaction) -> str | None:
    """Get the timezone that the user has set with ``/timezone set``, if any."""
    return await interaction.client.tz_manager.get_timezone(interaction.user.id)


# --- BUTTONS ----------------------------------------------------------------------------------------------------------
# Dynamic items: their state lives in the `custom_id`, so they keep working after the bot restarts.


class ReminderButton(discord.ui.DynamicItem[discord.ui.Button[Any]], template=r"$^"):
    """Base for the reminder buttons: answers `BadUserInputError`s to the user instead of failing silently."""

    async def run(self, interaction: Interaction) -> None:
        """Run the button's action."""
        raise NotImplementedError

    @override
    async def callback(self, interaction: Interaction) -> None:
        try:
            await self.run(interaction)
        except errors.BadUserInputError as exc:
            if interaction.response.is_done():
                await interaction.followup.send(str(exc), ephemeral=True)
            else:
                await interaction.response.send_message(str(exc), ephemeral=True)

    @staticmethod
    async def check_author(interaction: Interaction, author_id: int) -> None:
        """Only let the author of the reminder use the button."""
        if interaction.user.id != author_id:
            msg = "This is not your reminder."
            raise errors.BadUserInputError(msg)


class MeTooButton(ReminderButton, template=r"reminder:metoo:(?P<job_id>\d+)"):
    """Join somebody else's reminder: get pinged with them when it arrives."""

    def __init__(self, job_id: int) -> None:
        super().__init__(
            discord.ui.Button(
                label="Me too", emoji="🔔", style=discord.ButtonStyle.green, custom_id=f"reminder:metoo:{job_id}"
            )
        )
        self.job_id: int = job_id

    @override
    @classmethod
    async def from_custom_id(cls, interaction: Interaction, item: Any, match: re.Match[str], /) -> Self:
        return cls(int(match["job_id"]))

    @override
    async def run(self, interaction: Interaction) -> None:
        jobs = interaction.client.scheduler
        job: Job[ReminderData] | None = await jobs.get(self.job_id, kind=KIND)
        if job is None:
            msg = "This reminder is already over."
            raise errors.BadUserInputError(msg)
        mentions = list(job.data["mentions"])
        if interaction.user.id == job.user_id or interaction.user.id in mentions:
            msg = "You will be reminded already."
            raise errors.BadUserInputError(msg)
        if len(mentions) >= MAX_MENTIONS:
            msg = "Sorry, too many people have joined this reminder already."
            raise errors.BadUserInputError(msg)

        data: ReminderData = {**job.data, "mentions": [*mentions, interaction.user.id]}
        if await jobs.update(job.id, kind=KIND, data=data) is None:
            msg = "This reminder is just arriving, too late to join it."
            raise errors.BadUserInputError(msg)
        await interaction.response.send_message(
            f"Alright, I'll ping you too {clock.discord(job.due_at, 'R')}.", ephemeral=True
        )


class EditButton(ReminderButton, template=r"reminder:edit:(?P<job_id>\d+):(?P<author_id>\d+)"):
    """Open a form to change the reminder's time or text."""

    def __init__(self, job_id: int, author_id: int) -> None:
        super().__init__(discord.ui.Button(label="Edit", emoji="✏️", custom_id=f"reminder:edit:{job_id}:{author_id}"))
        self.job_id: int = job_id
        self.author_id: int = author_id

    @override
    @classmethod
    async def from_custom_id(cls, interaction: Interaction, item: Any, match: re.Match[str], /) -> Self:
        return cls(int(match["job_id"]), int(match["author_id"]))

    @override
    async def run(self, interaction: Interaction) -> None:
        await self.check_author(interaction, self.author_id)
        job: Job[ReminderData] | None = await interaction.client.scheduler.get(
            self.job_id, kind=KIND, user_id=self.author_id
        )
        if job is None:
            msg = "This reminder is already over."
            raise errors.BadUserInputError(msg)
        await interaction.response.send_modal(EditModal(job))


class DeleteButton(ReminderButton, template=r"reminder:delete:(?P<job_id>\d+):(?P<author_id>\d+)"):
    """Delete the reminder (or stop a repeating one)."""

    def __init__(self, job_id: int, author_id: int, *, label: str = "Delete", emoji: str = "🗑️") -> None:
        super().__init__(
            discord.ui.Button(
                label=label,
                emoji=emoji,
                style=discord.ButtonStyle.red,
                custom_id=f"reminder:delete:{job_id}:{author_id}",
            )
        )
        self.job_id: int = job_id
        self.author_id: int = author_id

    @override
    @classmethod
    async def from_custom_id(cls, interaction: Interaction, item: Any, match: re.Match[str], /) -> Self:
        return cls(int(match["job_id"]), int(match["author_id"]))

    @override
    async def run(self, interaction: Interaction) -> None:
        await self.check_author(interaction, self.author_id)
        deleted = await interaction.client.scheduler.delete(self.job_id, kind=KIND, user_id=self.author_id)
        if deleted is None:
            msg = "This reminder is already over."
            raise errors.BadUserInputError(msg)
        await interaction.response.send_message(f"Deleted the reminder #{self.job_id}.", ephemeral=True)


class SnoozeButton(ReminderButton, template=r"reminder:snooze:(?P<duration>\w+):(?P<author_id>\d+)"):
    """Remind again later about an arrived reminder.

    The text is read from the reminder's message itself, so this works however old the message is.
    ``duration`` "custom" opens a form for the time.
    """

    def __init__(self, duration: str, author_id: int, *, label: str | None = None) -> None:
        super().__init__(
            discord.ui.Button(
                label=label or duration,
                emoji="💤" if duration != "custom" else "⏰",
                custom_id=f"reminder:snooze:{duration}:{author_id}",
            )
        )
        self.duration: str = duration
        self.author_id: int = author_id

    @override
    @classmethod
    async def from_custom_id(cls, interaction: Interaction, item: Any, match: re.Match[str], /) -> Self:
        return cls(match["duration"], int(match["author_id"]))

    @override
    async def run(self, interaction: Interaction) -> None:
        await self.check_author(interaction, self.author_id)
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
        "mentions": [],
    }
    job = await interaction.client.scheduler.schedule(
        KIND, parsed.when, data=data, user_id=interaction.user.id, guild_id=interaction.guild_id
    )
    await interaction.response.send_message(
        f"💤 Snoozed: reminder #{job.id} {clock.discord(job.due_at, 'R')}.", ephemeral=True
    )


# --- MODALS -----------------------------------------------------------------------------------------------------------


class SnoozeModal(Modal, title="Snooze"):
    """Ask for how long to snooze an arrived reminder."""

    when = discord.ui.TextInput(label="When", placeholder="10m, 2h, tomorrow 9am, friday...", min_length=1)

    @override
    async def on_submit(self, interaction: Interaction) -> None:
        timezone = await user_timezone(interaction) or UTC
        await snooze(interaction, parse_time(self.when.value, now=interaction.created_at, timezone=timezone))


class EditModal(Modal, title="Edit reminder"):
    """Change the time and/or the text of a reminder."""

    when = discord.ui.TextInput(label="New time (leave empty to keep it)", required=False, max_length=100)
    text = discord.ui.TextInput(label="Text", style=discord.TextStyle.long, max_length=MAX_TEXT_LENGTH)

    def __init__(self, job: Job[ReminderData]) -> None:
        super().__init__()
        self.job: Job[ReminderData] = job
        self.text.default = job.data["text"]
        self.when.placeholder = f"Now: {job.due_at:%Y-%m-%d %H:%M} UTC"

    @override
    async def on_submit(self, interaction: Interaction) -> None:
        cog = interaction.client.get_cog("Reminders")
        assert isinstance(cog, Reminders)
        timezone = await user_timezone(interaction) or UTC
        parsed = parse_time(self.when.value, now=interaction.created_at, timezone=timezone) if self.when.value else None
        await cog.edit_reminder(interaction, self.job.id, parsed=parsed, text=self.text.value or DEFAULT_TEXT)


class RemindMeModal(Modal, title="Remind me about this"):
    """Ask when to remind about a message (from the message context menu)."""

    when = discord.ui.TextInput(label="When", placeholder="1h, tomorrow 9am, eow, friday 18:00...", max_length=100)
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
            name = f"#{job.id} · in {relative} · {Repeat.from_rule(job.rule).label} {shorten(text, 60)}"
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


class ReminderListView(LayoutView):
    """``/remind list``: the user's reminders, each with a 🗑️ button next to it, a page at a time.

    The delete buttons are `DeleteButton`s, the same as on the confirmations, so a deleted reminder simply
    isn't there the next time the list is opened.
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
        for job in self.jobs[start : start + REMINDERS_PER_PAGE]:
            text = (
                f"**#{job.id}** · {clock.discord(job.fire_at, 'f', 'R')} {Repeat.from_rule(job.rule).label}\n"
                f"-# {shorten(job.data['text'])}"
            )
            # a `DynamicItem` works as an accessory, it's only typed for both view kinds instead of `LayoutView`
            container.add_item(ui.Section(text, accessory=DeleteButton(job.id, self.user.id)))  # ty: ignore[invalid-argument-type]
        if not self.jobs:
            container.add_item(ui.TextDisplay("You don't have any reminders. Set one with `/remind set`."))
        container.add_item(ui.TextDisplay("-# Change one with `/remind edit`, or its ✏️ button on the confirmation."))
        self.add_item(container)

        if self.page_count > 1:
            previous = PageButton("◀️", -1, disabled=self.page == 0)
            following = PageButton("▶️", 1, disabled=self.page == self.page_count - 1)
            self.add_item(ui.ActionRow[ReminderListView](previous, following))

    async def turn(self, interaction: Interaction, step: int) -> None:
        """Move by `step` pages and redraw."""
        self.page = min(max(self.page + step, 0), self.page_count - 1)
        self.build()
        await interaction.response.edit_message(view=self, allowed_mentions=discord.AllowedMentions.none())


# --- COG --------------------------------------------------------------------------------------------------------------


class Reminders(Cog):
    """Remind yourself (and others) of something at some time."""

    def __init__(self, bot: Bot) -> None:
        super().__init__(bot)
        self.remind_me_menu: app_commands.ContextMenu = app_commands.ContextMenu(
            name="Remind me about this", callback=self.remind_me_about_message
        )

    @override
    async def cog_load(self) -> None:
        self.bot.add_dynamic_items(MeTooButton, EditButton, DeleteButton, SnoozeButton)
        self.bot.tree.add_command(self.remind_me_menu)
        await super().cog_load()

    @override
    async def cog_unload(self) -> None:
        self.bot.remove_dynamic_items(MeTooButton, EditButton, DeleteButton, SnoozeButton)
        self.bot.tree.remove_command(self.remind_me_menu.name, type=self.remind_me_menu.type)
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
        ephemeral: bool = False,
    ) -> None:
        """Create a reminder and confirm it with the buttons.

        Parameters
        ----------
        interaction
            The interaction to respond to.
        parsed
            When to remind.
        text
            What to remind of.
        repeat
            How to repeat the reminder.
        channel_id
            Channel to remind in. Defaults to the interaction's.
        message_id
            Message to reply to when the reminder arrives. Defaults to the confirmation message.
        ephemeral
            Whether only the user sees the confirmation (and nobody can join with 🔔).
        """
        user = interaction.user
        if len(text) > MAX_TEXT_LENGTH:
            msg = f"Reminders must be at most {MAX_TEXT_LENGTH} characters long."
            raise errors.BadUserInputError(msg)
        is_owner = await self.bot.is_owner(user)  # ty: ignore[invalid-argument-type]
        if not is_owner and await self.bot.scheduler.count(KIND, user_id=user.id) >= MAX_REMINDERS_PER_USER:
            msg = f"You have {MAX_REMINDERS_PER_USER} reminders already, please delete some first."
            raise errors.BadUserInputError(msg)

        timezone = await user_timezone(interaction)
        when = parsed.when
        if repeat is not Repeat.never and when.is_absolute:
            # repeats follow the user's clocks: "every day" at the same local time, even across DST
            when = to_wall_time(parsed.moment, timezone or UTC)

        channel_id = channel_id or interaction.channel_id
        assert channel_id is not None
        data: ReminderData = {"text": text, "channel_id": channel_id, "message_id": message_id, "mentions": []}
        job = await self.bot.scheduler.schedule(
            KIND, when, data=data, user_id=user.id, guild_id=interaction.guild_id, rule=repeat.rule
        )

        embed = await self.confirmation_embed(job, user, hint_timezone=timezone is None)
        view = discord.ui.View(timeout=None)
        if not ephemeral:
            view.add_item(MeTooButton(job.id))
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
        embed.add_field(name="When", value=clock.discord(job.due_at, "F", "R"))
        if job.rule is not None:
            embed.add_field(name="Repeats", value=Repeat.from_rule(job.rule).label)
        if hint_timezone:
            mention = await self.bot.tree.find_mention_for("timezone set") or "`/timezone set`"
            embed.add_field(
                name="P.S.", value=f"Times are read in UTC for you. Set your timezone with {mention}.", inline=False
            )
        return embed

    @remind_group.command(name="set")
    async def remind_set(
        self,
        interaction: Interaction,
        when: app_commands.Transform[ParsedTime, TimeTransformer],
        text: app_commands.Range[str, 1, MAX_TEXT_LENGTH] = DEFAULT_TEXT,
        repeat: Repeat = Repeat.never,
    ) -> None:
        """Set a reminder: I'll ping you when the time comes.

        Parameters
        ----------
        when
            "2h30m", "tomorrow 9am", "friday 18:00", "eow", "2026-12-31 23:00"... The suggestion shows how I read it.
        text
            What to remind you of.
        repeat
            Repeat the reminder at the same time on your clocks.
        """
        await self.create_reminder(interaction, when, text, repeat=repeat)

    async def remind_me_about_message(self, interaction: Interaction, message: discord.Message) -> None:
        """Message context menu: remind about this message."""
        await interaction.response.send_modal(RemindMeModal(message))

    # --- MANAGING -----------------------------------------------------------------------------------------------------

    @remind_group.command(name="list")
    async def remind_list(self, interaction: Interaction) -> None:
        """Show your reminders, with a button to delete each."""
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
            New time, if any.
        text
            New text, if any.
        repeat
            New repeat, if any.
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
        rule = changes.get("rule", job.rule)
        if parsed is not None:
            changes["when"] = parsed.when
        if rule is not None:
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
            New time.
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

    # --- ARRIVING -----------------------------------------------------------------------------------------------------

    @scheduler.handler(KIND, retry_delay=dt.timedelta(seconds=30))
    async def send_reminder(self, job: Job[ReminderData]) -> None:
        """Deliver a reminder: a reply to its message, or a DM if the channel is gone or closed."""
        author_id = job.user_id or 0
        data = job.data
        late = job.lateness > LATE_AFTER

        embed = discord.Embed(
            color=const.Palette.red_500 if late else const.Palette.purple_500, description=data["text"]
        )
        embed.set_author(name=f"⏰ Reminder #{job.id}")
        embed.add_field(name="Set", value=clock.discord(job.created_at, "R"))
        if job.rule is not None:
            embed.add_field(name="Repeats", value=Repeat.from_rule(job.rule).label)
        if late:
            embed.add_field(
                name="Sorry, I'm late",
                value=f"It was due {clock.discord(job.due_at, 'R')}, but I was offline.",
                inline=False,
            )

        view = discord.ui.View(timeout=None)
        for duration, label in SNOOZE_PRESETS:
            view.add_item(SnoozeButton(duration, author_id, label=label))
        view.add_item(SnoozeButton("custom", author_id, label="Later..."))
        if job.rule is not None:
            view.add_item(DeleteButton(job.id, author_id, label="Stop repeating", emoji="🛑"))
        if data["message_id"] is not None:
            url = message_url(job.guild_id, data["channel_id"], data["message_id"])
            view.add_item(discord.ui.Button(label="Original message", url=url))

        people = [author_id, *data["mentions"]]
        content = " ".join(f"<@{user_id}>" for user_id in people)
        # the text is typed by users but sent by the bot: only the reminder's people may ever be pinged by it
        mentions = discord.AllowedMentions(everyone=False, roles=False, users=[discord.Object(i) for i in people])

        try:
            channel = self.bot.get_channel(data["channel_id"]) or await self.bot.fetch_channel(data["channel_id"])
            assert isinstance(channel, discord.abc.Messageable)
            reference = None
            if data["message_id"] is not None:
                reference = discord.MessageReference(
                    message_id=data["message_id"], channel_id=data["channel_id"], fail_if_not_exists=False
                )
            await channel.send(content, embed=embed, view=view, allowed_mentions=mentions, reference=reference)
        except discord.Forbidden, discord.NotFound, AssertionError:
            logger.info("Reminder {}: channel {} is unusable, sending a DM.", job.id, data["channel_id"])
        else:
            return

        try:
            user = self.bot.get_user(author_id) or await self.bot.fetch_user(author_id)
            await user.send(embed=embed, view=view)
        except discord.Forbidden, discord.NotFound:
            # nowhere to deliver it: retrying won't help
            logger.warning("Reminder {}: neither channel {} nor DMs of {} work.", job.id, data["channel_id"], author_id)


async def setup(bot: Bot) -> None:
    """Load the extension (discord.py entry point)."""
    await bot.add_cog(Reminders(bot))
