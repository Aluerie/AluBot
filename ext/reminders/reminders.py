from __future__ import annotations

import datetime  # noqa: TCH003
import logging
import textwrap
from typing import TYPE_CHECKING, Annotated, Any, TypedDict, override

import discord
from discord import app_commands
from discord.ext import commands

from utils import AluContext, const, formats, pages, times

from ._base import RemindersCog

if TYPE_CHECKING:
    from bot import AluBot, Timer

    class RemindTimerData(TypedDict):
        author_id: int
        channel_id: int
        text: str
        message_id: int


log = logging.getLogger(__name__)
log.setLevel(logging.INFO)


class SnoozeModal(discord.ui.Modal, title="Snooze"):
    duration = discord.ui.TextInput(label="Duration", placeholder="10 minutes", default="10 minutes", min_length=2)

    def __init__(self, parent: ReminderView, timer: Timer[RemindTimerData]) -> None:
        super().__init__()
        self.parent: ReminderView = parent
        self.timer: Timer[RemindTimerData] = timer

    @override
    async def on_submit(self, interaction: discord.Interaction[AluBot]) -> None:
        try:
            when = times.FutureTime(str(self.duration)).dt
        except commands.BadArgument:  # Exception
            msg = 'Duration could not be parsed, sorry. Try something like "5 minutes" or "1 hour"'
            await interaction.response.send_message(msg, ephemeral=True)
            return

        self.parent.snooze.disabled = True
        await interaction.response.edit_message(view=self.parent)

        zone = await interaction.client.tz_manager.get_timezone(interaction.user.id)
        refreshed = await interaction.client.create_timer(
            event=self.timer.event,
            expires_at=when,
            created_at=interaction.created_at,
            timezone=zone or "UTC",
            data=self.timer.data,
        )
        author_id = self.timer.data.get("author_id")
        text = self.timer.data.get("text")
        delta = formats.human_timedelta(when, source=refreshed.created_at)
        msg = f"Alright <@{author_id}>, I've snoozed your reminder for {delta}: {text}"
        await interaction.followup.send(msg, ephemeral=True)


class SnoozeButton(discord.ui.Button["ReminderView"]):
    def __init__(self, cog: Reminder, timer: Timer[RemindTimerData]) -> None:
        super().__init__(label="Snooze", style=discord.ButtonStyle.blurple)
        self.timer: Timer[RemindTimerData] = timer
        self.cog: Reminder = cog

    @override
    async def callback(self, interaction: discord.Interaction) -> Any:
        assert self.view is not None
        await interaction.response.send_modal(SnoozeModal(self.view, self.timer))


class ReminderView(discord.ui.View):
    message: discord.Message

    def __init__(self, *, url: str, timer: Timer[RemindTimerData], cog: Reminder, author_id: int) -> None:
        super().__init__(timeout=300)
        self.author_id: int = author_id
        self.snooze = SnoozeButton(cog, timer)
        self.add_item(discord.ui.Button(url=url, label="Go to original message"))
        self.add_item(self.snooze)

    @override
    async def interaction_check(self, interaction: discord.Interaction) -> bool:
        if interaction.user.id != self.author_id:
            await interaction.response.send_message("This snooze button is not for you, sorry!", ephemeral=True)
            return False
        return True

    @override
    async def on_timeout(self) -> None:
        self.snooze.disabled = True
        await self.message.edit(view=self)


