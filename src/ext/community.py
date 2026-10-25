"""Community Features.

Notices
-------
* MPL-2.0 License, see LICENSE file for more details.
* Copyright (C) 2020-present @Aluerie.
"""

from __future__ import annotations

import asyncio
import contextlib
import datetime as dt
import functools
import logging
import random
import time
from io import BytesIO
from pathlib import Path
from typing import TYPE_CHECKING, ClassVar, Final, override

import discord
from discord.ext import commands
from PIL import Image, ImageDraw, ImageFont

from config import env
from core import Cog, Context
from shared import clock, globs
from shared.concepts import loop
from utils import const

if TYPE_CHECKING:
    from collections.abc import Sequence

    from core import Bot
    from shared.typings.dpy import SendKwargs


log = logging.getLogger(__name__)
log.setLevel(logging.INFO)

ASSETS = Path(__file__).resolve().parents[2] / "assets"

# Welcome image constants
MARGIN = 10
MASK_SUPERSAMPLING = 4
NAME_FONT = "Inter-Black-slnt=0.ttf"
NAME_FONT_SIZE = 110
NAME_FONT_MIN_SIZE = 24
WELCOME_FONT = "MonsieurLaDoulaise-Regular.ttf"
WELCOME_FONT_SIZE = 90

# a kick or ban also dispatches `on_member_remove`, so a leave is only reported if no kick/ban entry showed up
REMOVE_GRACE_SECONDS = 2.0
MODERATION_WINDOW_SECONDS = 10.0

# action -> (title, past tense verb, colour)
MODERATION_ACTIONS: dict[discord.AuditLogAction, tuple[str, str, discord.Colour]] = {
    discord.AuditLogAction.kick: ("Member kicked", "kicked from", discord.Colour.orange()),
    discord.AuditLogAction.ban: ("Member banned", "banned from", discord.Colour.red()),
    discord.AuditLogAction.unban: ("Member unbanned", "unbanned from", discord.Colour.green()),
}


@functools.cache
def _font(filename: str, size: int) -> ImageFont.FreeTypeFont:
    return ImageFont.truetype(str(ASSETS / "fonts" / filename), size)


def _fit_font(text: str, filename: str, size: int, max_width: float) -> ImageFont.FreeTypeFont:
    """Return the largest font (at most `size`) in which `text` fits into `max_width`."""
    while size > NAME_FONT_MIN_SIZE and _font(filename, size).getlength(text) > max_width:
        size -= 4
    return _font(filename, size)


def _circle_mask(size: int) -> Image.Image:
    """Make an anti-aliased circular mask by drawing large and downscaling."""
    big_size = size * MASK_SUPERSAMPLING
    big = Image.new("L", (big_size, big_size), 0)
    ImageDraw.Draw(big).ellipse((0, 0, big_size - 1, big_size - 1), fill=255)
    return big.resize((size, size), Image.Resampling.LANCZOS)


def _build_welcome_image(avatar_bytes: bytes, display_name: str) -> Image.Image:
    """Blocking part of the welcome image. Run it in a thread."""
    with Image.open(ASSETS / "images" / "profile" / "welcome.png") as template:
        canvas = template.convert("RGBA")
    canvas_w, canvas_h = canvas.size

    # the avatar is a circle as tall as the canvas, centered horizontally
    avatar_size = canvas_h
    with Image.open(BytesIO(avatar_bytes)) as raw_avatar:
        avatar = raw_avatar.convert("RGBA").resize((avatar_size, avatar_size), Image.Resampling.LANCZOS)
    left = (canvas_w - avatar_size) // 2
    canvas.paste(avatar, (left, 0), _circle_mask(avatar_size))

    draw = ImageDraw.Draw(canvas)
    right, bottom = canvas_w - MARGIN, canvas_h - MARGIN

    # the name must fit into the free space to the right of the avatar
    max_name_width = left - 2 * MARGIN
    name_font = _fit_font(display_name, NAME_FONT, NAME_FONT_SIZE, max_name_width)
    draw.text((right, bottom), display_name, fill="white", font=name_font, anchor="rd")
    name_top = draw.textbbox((right, bottom), display_name, font=name_font, anchor="rd")[1]

    welcome_font = _font(WELCOME_FONT, WELCOME_FONT_SIZE)
    draw.text((right, name_top - MARGIN), "Welcome !", fill="white", font=welcome_font, anchor="rd")
    return canvas


