"""Reminders.

Notices
-------
* MPL-2.0 License, see LICENSE file for more details.
* Copyright (C) 2020-present @Aluerie.
"""

from __future__ import annotations

import datetime  # ruff: ignore[typing-only-standard-library-import]
import logging
import textwrap
from typing import TYPE_CHECKING, NotRequired, Self, TypedDict, override

import discord
from discord import app_commands
from discord.ext import commands

from core import Cog, Modal, View
from shared import clock, errors, fmt
from utils import const, pages, prompts, times

if TYPE_CHECKING:
    from core import Bot, Interaction, Timer

    class RemindTimerData(TypedDict):
        author_id: int
        channel_id: int
        text: str
        message_id: int
        guild_id: NotRequired[int | None]  # timers created before this key was introduced don't have it


__all__ = ("Reminders",)

log = logging.getLogger(__name__)
log.setLevel(logging.INFO)

MAX_TEXT_LENGTH = 1500
MAX_LIST_TEXT_LENGTH = 200
"""Reminder texts are shortened to this in `/remind list`, so a page of them fits into an embed description."""


def reminder_url(*, guild_id: int | None, channel_id: int, message_id: int) -> str:
    """Make a link to a message: guild-less (DMs) messages live under "@me"."""
    return f"https://discord.com/channels/{guild_id or '@me'}/{channel_id}/{message_id}"


class SnoozeModal(Modal, title="Snooze"):
    """Modal asking for how long a fired reminder should be snoozed."""

    duration = discord.ui.TextInput(label="Duration", placeholder="10 minutes", default="10 minutes", min_length=2)

    def __init__(self, parent: ReminderView, timer: Timer[RemindTimerData]) -> None:
        super().__init__()
        self.parent: ReminderView = parent
        self.timer: Timer[RemindTimerData] = timer

    @override
    async def on_submit(self, interaction: Interaction) -> None:
        tz_manager = interaction.client.tz_manager
        tzinfo = await tz_manager.get_tzinfo(interaction.user.id)
        try:
            when = times.FutureTime(str(self.duration), now=interaction.created_at, tzinfo=tzinfo).dt
        except errors.BadUserInputError:
            msg = 'Duration could not be parsed, sorry. Try something like "5 minutes" or "1 hour"'
            await interaction.response.send_message(msg, ephemeral=True)
            return

        await interaction.client.timers.create(
            event=self.timer.event,
            expires_at=when,
            created_at=self.timer.created_at,  # still the reminder that was originally set at that time
            timezone=await tz_manager.get_timezone(interaction.user.id) or "UTC",
            data=self.timer.data,
        )

        self.parent.snooze.disabled = True
        await interaction.response.edit_message(view=self.parent)

        delta = clock.human_datetime_diff(when, relative_to=interaction.created_at)
        text = self.timer.data["text"]
        msg = f"Alright {interaction.user.mention}, I've snoozed your reminder for {delta}: {text}"
        await interaction.followup.send(msg, ephemeral=True, allowed_mentions=discord.AllowedMentions.none())


class ReminderView(View):
    """Buttons under a fired reminder: a link to the original message and a snooze button."""

    def __init__(self, *, url: str, timer: Timer[RemindTimerData], author_id: int) -> None:
        super().__init__(author_id=author_id, timeout=300)
        self.timer: Timer[RemindTimerData] = timer
        self.add_item(discord.ui.Button(url=url, label="Go to original message"))

    @discord.ui.button(label="Snooze", style=discord.ButtonStyle.blurple)
    async def snooze(self, interaction: Interaction, _: discord.ui.Button[Self]) -> None:
        """Ask for how long to snooze the reminder."""
        await interaction.response.send_modal(SnoozeModal(self, self.timer))


