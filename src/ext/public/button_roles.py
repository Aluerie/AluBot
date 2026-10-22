"""Button Roles.

Notices
-------
* MPL-2.0 License, see LICENSE file for more details.
* Copyright (C) 2020-present @Aluerie.
"""

from __future__ import annotations

from typing import TYPE_CHECKING, override

import discord
from discord import app_commands, ui

from core import AluCog

if TYPE_CHECKING:
    from core import AluBot, AluInteraction


class EmbedRolesModal(ui.Modal, title="Button Roles with an Embed"):
    """Embed Role Modal."""

    # def __init__(self) -> None:
    #     super().__init__()

    #     for
    #     self.add_item()

    embed_title = ui.Label(text="Title", component=ui.TextInput())
    description = ui.Label(text="Answer", component=ui.TextInput(style=discord.TextStyle.paragraph))
    # color =

    @override
    async def on_submit(self, interaction: AluInteraction) -> None:
        embed = discord.Embed(
            # color=self.color,
            title=self.embed_title,
            description=self.description,
        )
        await interaction.response.send_message(embed=embed)


class ButtonRoles(AluCog):
    """ButtonRoles."""

    @override
    async def cog_load(self) -> None:
        await super().cog_load()

    @override
    async def cog_unload(self) -> None:
        await super().cog_unload()

    button_roles_group = app_commands.Group(
        name="button-roles",
        description="🎨 Create and manage button roles.",
        allowed_contexts=app_commands.AppCommandContext(guild=True, dm_channel=False, private_channel=False),
        allowed_installs=app_commands.AppInstallationType(guild=True, user=False),
    )


async def setup(bot: AluBot) -> None:
    """Load AluBot extension. Framework of discord.py."""
    await bot.add_cog(ButtonRoles(bot))
