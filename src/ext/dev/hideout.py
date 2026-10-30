# Copyright (C) 2020-present, Irene Adler ❤ (@Aluerie).
# Licensed under MPL-2.0, see the LICENSE file for details.
"""Hideout."""

from __future__ import annotations

import asyncio
from typing import TYPE_CHECKING, Any, Final, override

import discord
from discord import ui
from discord.ext import commands
from discord.utils import escape_markdown

from config import env
from core import Context, DevCog
from shared import clock, fmt
from shared.concepts.discord_logs import DiscordWebhookLogs
from utils import const

if TYPE_CHECKING:
    from collections.abc import Sequence

    from core import Bot


class Hideout(DiscordWebhookLogs, DevCog):
    """Hideout Discord Guild Related Features."""

    JAILED_BOTS_ROLE_ID = 1090428532162822234

    GLOBAL_LOGS_CHANNEL_ID = 997149550324240465

    EXTRA_EXACT_AVATAR_MAPPING: Final[dict[str, str]] = {
        "discord.gateway": "https://em-content.zobj.net/source/microsoft/476/broken-heart_1f494.png",
        "core.bot": "https://em-content.zobj.net/source/microsoft/476/swan_1f9a2.png",
        "ext.dev.reload": "https://em-content.zobj.net/source/microsoft/476/counterclockwise-arrows-button_1f504.png",
    }

    def __init__(self, bot: Bot) -> None:
        super().__init__(env.WEBHOOK_LOGGER, bot.session)
        super(DevCog, self).__init__(bot)

    @override
    async def cog_load(self) -> None:
        await self.load()
        await super().cog_load()

    @override
    async def cog_unload(self) -> None:
        await self.teardown()
        await super().cog_unload()

    ####################################################################################################################
    # JAILED BOTS
    ####################################################################################################################

    @commands.Cog.listener(name="on_member_join")
    async def moderate_hideout_joiners(self, member: discord.Member) -> None:
        """Jail or kick outsiders.

        * Kicks non-bot accounts from the server if they somehow managed to enter;
        * Gives newly entered bot-accounts @Jailed Bots role.
        """
        if member.guild.id != const.Guild.hideout:
            return

        if member.bot:
            await member.add_roles(
                discord.Object(self.JAILED_BOTS_ROLE_ID), reason="New bot account: jailed by default"
            )
        else:
            await self.bot.notify_developers(
                f"{member} ({member.id}) joined and I'm kicking them. Please disable invites."
            )
            await member.kick(reason="Non-bot account joined hideout (it's private)")

    ####################################################################################################################
    # GUILD JOIN/REMOVE LOGGING
    ####################################################################################################################

    @staticmethod
    def _info_section(
        title: str,
        fields: dict[str, object],
        image_url: str | None,
    ) -> ui.Section[Any] | ui.TextDisplay[Any]:
        """Build a titled section, with a thumbnail when an image is available."""
        content = f"## {title}\n{fmt.bullet_list([f'{key}: {value}' for key, value in fields.items()])}"
        if image_url is None:
            return ui.TextDisplay(content)
        return ui.Section(content, accessory=ui.Thumbnail(image_url))

    async def _get_owner(self, guild: discord.Guild) -> discord.User | discord.Member | None:
        """Return the guild owner from cache, falling back to an API fetch."""
        if guild.owner is not None:
            return guild.owner
        if guild.owner_id is None:
            return None
        try:
            return await self.bot.fetch_user(guild.owner_id)
        except discord.HTTPException:  # includes NotFound
            return None

    async def _find_inviter(
        self,
        guild: discord.Guild,
        delays: Sequence[float] = (0, 1, 2),
    ) -> discord.User | discord.Member | None:
        """Look up who added the bot via the audit log, if permitted."""
        if not guild.me.guild_permissions.view_audit_log:
            return None

        for delay in delays:
            await asyncio.sleep(delay)  # audit log entry may lag behind the join event
            try:
                async for entry in guild.audit_logs(action=discord.AuditLogAction.bot_add, limit=10):
                    if entry.target is not None and entry.target.id == guild.me.id:
                        return entry.user
            except discord.Forbidden:
                return None
        return None

    def _get_guild_section(self, guild: discord.Guild) -> ui.Section[Any] | ui.TextDisplay[Any]:
        members = guild.members
        bots_count = sum(m.bot for m in members)
        return self._info_section(
            "Guild",
            {
                "Name": escape_markdown(guild.name),
                "ID": f"`{guild.id}`",
                "Humans / Bots": f"{len(members) - bots_count} / {bots_count}",
                "Created": clock.discord(guild.created_at, "R"),
                "Channels": f"{len(guild.text_channels)} text, {len(guild.voice_channels)} voice",
                "Roles": len(guild.roles),
                "Boosts": f"Tier {guild.premium_tier} ({guild.premium_subscription_count} boosts)",
                "Bot joined": clock.discord(guild.me.joined_at, "R") if guild.me.joined_at is not None else "Unknown",
                "Description": escape_markdown(guild.description) if guild.description is not None else "Unset",
            },
            guild.icon.url if guild.icon is not None else None,
        )

    def _get_user_section(
        self, title: str, user: discord.Member | discord.User
    ) -> ui.Section[Any] | ui.TextDisplay[Any]:
        return self._info_section(
            title=title,
            fields={
                "Display Name": escape_markdown(user.display_name),
                "Username": f"[@{escape_markdown(user.name)}](https://discord.com/users/{user.id})",
                "ID": f"`{user.id}`",
            },
            image_url=user.display_avatar.url,
        )

    async def _send_guild_info(
        self,
        guild: discord.Guild,
        destination: discord.abc.Messageable,
        *,
        accent_color: discord.Colour | int,
        heading: str | None = None,
        inviter_delays: Sequence[float] | None = (0, 1, 2),
    ) -> None:
        """Send an info card about guild to destination."""
        container = ui.Container(accent_color=accent_color)
        if heading is not None:
            container.add_item(ui.TextDisplay(f"# {heading}"))
        container.add_item(self._get_guild_section(guild))
        if (owner := await self._get_owner(guild)) is not None:
            container.add_item(self._get_user_section("Guild Owner", owner))
        if inviter_delays is not None and (inviter := await self._find_inviter(guild, inviter_delays)) is not None:
            container.add_item(self._get_user_section("Inviter", inviter))
        container.add_item(ui.Separator())
        container.add_item(ui.TextDisplay(f"-# Now in {len(self.bot.guilds)} guilds"))

        view = ui.LayoutView()
        view.add_item(container)
        await destination.send(view=view, allowed_mentions=discord.AllowedMentions.none())

    @commands.Cog.listener()
    async def on_guild_join(self, guild: discord.Guild) -> None:
        """Send a notification with guild stats on `guild_join` events."""
        await self._send_guild_info(
            guild,
            destination=self.bot.get_text_channel(self.GLOBAL_LOGS_CHANNEL_ID),
            heading="Joined Guild",
            accent_color=const.Palette.green_500,
        )

    @commands.command(name="test-guild")
    @commands.is_owner()
    @commands.guild_only()
    async def test_guild(self, ctx: Context) -> None:
        """Show info about the current guild."""
        assert ctx.guild is not None
        await self._send_guild_info(
            ctx.guild,
            destination=ctx,
            inviter_delays=(0,),
            heading="Guild Information",
            accent_color=ctx.guild.me.color,
        )

    @commands.Cog.listener()
    async def on_guild_remove(self, guild: discord.Guild) -> None:
        """Send a notification with guild stats on `guild_remove` events."""
        await self._send_guild_info(
            guild,
            destination=self.bot.get_text_channel(self.GLOBAL_LOGS_CHANNEL_ID),
            heading="Left Guild",
            accent_color=const.Palette.red_500,
            inviter_delays=None,
        )


async def setup(bot: Bot) -> None:
    """Load the extension (discord.py entry point)."""
    await bot.add_cog(Hideout(bot))