class Reminders(Cog):
    """Remind yourself of something at sometime."""

    remind_group = app_commands.Group(
        name="remind",
        description="Set reminders to ping you when the time comes.",
    )

    @remind_group.command(name="set")
    async def reminder_set(
        self,
        interaction: Interaction,
        when: app_commands.Transform[datetime.datetime, times.TimeTransformer],
        text: str = "...",
    ) -> None:
        """Set a reminder to remind you of something at a specific time.

        Parameters
        ----------
        when
            When to be reminded of something: "10m", "2 days", "tomorrow at 3pm", etc. In your timezone if you set it.
        text
            What to be reminded of.
        """
        if len(text) > MAX_TEXT_LENGTH:
            msg = f"Reminder must be at most {MAX_TEXT_LENGTH} characters long."
            raise errors.BadUserInputError(msg)

        zone = await self.bot.tz_manager.get_timezone(interaction.user.id)

        delta = clock.human_datetime_diff(when, relative_to=interaction.created_at)
        embed = discord.Embed(
            color=interaction.user.color,
            description=f"in {delta} — {clock.discord(when, 'd', 't', 'R')}\n{text}",
        ).set_author(
            name=f"Reminder for {interaction.user.display_name} is created",
            icon_url=interaction.user.display_avatar,
        )
        if zone is None:
            mention = self.bot.tree.find_mention_for("timezone set") or "`/timezone set`"
            embed.add_field(
                name="P.S.",
                value=f"\N{ELECTRIC LIGHT BULB} You can set your timezone with {mention}",
            )

        # The reminder points to this very response message, so it has to be sent before the timer is created.
        await interaction.response.send_message(embed=embed)
        response = await interaction.original_response()

        data: RemindTimerData = {
            "author_id": interaction.user.id,
            "channel_id": response.channel.id,
            "guild_id": interaction.guild_id,
            "text": text,
            "message_id": response.id,
        }
        try:
            await self.bot.timers.create(
                event="reminder",
                expires_at=when,
                created_at=interaction.created_at,
                timezone=zone or "UTC",
                data=data,
            )
        except Exception:
            # do not leave the user thinking everything is fine
            await interaction.edit_original_response(content="Failed to create the reminder, sorry!", embed=None)
            raise

    @remind_group.command(name="list")
    async def remind_list(self, interaction: Interaction) -> None:
        """Show a list of your current reminders."""
        timers: list[Timer[RemindTimerData]] = await self.bot.timers.fetch_by_kwargs(
            "reminder", author_id=interaction.user.id
        )

        entries = [
            f"\N{BLACK CIRCLE} {timer.id}: {clock.discord(timer.expires_at, 'd', 't', 'R')}\n"
            f"{textwrap.shorten(timer.data['text'], width=MAX_LIST_TEXT_LENGTH)}"
            for timer in timers
        ]
        paginator = pages.EmbedDescriptionPaginator(
            interaction,
            entries,
            per_page=10,
            empty_description="You do not have any reminders.",
            template={
                "color": interaction.user.color.value,
                "author": {
                    "name": f"{interaction.user.display_name}'s Reminders list",
                    "icon_url": interaction.user.display_avatar.url,
                },
            },
        )
        await paginator.start()

    @remind_group.command(name="delete")
    async def remind_delete(self, interaction: Interaction, reminder_id: int) -> None:
        """Delete a reminder by its ID.

        To get a reminder ID, use the reminder list command.

        You must own the reminder to delete it, obviously.

        Parameters
        ----------
        reminder_id
            ID of the reminder to delete.
        """
        deleted = await self.bot.timers.delete_by_id(reminder_id, "reminder", author_id=interaction.user.id)
        if not deleted:
            embed = discord.Embed(
                color=const.Palette.red_500,
                description="Could not delete any reminders with that ID.",
            ).set_author(name="NotFound")
            await interaction.response.send_message(embed=embed, ephemeral=True)
            return

        embed = discord.Embed(description="Successfully deleted reminder.", color=const.Palette.purple_500)
        await interaction.response.send_message(embed=embed)

    @remind_group.command(name="clear")
    async def reminder_clear(self, interaction: Interaction) -> None:
        """Clear all reminders you have set."""
        total = len(await self.bot.timers.fetch_by_kwargs("reminder", author_id=interaction.user.id))
        if total == 0:
            embed = discord.Embed(color=interaction.user.color, description="You do not have any reminders to delete.")
            await interaction.response.send_message(embed=embed, ephemeral=True)
            return

        confirm_embed = discord.Embed(
            color=interaction.user.color,
            description=f"Are you sure you want to delete {fmt.plural(total):reminder}?",
        )
        if not await prompts.confirm(interaction, embed=confirm_embed):
            return

        deleted = await self.bot.timers.delete_by_kwargs("reminder", author_id=interaction.user.id)
        embed = discord.Embed(
            color=interaction.user.color,
            description=f"Successfully deleted {fmt.plural(deleted):reminder}.",
        )
        # `confirm` has used up the initial response
        await interaction.followup.send(embed=embed)

    @commands.Cog.listener()
    async def on_reminder_timer_complete(self, timer: Timer[RemindTimerData]) -> None:
        """Send the reminder when its time comes."""
        log.debug('Timer Event "on_reminder_timer_complete" starts now')
        try:
            await self._send_reminder(timer)
        finally:
            # whatever happened (the channel was deleted, the user blocked the bot, ...) a reminder is never retried
            await self.bot.timers.cleanup(timer.id)

    async def _send_reminder(self, timer: Timer[RemindTimerData]) -> None:
        """Deliver the reminder to its channel; if that's impossible then to the author's DMs."""
        author_id = timer.data["author_id"]
        channel_id = timer.data["channel_id"]
        message_id = timer.data["message_id"]
        text = timer.data["text"]

        content = f"<@{author_id}>, {discord.utils.format_dt(timer.created_at, style='R')}\n{text}"
        # The text is typed by the user, but the bot sends it: only the author may ever be pinged by it
        # (not `@everyone`, not roles that the user wouldn't be allowed to ping themselves).
        mentions = discord.AllowedMentions(everyone=False, roles=False, users=[discord.Object(author_id)])

        channel = self.bot.get_channel(channel_id)
        if channel is None:
            try:
                channel = await self.bot.fetch_channel(channel_id)
            except discord.HTTPException:
                log.info("Reminder channel %s is gone, trying to DM the author %s instead.", channel_id, author_id)

        # (guild_id wasn't stored by earlier versions: take it from the channel then)
        guild_id = timer.data.get("guild_id") or getattr(getattr(channel, "guild", None), "id", None)
        url = reminder_url(guild_id=guild_id, channel_id=channel_id, message_id=message_id)
        view = ReminderView(url=url, timer=timer, author_id=author_id)

        if isinstance(channel, discord.abc.Messageable):
            try:
                view.message = await channel.send(content, view=view, allowed_mentions=mentions)
            except discord.HTTPException:
                log.info("Could not send reminder to the channel %s.", channel_id, exc_info=True)
            else:
                return

        # the channel is gone or we can't speak there anymore
        try:
            user = self.bot.get_user(author_id) or await self.bot.fetch_user(author_id)
            view.message = await user.send(content, view=view, allowed_mentions=mentions)
        except discord.HTTPException:
            log.warning(
                "Discarding reminder %s: neither channel %s nor DMs of %s work.", timer.id, channel_id, author_id
            )


async def setup(bot: Bot) -> None:
    """Load the extension (discord.py entry point)."""
    await bot.add_cog(Reminders(bot))
