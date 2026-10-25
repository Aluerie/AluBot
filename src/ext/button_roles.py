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

from core import Cog

if TYPE_CHECKING:
    from core import Bot, Interaction


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
    async def on_submit(self, interaction: Interaction) -> None:
        embed = discord.Embed(
            # color=self.color,
            title=self.embed_title,
            description=self.description,
        )
        await interaction.response.send_message(embed=embed)


class ButtonRoles(Cog):
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


async def setup(bot: Bot) -> None:
    """Load AluBot extension. Framework of discord.py."""
    await bot.add_cog(ButtonRoles(bot))


class ButtonRolesView(discord.ui.View):  # ruff: ignore[undocumented-public-class]
    def __init__(self, roles: list[discord.Role]) -> None:
        super().__init__(timeout=None)
        for role in roles:
            self.add_item(RoleButton(role))


class RoleButton(discord.ui.Button):  # ty: ignore[missing-type-argument]  # ruff: ignore[undocumented-public-class]
    def __init__(self, role: discord.Role) -> None:
        super().__init__(
            label=role.name,
            style=discord.ButtonStyle.blurple,
        )
        self.role: discord.Role = role
        self.custom_id = str(role.id)

    @override
    async def callback(self, interaction: Interaction) -> None:
        assert self.view is not None
        assert isinstance(interaction.user, discord.Member)
        if self.role in interaction.user.roles:
            await interaction.user.remove_roles(self.role)
            await interaction.response.send_message(f"Removed {self.role.mention}", ephemeral=True)
        else:
            await interaction.user.add_roles(self.role)
            await interaction.response.send_message(f"Added {self.role.mention}", ephemeral=True)


class ImageTools(Cog):
    """Some useful stuff.

    Maybe one day it's going to be helpful for somebody.
    """

    # @commands.Cog.listener(name="on_ready")
    # async def activate_color_roles(self) -> None:
    #     """Register/activate persistent view for Color Roles dropdown."""
    #     query = """SELECT guild_id, role_id FROM button_roles"""
    #     rows = await self.bot.pool.fetch(query)
    #     roles = [self.bot.get_guild(row["guild_id"]).get_role(row["role_id"]) for row in rows]
    #     self.bot.add_view(ButtonRolesView(roles))

    # @app_commands.command()
    # @app_commands.guild_only()
    # @app_commands.guild_install()
    # @app_commands.default_permissions(manage_roles=True)
    # async def create_button_roles(
    #     self,
    #     interaction: Interaction,
    #     role_1: discord.Role | None = None,
    #     role_2: discord.Role | None = None,
    #     role_3: discord.Role | None = None,
    #     role_4: discord.Role | None = None,
    #     role_5: discord.Role | None = None,
    #     role_6: discord.Role | None = None,
    #     role_7: discord.Role | None = None,
    #     role_8: discord.Role | None = None,
    #     role_9: discord.Role | None = None,
    #     role_10: discord.Role | None = None,
    #     role_11: discord.Role | None = None,
    #     role_12: discord.Role | None = None,
    #     role_13: discord.Role | None = None,
    #     role_14: discord.Role | None = None,
    # ) -> None:
    #     await interaction.response.send_message("Sending", ephemeral=True)
    #     roles = [
    #         role_1,
    #         role_2,
    #         role_3,
    #         role_4,
    #         role_5,
    #         role_6,
    #         role_7,
    #         role_8,
    #         role_9,
    #         role_10,
    #         role_11,
    #         role_12,
    #         role_13,
    #         role_14,
    #     ]
    #     roles = [r for r in roles if r is not None]
    #     query = """
    #         INSERT INTO button_roles
    #         (guild_id, role_id)
    #         VALUES ($1, $2)
    #         ON CONFLICT DO NOTHING
    #     """
    #     await self.bot.pool.executemany(query, [(interaction.guild.id, role.id) for role in roles])
    #     await interaction.channel.send(view=ButtonRolesView(roles))