class Community(Cog):
    """Community Features."""

    HIDEOUT_STEAM_DB_CHANNEL_ID: Final = const.ChannelId(873430376033452053)
    HIDEOUT_SPAM_CHANNEL_ID: Final = const.ChannelId(970823670702411810)

    RULES_INFO_CHANNEL_ID: Final = const.ChannelId(724996010169991198)
    ROLE_SELECTION_CHANNEL_ID: Final = const.ChannelId(1099742867947262093)
    WELCOME_CHANNEL_ID: Final = const.ChannelId(725000501690630257)
    GENERAL_CHANNEL_ID: Final = const.ChannelId(702561315478044807)
    BOT_SPAM_CHANNEL_ID: Final = const.ChannelId(724986090632642653)

    LIVE_STREAMER_ROLE_ID: Final = const.RoleId(760082390059581471)
    BOTS_ROLE_ID: Final = const.RoleId(724981475099017276)

    CATEGORY_ROLES: Final[tuple[discord.Object, ...]] = tuple(
        discord.Object(role_id)
        for role_id in (
            856589983707693087,  # moderation
            852199351808032788,  # activity
            852193537067843634,  # subscription
            852199851840372847,  # special
            851786344354938880,  # games
            852192240306618419,  # notification
            727492782196916275,  # plebs
        )
    )

    MENTION_REACTIONS: ClassVar[tuple[str, ...]] = ("❔", "❕", "🤔")
    JOKE_CHANCE: ClassVar[float] = 1 / 300
    JOKE_MIN_WORDS: ClassVar[int] = 3
    JOKE_MAX_WORDS: ClassVar[int] = 12

    @override
    async def cog_load(self) -> None:
        self.restart_clean_up.start()
        await super().cog_load()

    @override
    async def cog_unload(self) -> None:
        self.restart_clean_up.cancel()
        await super().cog_unload()

    ####################################################################################################################
    # CHATTER
    ####################################################################################################################

    async def _react_to_mentions(self, message: discord.Message) -> None:
        """React with confused emojis if the bot is mentioned."""
        if self.bot.user not in message.mentions:
            return
        with contextlib.suppress(discord.HTTPException):
            for r in self.MENTION_REACTIONS:
                await message.add_reaction(r)

    async def _your_life_joke(self, message: discord.Message) -> None:
        """Occasionally reply with "Your life ..." replacing the first two words."""
        words = message.content.split()
        if not (self.JOKE_MIN_WORDS <= len(words) <= self.JOKE_MAX_WORDS):
            return
        if random.random() >= self.JOKE_CHANCE:
            return
        await message.channel.send("Your life " + " ".join(words[2:]), allowed_mentions=discord.AllowedMentions.none())

    @commands.Cog.listener("on_message")
    async def chatter(self, message: discord.Message) -> None:
        """React and respond to community member's messages."""
        if message.guild is None or message.guild.id != const.Guild.community:
            return
        if message.author.bot or message.webhook_id:
            return
        await self._react_to_mentions(message)
        await self._your_life_joke(message)

    ####################################################################################################################
    # STEAM DB REPOSTING
    ####################################################################################################################

    @discord.utils.cached_property
    def news_webhook(self) -> discord.Webhook:
        """Webhook to send Dota 2 News to."""
        webhook_url = env.WEBHOOK_DOTANEWS if not self.bot.test else env.WEBHOOK_SPAM
        return self.bot.webhook_from_url(webhook_url)

    @commands.Cog.listener("on_message")
    async def filter_steam_db_messages(self, message: discord.Message) -> None:
        """Filter SteamDB messages from uninteresting ones.

        That channel contains all kind of updates, but we are only interested in blogpost ones.

        Warning
        -------
        Reposting from steamDB resources is rude and copyright-tier bad.
        Please, think of other ways to implement this (e.g. ISteamNews/GetNewsForApp or RSS feed)
        """
        if message.channel.id != self.HIDEOUT_STEAM_DB_CHANNEL_ID:
            return
        if "https://steamcommunity.com" not in message.content:
            return

        msg = await self.news_webhook.send(content=f"# {message.content}", wait=True)
        await msg.publish()

    ####################################################################################################################
    # LIVE STREAMER
    ####################################################################################################################

    @staticmethod
    def _is_streaming(member: discord.Member) -> bool:
        """Return whether the member has a streaming activity on any platform."""
        return any(isinstance(a, discord.Streaming) for a in member.activities)

    async def _sync_streamer_role(self, member: discord.Member, role: discord.Role) -> None:
        """Add or remove the streamer role so it matches the member's streaming activity.

        Parameters
        ----------
        member
            The member to update.
        role
            The @LiveStreamer role.
        """
        is_streaming = self._is_streaming(member)
        has_role = role in member.roles

        if is_streaming and not has_role:
            await member.add_roles(role, reason="Started streaming")
        elif not is_streaming and has_role:
            await member.remove_roles(role, reason="Stopped streaming")

    @commands.Cog.listener(name="on_presence_update")
    async def community_streamer_role_management(self, before: discord.Member, after: discord.Member) -> None:
        """Detect community members who are currently streaming and grant them @LiveStreamer role."""
        if after.guild.id != const.Guild.community or after.bot:
            return
        if self._is_streaming(before) == self._is_streaming(after):
            return
        await self._sync_streamer_role(after, self.bot.get_role(after.guild.id, self.LIVE_STREAMER_ROLE_ID))

    @loop(count=1, wait_for_ready=True)
    async def restart_clean_up(self) -> None:
        """Resync @LiveStreamer role after a restart.

        The bot can be offline for a long time, so presence events are missed.
        """
        role = self.bot.get_role(const.Guild.community, self.LIVE_STREAMER_ROLE_ID)
        for member in role.guild.members:
            if not member.bot:
                await self._sync_streamer_role(member, role)

    ####################################################################################################################
    # LOGGER
    ####################################################################################################################

    @discord.utils.cached_property
    def bot_spam_channel(self) -> discord.TextChannel:
        """Bot spam channel."""
        channel_id = self.BOT_SPAM_CHANNEL_ID if not self.bot.test else self.HIDEOUT_SPAM_CHANNEL_ID
        return self.bot.get_text_channel(channel_id)

    @staticmethod
    def _emoji_embed(
        title: str,
        color: int,
        emoji: discord.Emoji,
        description: str,
        actor: discord.Member | discord.User | None,
    ) -> discord.Embed:
        embed = discord.Embed(color=color, title=title, description=description).set_thumbnail(url=emoji.url)
        if actor is not None:
            embed.set_author(name=actor.display_name, icon_url=actor.display_avatar.url)
        elif emoji.managed:
            embed.set_author(name="Managed by an integration", icon_url=globs.Logo.Twitch)
        return embed

    async def _find_emoji_actor(
        self, guild: discord.Guild, action: discord.AuditLogAction, emoji: discord.Emoji
    ) -> discord.Member | discord.User | None:
        if emoji.managed:
            return None  # synced by an integration, so there's no "actor"

        cutoff = clock.utcnow() - dt.timedelta(seconds=15)
        for _ in range(3):
            try:
                async for entry in guild.audit_logs(limit=10, action=action):
                    if entry.created_at < cutoff:
                        break
                    if entry.target is not None and entry.target.id == emoji.id:
                        return entry.user
            except discord.Forbidden:
                log.warning("Missing View Audit Log permission in %s", guild)
                return None
            await asyncio.sleep(1)
        return None

    @commands.Cog.listener()
    async def on_guild_emojis_update(
        self,
        guild: discord.Guild,
        before: Sequence[discord.Emoji],
        after: Sequence[discord.Emoji],
    ) -> None:
        """Log emoji additions, removals, and edits to the bot spam channel."""
        expected_guild = const.Guild.hideout if self.bot.test else const.Guild.community
        if guild.id != expected_guild:
            return

        old = {e.id: e for e in before}
        new = {e.id: e for e in after}

        for emoji_id in new.keys() - old.keys():
            emoji = new[emoji_id]
            actor = await self._find_emoji_actor(guild, discord.AuditLogAction.emoji_create, emoji)
            embed = self._emoji_embed("Emote added", 0x00FF7F, emoji, f"`:{emoji.name}:`", actor)
            await self.bot_spam_channel.send(embed=embed)

        for emoji_id in old.keys() - new.keys():
            emoji = old[emoji_id]
            actor = await self._find_emoji_actor(guild, discord.AuditLogAction.emoji_delete, emoji)
            embed = self._emoji_embed("Emote removed", 0xFF4500, emoji, f"`:{emoji.name}:`", actor)
            await self.bot_spam_channel.send(embed=embed)

        for emoji_id in old.keys() & new.keys():
            b, a = old[emoji_id], new[emoji_id]
            changes: list[str] = []
            if b.name != a.name:
                changes.append(f"**Name:** `{b.name}` -> `{a.name}`")
            if {r.id for r in b.roles} != {r.id for r in a.roles}:
                before_roles = ", ".join(r.mention for r in b.roles) or "everyone"
                after_roles = ", ".join(r.mention for r in a.roles) or "everyone"
                changes.append(f"**Roles:** {before_roles} -> {after_roles}")
            if changes:
                actor = await self._find_emoji_actor(guild, discord.AuditLogAction.emoji_update, a)
                embed = self._emoji_embed("Emote updated", 0xFFD700, a, "\n".join(changes), actor)
                await self.bot_spam_channel.send(embed=embed)

    @commands.Cog.listener()
    async def on_user_update(self, before: discord.User, after: discord.User) -> None:
        """Log changes to a user's global profile to the bot spam channel (if they are a community member)."""
        guild = self.bot.get_guild(const.Guild.community)
        if guild is None or guild.get_member(after.id) is None:
            return

        embed = discord.Embed(
            title=f"User updated {const.Emoji.PepoDetective}",
            description=after.mention,
            colour=after.color,
        ).set_author(name=str(after), icon_url=after.display_avatar.url)

        changed = False

        if before.name != after.name:
            changed = True
            embed.add_field(
                name="Username",
                value=f"`{before.name}` → `{after.name}`",
                inline=False,
            )

        if before.global_name != after.global_name:
            changed = True
            embed.add_field(
                name="Global Display name",
                value=f"`{before.global_name}` → `{after.global_name}`",
                inline=False,
            )

        if before.avatar != after.avatar:
            changed = True
            embed.add_field(
                name="Avatar",
                value="Before (thumbnail to the right) → (After) (image below)",
                inline=False,
            )
            embed.set_thumbnail(url=before.display_avatar.url)
            embed.set_image(url=after.display_avatar.url)

        if not changed:
            return

        await self.bot_spam_channel.send(embed=embed, allowed_mentions=discord.AllowedMentions.none())

    @commands.Cog.listener()
    async def on_member_update(self, before: discord.Member, after: discord.Member) -> None:
        """Log changes to a community member's guild profile to the bot spam channel."""
        if before.guild.id != const.Guild.community:
            return
        embed = discord.Embed(
            title=f"Member updated {const.Emoji.PepoDetective}",
            description=after.mention,
            colour=after.colour,
        ).set_author(name=str(after), icon_url=after.display_avatar.url)

        changed = False

        if before.nick != after.nick:
            changed = True
            embed.add_field(
                name="Nickname",
                value=f"`{before.nick}` → `{after.nick}`",
                inline=False,
            )

        before_roles = set(before.roles)
        after_roles = set(after.roles)
        if added := after_roles - before_roles:
            changed = True
            embed.add_field(
                name="Roles added",
                value=", ".join(role.mention for role in sorted(added, reverse=True)),
                inline=False,
            )
        if removed := before_roles - after_roles:
            changed = True
            embed.add_field(
                name="Roles removed",
                value=", ".join(role.mention for role in sorted(removed, reverse=True)),
                inline=False,
            )

        if before.timed_out_until != after.timed_out_until:
            changed = True
            if after.timed_out_until is None:
                timeout = "Timeout removed"
            else:
                timeout = f"Timed out until {clock.discord(after.timed_out_until)}"
            embed.add_field(name="Timeout", value=timeout, inline=False)

        if before.premium_since != after.premium_since:
            changed = True
            embed.add_field(
                name="Server boost",
                value="Started boosting" if after.premium_since else "Stopped boosting",
                inline=False,
            )

        if before.guild_avatar != after.guild_avatar:
            changed = True
            embed.add_field(
                name="Server avatar",
                value="Before (thumbnail to the right) → (After) (image below)",
                inline=False,
            )
            embed.set_thumbnail(url=before.display_avatar.url)
            embed.set_image(url=after.display_avatar.url)

        if not changed:
            return

        await self.bot_spam_channel.send(embed=embed, allowed_mentions=discord.AllowedMentions.none())

    @commands.Cog.listener()
    async def on_guild_update(self, before: discord.Guild, after: discord.Guild) -> None:
        """Log community server changes to the bot spam channel."""
        if before.id != const.Guild.community:
            return

        embed = discord.Embed(
            title=f"Server updated {const.Emoji.PepoDetective}",
            colour=discord.Colour(0xF47FFF),
        ).set_author(name=after.name, icon_url=after.icon.url if after.icon is not None else None)

        changed = False

        if before.premium_tier != after.premium_tier:
            changed = True
            embed.add_field(
                name="Boost level",
                value=f"`Level {before.premium_tier}` → `Level {after.premium_tier}`",
                inline=False,
            )
            embed.add_field(
                name="Total boosts",
                value=str(after.premium_subscription_count),
                inline=False,
            )

        if not changed:
            return

        await self.bot_spam_channel.send(embed=embed, allowed_mentions=discord.AllowedMentions.none())

    ####################################################################################################################
    # WELCOME
    ####################################################################################################################

    @discord.utils.cached_property
    def welcome_channel(self) -> discord.TextChannel:
        """Welcome channel."""
        channel_id = self.WELCOME_CHANNEL_ID if not self.bot.test else self.HIDEOUT_SPAM_CHANNEL_ID
        return self.bot.get_text_channel(channel_id)

    async def welcome_image(self, member: discord.User | discord.Member) -> Image.Image:
        """Build the welcome image for a member."""
        avatar_bytes = await member.display_avatar.with_static_format("png").with_size(512).read()
        return await asyncio.to_thread(_build_welcome_image, avatar_bytes, member.display_name)

    async def get_send_welcome_kwargs(self, member: discord.Member) -> SendKwargs:
        """Build the keyword arguments for sending a welcome message about a member.

        The message consists of a greeting, an embed with onboarding steps (or a short note for bots) and, when it
        can be generated, a welcome image with the member's avatar and name. If the image fails to build, it is
        logged and left out so that the rest of the welcome message is still sent.

        Parameters
        ----------
        member
            The member to welcome.

        Returns
        -------
        SendKwargs
            Keyword arguments for `send`: `content`, `embed` and optionally `file`.
        """
        content_text = (
            f"**💜 Welcome to Irene's server, {member.mention}!** "
            f"{const.Emoji.DankHey} {const.Emoji.DankHey} {const.Emoji.DankHey}"
        )

        if not member.bot:
            description = f"""
**💜 {self.bot.owner.mention} is our princess and I'm her bot! {const.Emoji.peepoRoseDank}**
{globs.DIGITS[1]} Read the rules and useful info in {self.RULES_INFO_CHANNEL_ID.mention} {const.Emoji.PepoG}
{globs.DIGITS[2]} Choose some fancy roles in {self.ROLE_SELECTION_CHANNEL_ID.mention} and <id:customize> {const.Emoji.peepoNiceDay}
{globs.DIGITS[3]} Go to {self.GENERAL_CHANNEL_ID.mention} or any other channel and chat with us {const.Emoji.peepoComfy}
{globs.DIGITS[4]} Check out <id:guide>, <id:browse> as well {const.Emoji.DankApprove}
{globs.DIGITS[5]} Have fun! (but follow the rules {const.Emoji.bubuGun})
"""  # ruff: ignore[line-too-long]
        else:
            description = "Chat, new bot in our server."

        embed = discord.Embed(color=0x3F3B5A, description=description)
        send_kwargs: SendKwargs = {"content": content_text, "embed": embed}

        # a broken image must not prevent the welcome message itself
        try:
            image = await self.welcome_image(member)
            send_kwargs["file"] = await asyncio.to_thread(self.bot.image_to_file, image)
        except discord.HTTPException, OSError:
            log.exception("Failed to build the welcome image for %s", member)

        return send_kwargs

    @commands.Cog.listener()
    async def on_member_join(self, member: discord.Member) -> None:
        """Assign join roles to a new member and post a welcome message.

        Bots receive the bots role, while humans receive the category roles. Role assignment failures are logged and
        do not prevent the welcome message from being sent.
        """
        if member.guild.id != const.Guild.community:
            return

        try:
            if member.bot:
                await member.add_roles(self.BOTS_ROLE_ID.object, reason="Bot joined the server")
            else:
                await member.add_roles(*self.CATEGORY_ROLES, reason="Category roles for a new member")
        except discord.HTTPException:
            log.exception("Failed to add join roles to %s", member)

        send_kwargs = await self.get_send_welcome_kwargs(member)
        await self.welcome_channel.send(**send_kwargs)

    @commands.command(name="test-welcome")
    @commands.is_owner()
    @commands.guild_only()
    async def test_welcome(self, ctx: Context) -> None:
        """Preview the welcome message for yourself.

        Sends the same message that a new member would receive, in the channel where the command is used, without
        touching any roles. Useful for testing changes to the embed and the welcome image.
        """
        if not isinstance(ctx.author, discord.Member):
            return
        send_kwargs = await self.get_send_welcome_kwargs(ctx.author)
        await ctx.send(**send_kwargs)

    ####################################################################################################################
    # MEMBER LEAVE
    ####################################################################################################################

    def _recently_moderated(self, user_id: int) -> bool:
        timestamp = self._moderated.get(user_id)
        return timestamp is not None and time.monotonic() - timestamp < MODERATION_WINDOW_SECONDS

    async def _resolve_user(self, user_id: int) -> discord.User | None:
        """Get a user from the cache or the API. Returns `None` if they can't be found."""
        if user := self.bot.get_user(user_id):
            return user
        try:
            return await self.bot.fetch_user(user_id)
        except discord.HTTPException:
            return None

    @commands.Cog.listener()
    async def on_member_remove(self, member: discord.Member) -> None:
        """Log a member leaving the server to the bot spam channel.

        Kicks and bans also dispatch this event, but they are reported with a moderator and a reason by
        `on_audit_log_entry_create`. To avoid duplicates, this waits briefly and stays silent if such an entry
        arrived for the member.

        Parameters
        ----------
        member
            The member that left the guild.
        """
        if member.guild.id != const.Guild.community:
            return

        await asyncio.sleep(REMOVE_GRACE_SECONDS)
        if self._recently_moderated(member.id):
            return

        embed = discord.Embed(
            title=f"Member left {const.Emoji.SmogeInTheRain}",
            description=f"{member.mention} (`{member}`) has left the server.",
            colour=discord.Colour.dark_grey(),
        ).set_thumbnail(url=member.display_avatar.url)

        await self.welcome_channel.send(embed=embed, allowed_mentions=discord.AllowedMentions.none())

    @commands.Cog.listener()
    async def on_audit_log_entry_create(self, entry: discord.AuditLogEntry) -> None:
        """Log kicks, bans and unbans with the moderator and reason to the bot spam channel.

        Requires the `moderation` intent and the View Audit Log permission. Kicks and bans are also remembered for a
        short time so that `on_member_remove` doesn't report the same removal as a plain leave.

        Parameters
        ----------
        entry
            The audit log entry that was created.
        """
        if entry.guild.id != const.Guild.community:
            return

        if entry.action not in MODERATION_ACTIONS:
            return

        # for kick/ban/unban the target is a `Member` or `User` if known, otherwise just an `Object` with the ID
        target = entry.target
        if not isinstance(target, discord.User | discord.Member | discord.Object):
            return

        if entry.action is not discord.AuditLogAction.unban:
            now = time.monotonic()
            self._moderated = {
                user_id: timestamp
                for user_id, timestamp in self._moderated.items()
                if now - timestamp < MODERATION_WINDOW_SECONDS
            }
            self._moderated[target.id] = now

        title, verb, colour = MODERATION_ACTIONS[entry.action]
        user = target if isinstance(target, discord.User | discord.Member) else await self._resolve_user(target.id)
        name = f"`{user}`" if user else "*unknown user*"

        embed = discord.Embed(
            title=f"{title} {const.Emoji.PepoDetective}",
            description=f"<@{target.id}> ({name}) has been {verb} the server.",
            colour=colour,
        )
        embed.add_field(name="Moderator", value=entry.user.mention if entry.user else "*unknown*", inline=False)
        embed.add_field(name="Reason", value=entry.reason or "*No reason provided*", inline=False)
        if user:
            embed.set_thumbnail(url=user.display_avatar.url)

        await self.welcome_channel.send(embed=embed, allowed_mentions=discord.AllowedMentions.none())


async def setup(bot: Bot) -> None:
    """Load the extension (discord.py entry point)."""
    await bot.add_cog(Community(bot))
