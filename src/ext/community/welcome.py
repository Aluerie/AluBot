"""Community Features.

Notices
-------
* MPL-2.0 License, see LICENSE file for more details.
* Copyright (C) 2020-present @Aluerie.
"""

import asyncio
import functools
import logging
import time
from io import BytesIO
from pathlib import Path
from typing import TYPE_CHECKING, Final

import discord
from discord.ext import commands
from PIL import Image, ImageDraw, ImageFont

from core import Cog, Context
from shared import globs
from utils import const

if TYPE_CHECKING:
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

# action -> (title, past tense verb, color)
MODERATION_ACTIONS: dict[discord.AuditLogAction, tuple[str, str, discord.Color]] = {
    discord.AuditLogAction.kick: ("Member kicked", "kicked from", discord.Color.orange()),
    discord.AuditLogAction.ban: ("Member banned", "banned from", discord.Color.red()),
    discord.AuditLogAction.unban: ("Member unbanned", "unbanned from", discord.Color.green()),
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

    RULES_INFO_CHANNEL_ID: Final = const.ChannelId(724996010169991198)
    ROLE_SELECTION_CHANNEL_ID: Final = const.ChannelId(1099742867947262093)
    WELCOME_CHANNEL_ID: Final = const.ChannelId(725000501690630257)
    GENERAL_CHANNEL_ID: Final = const.ChannelId(702561315478044807)

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

    def __init__(self, bot: Bot) -> None:
        super().__init__(bot)
        # user id -> `time.monotonic()` of their latest kick/ban audit log entry
        self._moderated: dict[int, float] = {}

    ####################################################################################################################
    # WELCOME
    ####################################################################################################################

    @discord.utils.cached_property
    def welcome_channel(self) -> discord.TextChannel:
        """Welcome channel."""
        return self.bot.get_text_channel_or_test(self.WELCOME_CHANNEL_ID)

    async def welcome_image(self, member: discord.User | discord.Member) -> Image.Image:
        """Build the welcome image for a member."""
        avatar_bytes = await member.display_avatar.with_static_format("png").with_size(512).read()
        return await asyncio.to_thread(_build_welcome_image, avatar_bytes, member.display_name)

    async def get_send_welcome_kwargs(self, member: discord.Member) -> SendKwargs:
        """Build the keyword arguments for sending a welcome message about a member.

        The message consists of a greeting, an embed with onboarding steps (or a short note for bots) and, when it
        can be generated, a welcome image with the member's avatar and name. If the image fails to build, it is
        logged and left out so that the rest of the welcome message is still sent.
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
                return
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
        """Log a member leaving the server to the welcome channel.

        Kicks and bans also dispatch this event, but they are reported with a moderator and a reason by
        `on_audit_log_entry_create`. To avoid duplicates, this waits briefly and stays silent if such an entry
        arrived for the member.
        """
        if member.guild.id != const.Guild.community:
            return
        if member.bot:
            return

        await asyncio.sleep(REMOVE_GRACE_SECONDS)
        if self._recently_moderated(member.id):
            return

        embed = discord.Embed(
            title=f"Member left {const.Emoji.SmogeInTheRain}",
            description=f"{member.mention} (`{member}`) has left the server.",
            color=discord.Color.dark_grey(),
        ).set_thumbnail(url=member.display_avatar.url)

        await self.welcome_channel.send(embed=embed, allowed_mentions=discord.AllowedMentions.none())

    @commands.Cog.listener()
    async def on_audit_log_entry_create(self, entry: discord.AuditLogEntry) -> None:
        """Log kicks, bans and unbans with the moderator and reason to the bot spam channel.

        Requires the `moderation` intent and the View Audit Log permission. Kicks and bans are also remembered for a
        short time so that `on_member_remove` doesn't report the same removal as a plain leave.
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

        title, verb, color = MODERATION_ACTIONS[entry.action]
        user = target if isinstance(target, discord.User | discord.Member) else await self._resolve_user(target.id)
        name = f"`{user}`" if user else "*unknown user*"

        embed = discord.Embed(
            title=f"{title} {const.Emoji.PepoDetective}",
            description=f"<@{target.id}> ({name}) has been {verb} the server.",
            color=color,
        )
        embed.add_field(name="Moderator", value=entry.user.mention if entry.user else "*unknown*", inline=False)
        embed.add_field(name="Reason", value=entry.reason or "*No reason provided*", inline=False)
        if user:
            embed.set_thumbnail(url=user.display_avatar.url)

        await self.welcome_channel.send(embed=embed, allowed_mentions=discord.AllowedMentions.none())


async def setup(bot: Bot) -> None:
    """Load the extension (discord.py entry point)."""
    await bot.add_cog(Community(bot))
