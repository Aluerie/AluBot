"""Color Roles Dropdown.

Notices
-------
* MPL-2.0 License, see LICENSE file for more details.
* Copyright (C) 2020-present @Aluerie.
"""

from __future__ import annotations

import asyncio
from typing import TYPE_CHECKING, Self, override

import discord
from discord.ext import commands

from core import Cog

if TYPE_CHECKING:
    from core import Bot, Context, Interaction


class ColorRolesView(discord.ui.View):
    """Persistent view with a dropdown for choosing a colour role."""

    COLOR_CATEGORY_ROLE_ID = 851786344354938880
    ACTIVITY_CATEGORY_ROLE_ID = 852199351808032788

    def __init__(self) -> None:
        super().__init__(timeout=None)

    @discord.ui.select(
        cls=discord.ui.RoleSelect,
        custom_id="colour_roles_dropdown",
        placeholder="Type \N{KEYBOARD} name of a colour and select it.",
        min_values=1,
        max_values=1,
    )
    async def dropdown(self, interaction: Interaction, select: discord.ui.RoleSelect[Self]) -> None:
        """Dropdown Roles Select for color roles."""
        guild = interaction.guild
        member = interaction.user
        assert guild is not None
        assert isinstance(member, discord.Member)

        color_category_role = guild.get_role(self.COLOR_CATEGORY_ROLE_ID)
        activity_category_role = guild.get_role(self.ACTIVITY_CATEGORY_ROLE_ID)
        if color_category_role is None or activity_category_role is None:
            await interaction.response.send_message(
                "Color role setup is broken, please tell the admins.", ephemeral=True
            )
            return

        def is_color_role(role: discord.Role) -> bool:
            """Color roles should be placed between those two in the server settings."""
            return activity_category_role < role < color_category_role

        role = select.values[0]
        if not is_color_role(role):
            await interaction.response.send_message(
                "You are trying to choose a non-colour role, which I won't give.", ephemeral=True
            )
            return

        await interaction.response.defer(ephemeral=True)

        try:
            if role in member.roles:
                await member.remove_roles(role)
                message = f"Removed {role.mention} colour role!"
            else:
                old_colors = [r for r in member.roles if is_color_role(r)]
                if old_colors:
                    await member.remove_roles(*old_colors)
                await member.add_roles(role)
                message = f"Added {role.mention} colour role!"
        except discord.HTTPException:
            await interaction.followup.send("I couldn't change your roles, please tell the admins.", ephemeral=True)
            return
        await interaction.followup.send(message, ephemeral=True)


class ColorRoles(Cog):
    """Color Roles for the community server."""

    @override
    async def cog_load(self) -> None:
        """Register/activate persistent view for Color Roles dropdown."""
        await super().cog_load()
        self.bot.add_view(ColorRolesView())

    @commands.is_owner()
    @commands.command(hidden=True)
    async def new_role_selection(self, ctx: Context) -> None:
        """Create a view with color roles dropdown.

        Ideally, this should only be used once to setup the color roles menu.
        """
        await ctx.send(view=ColorRolesView())
        await asyncio.sleep(2.0)
        await ctx.message.delete()


async def setup(bot: Bot) -> None:
    """Load AluBot extension. Framework of discord.py."""
    await bot.add_cog(ColorRoles(bot))