class Reminder(RemindersCog, emote=const.Emote.DankG):
    """Remind yourself of something at sometime."""

    @override
    async def cog_load(self) -> None:
        self.bot.initialize_tz_manager()

    async def remind_helper(self, ctx: AluContext, *, dt: datetime.datetime, text: str) -> None:
        """Remind helper so we don't duplicate."""
        if len(text) >= 1500:
            await ctx.send("Reminder must be fewer than 1500 characters.")
            return

        zone = await self.bot.tz_manager.get_timezone(ctx.author.id)
        data: RemindTimerData = {
            "author_id": ctx.author.id,
            "channel_id": ctx.channel.id,
            "text": text,
            "message_id": ctx.message.id,
        }
        timer = await self.bot.create_timer(
            event="reminder",
            expires_at=dt,
            created_at=ctx.message.created_at,
            timezone=zone or "UTC",
            data=data,
        )
        delta = formats.human_timedelta(dt, source=timer.created_at)
        e = discord.Embed(colour=ctx.author.colour)
        e.set_author(name=f"Reminder for {ctx.author.display_name} is created", icon_url=ctx.author.display_avatar)
        e.description = f"in {delta} — {formats.format_dt_tdR(dt)}\n{text}"
        if zone is None:
            e.set_footer(text=f'\N{ELECTRIC LIGHT BULB} You can set your timezone with "{ctx.prefix}timezone set')
        await ctx.reply(embed=e)

    @commands.hybrid_group(aliases=["reminder", "remindme"], usage="<when>")
    async def remind(
        self,
        ctx: AluContext,
        *,
        when: Annotated[times.FriendlyTimeResult, times.UserFriendlyTime(commands.clean_content, default="...")],
    ) -> None:
        """Main group of remind command. Just a way to make an alias for 'remind me' with a space."""
        await self.remind_helper(ctx, dt=when.dt, text=when.arg)

    @remind.app_command.command(name="set")
    @app_commands.describe(when="When to be reminded of something, in GMT", text="What to be reminded of")
    async def reminder_set(
        self,
        interaction: discord.Interaction[AluBot],
        when: app_commands.Transform[datetime.datetime, times.TimeTransformer],
        text: str = "...",
    ) -> None:
        """Sets a reminder to remind you of something at a specific time."""
        ctx = await AluContext.from_interaction(interaction)
        await self.remind_helper(ctx, dt=when, text=text)

    @remind.command(name="me", with_app_command=False)
    async def remind_me(
        self,
        ctx: AluContext,
        *,
        when_and_what: Annotated[
            times.FriendlyTimeResult, times.UserFriendlyTime(commands.clean_content, default="...")
        ],
    ) -> None:
        """Reminds you of something after a certain amount of time. \
        The input can be any direct date (i.e. DD/MM/YYYY) or a human \
        readable offset. Examples:
        * "next thursday at 3pm do something funny"
        * "do the dishes tomorrow"
        * "in 50 minutes do the thing"
        * "2d unmute someone"
        Times are assumed in UTC.
        """
        await self.remind_helper(ctx, dt=when_and_what.dt, text=when_and_what.arg)

    @remind.command(name="list", ignore_extra=False)
    async def remind_list(self, ctx: AluContext) -> None:
        """Shows a list of your current reminders."""
        query = """
            SELECT id, expires, extra #>> '{args,2}'
            FROM timers
            WHERE event = 'reminder'
            AND data #>> '{author_id}' = $1
            ORDER BY expires
        """
        records = await ctx.pool.fetch(query, str(ctx.author.id))

        string_list = []
        for _id, expires, message in records:
            shorten = textwrap.shorten(message, width=512)
            string_list.append(f"\N{BLACK CIRCLE} {_id}: {formats.format_dt_tdR(expires)}\n{shorten}")

        pgs = pages.EnumeratedPaginator(
            ctx,
            string_list,
            per_page=10,
            author_name=f"{ctx.author.display_name}'s Reminders list",
            author_icon=ctx.author.display_avatar.url,
            colour=ctx.author.colour,
        )
        await pgs.start()

    # TODO: finish this?
    # async def remind_delete_id_autocomplete(
    #         self,
    #         interaction: discord.Interaction,
    #         current: str
    # ) -> List[app_commands.Choice[str]]:
    #     """idk if it is a good idea"""
    #     query = """ SELECT id, expires, extra #>> '{args,2}'
    #                 FROM reminders
    #                 WHERE event = 'reminder'
    #                 AND data #>> '{author_id}' = $1
    #                 ORDER BY similarity(extra #>> '{args, 2}', $2) DESC
    #                 LIMIT 10
    #             """
    #     records = await self.bot.pool.fetch(query, str(ntr.user.id), current)
    #     choice_list = [
    #         (_id, f"{_id}: ({expires.strftime('%d/%b/%y')}) {textwrap.shorten(message, width=100)}")
    #         for _id, expires, message in records
    #     ]
    #     return [app_commands.Choice(name=m, value=n) for n, m in choice_list if current.lower() in m.lower()]

    @remind.command(name="delete", aliases=["remove", "cancel"], ignore_extra=True)
    # @app_commands.autocomplete(id=remind_delete_id_autocomplete)  # type: ignored
    # @app_commands.describe(id='either input a number of reminder id or choose it from suggestion^')
    async def remind_delete(self, ctx: AluContext, *, id: int) -> None:
        """Deletes a reminder by its ID.

        To get a reminder ID, use the reminder list command or autocomplete for slash command.

        You must own the reminder to delete it, obviously.
        """
        query = """
            DELETE FROM timers
            WHERE id=$1
            AND event = 'reminder'
            AND data #>> '{author_id}' = $2;
        """
        status = await ctx.pool.execute(query, id, str(ctx.author.id))
        if status == "DELETE 0":
            e = discord.Embed(description="Could not delete any reminders with that ID.", colour=const.Colour.maroon)
            e.set_author(name="IDError")
            await ctx.reply(embed=e)
            return

        # if the current timer is being deleted
        if self.bot._current_timer and self.bot._current_timer.id == id:
            # cancel the task and re-run it
            self.bot.rerun_the_task()

        e = discord.Embed(description="Successfully deleted reminder.", colour=const.Colour.blueviolet)
        await ctx.reply(embed=e)

    @remind.command(name="clear", ignore_extra=False)
    async def reminder_clear(self, ctx: AluContext) -> None:
        """Clears all reminders you have set."""
        # For UX purposes this has to be two queries.
        query = """
            SELECT COUNT(*) FROM timers
            WHERE event = 'reminder'
            AND data #>> '{author_id}' = $1;
        """
        author_id = str(ctx.author.id)
        total: int = await ctx.pool.fetchval(query, author_id)
        if total == 0:
            no_reminders_embed = discord.Embed(
                colour=ctx.author.colour,
                description="You do not have any reminders to delete.",
            )
            await ctx.reply(embed=no_reminders_embed)
            return

        confirm_embed = discord.Embed(
            colour=ctx.author.colour,
            description=f"Are you sure you want to delete {formats.plural(total):reminder}?",
        )
        if not await ctx.bot.disambiguator.confirm(ctx, embed=confirm_embed):
            return

        query = """
            DELETE FROM timers
            WHERE event = 'reminder'
            AND data #>> '{author_id}' = $1;
        """
        await ctx.pool.execute(query, author_id)

        # Check if the current timer is the one being cleared and cancel it if so
        current_timer = self.bot._current_timer
        if current_timer and current_timer.event == "reminder" and current_timer.data:
            author_id = current_timer.data.get("author_id")
            if author_id == ctx.author.id:
                self.bot.rerun_the_task()

        response_embed = discord.Embed(
            colour=ctx.author.colour,
            description=f"Successfully deleted {formats.plural(total):reminder}.",
        )
        await ctx.reply(embed=response_embed)

    @commands.Cog.listener()
    async def on_reminder_timer_complete(self, timer: Timer[RemindTimerData]) -> None:
        log.debug('Timer Event "on_reminder_timer_complete" starts now')

        author_id = timer.data["author_id"]
        channel_id = timer.data["channel_id"]
        text = timer.data["text"]
        message_id = timer.data["message_id"]

        try:
            channel = self.bot.get_channel(channel_id) or (await self.bot.fetch_channel(channel_id))
        except discord.HTTPException:
            log.warning("Discarding channel %s as it's not found.", channel_id)
            return

        guild_id = channel.guild.id if isinstance(channel, (discord.TextChannel, discord.Thread)) else "@me"
        content = f"<@{author_id}>, {timer.format_dt_R}\n{text}"
        view = discord.utils.MISSING

        if message_id:
            url = f"https://discord.com/channels/{guild_id}/{channel.id}/{message_id}"
            view = ReminderView(url=url, timer=timer, cog=self, author_id=author_id)

        try:
            msg = await channel.send(content, view=view)  # type: ignore
        except discord.HTTPException:
            return
        else:
            if view is not discord.utils.MISSING:
                view.message = msg


async def setup(bot: AluBot) -> None:
    await bot.add_cog(Reminder(bot))
