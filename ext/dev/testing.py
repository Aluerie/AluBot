from __future__ import annotations

from typing import TYPE_CHECKING

import discord
from discord import app_commands

from utils import const, mimics

from ._base import BaseDevCog

if TYPE_CHECKING:
    from bot import AluBot, AluInteraction


class Testing(BaseDevCog):
    """Commands to test various discord "technicalities".

    Probably better to explain with an example:
    * I hope discord one-day will allow channel webhooks to use emotes from bots' dashboards. So when I get the irk
        to check if this wish came true - I will just use a command that tries to send an emote in a webhook.
    """

    test_group = app_commands.Group(
        name="test-dev",
        description="\N{ELECTRIC TORCH} Commands to test various technicalities.",
        guild_ids=[const.Guild.hideout],
        default_permissions=discord.Permissions(manage_guild=True),
    )

    @test_group.command(name="webhook-emote")
    async def webhook_emote(self, interaction: AluInteraction) -> None:
        """🔦Test if webhooks can send emotes from bots' dashboards."""
        content = (
            "AluBot dashboard emote - <:hu:1409577106601676862>\nYenBot dashboard emote - <:hu:1409577790700912690>"
        )
        await interaction.response.send_message(f"## 1. The Interaction.\n{content}")
        await self.bot.spam_webhook.send(f"## 2. Aluerie's Owned Webhook.\n{content}")

        if channel_webhooks := await interaction.channel.webhooks():  # type: ignore[reportAttributeAccessIssue]
            await channel_webhooks[0].send(f"## 3. The Bot's Owned Webhook.\n{content}")

        mirror = mimics.Mirror.from_interaction(interaction)
        await mirror.send(member=interaction.user, content=f"## 4. Mirror-Mimic.\n{content}")


async def setup(bot: AluBot) -> None:
    """Load AluBot extension. Framework of discord.py."""
    await bot.add_cog(Testing(bot))
