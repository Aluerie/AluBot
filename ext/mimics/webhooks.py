from __future__ import annotations

import asyncio
from typing import TYPE_CHECKING, TypedDict

import discord
from discord.ext import commands

from bot import AluBot, aluloop
from utils import errors

from ..config_guilds._base import ConfigGuildCog

if TYPE_CHECKING:
    from bot import AluBot

    class AllWebhooksQueryRow(TypedDict):
        id: int
        channel_id: int
        guild_id: int
        url: str


__all__ = ("WebhookMaintenance",)


class WebhookMaintenance(ConfigGuildCog):
    """Maintaining `webhooks` database.

    This cog keeps the table up-to-date, i.e.
    * removes invalid webhooks;
    * checks valid webhooks from time to time;

    Webhooks are used across many of the bot's features so it's important to keep the table updated.
    """

    def __init__(self, bot: AluBot) -> None:
        super().__init__(bot)
        self.check_valid_webhooks.start()

    @commands.Cog.listener(name="on_guild_channel_delete")
    async def deleted_channels(self, channel: discord.abc.GuildChannel) -> None:
        """Delete webhooks associated with a channel from the database when the channel gets deleted."""
        query = "DELETE FROM webhooks WHERE channel_id = $1"
        await self.bot.pool.execute(query, channel.id)

    @commands.Cog.listener(name="on_guild_remove")
    async def removed_guilds(self, guild: discord.Guild) -> None:
        """Delete webhooks associated with a guild from the database when the bot leaves it."""
        query = "DELETE FROM webhooks WHERE guild_id = $1"
        await self.bot.pool.execute(query, guild.id)

    @aluloop(hours=30 * 24)  # 30 days
    async def check_valid_webhooks(self) -> None:
        """Monthly task to double check webhooks in the database."""
        if self.check_valid_webhooks.current_loop == 0:
            return

        query = "SELECT * FROM webhooks"
        rows: list[AllWebhooksQueryRow] = await self.bot.pool.fetch(query)

        for row in rows:
            webhook = self.bot.webhook_from_url(row["url"])

            try:
                webhook = await webhook.fetch()
            except discord.NotFound:
                # webhook is no longer valid
                query = "DELETE FROM webhooks WHERE id = $1"
                await self.bot.pool.execute(query, row["id"])
            else:
                # check if channel is still correct.
                if not webhook.channel:
                    msg = "Webhook channel is None even though we fetched it..."
                    raise errors.PlaceholderError(msg)

                if webhook.channel.id != row["channel_id"]:
                    query = "UPDATE webhooks SET channel_id = $1 WHERE id=$2"
                    await self.bot.pool.execute(query, webhook.channel.id, row["id"])

            await asyncio.sleep(30)


async def setup(bot: AluBot) -> None:
    """Load AluBot extension. Framework of discord.py."""
    await bot.add_cog(WebhookMaintenance(bot))
