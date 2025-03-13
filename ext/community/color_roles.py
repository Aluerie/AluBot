from __future__ import annotations

import asyncio
from typing import TYPE_CHECKING, Self

import discord
from discord.ext import commands

from bot import AluCog
from utils import const

if TYPE_CHECKING:
    from bot import AluBot, AluGuildContext, AluInteraction


__all__ = ("ColorRoles",)


class ColorRolesView(discord.ui.View):
    def __init__(self) -> None:
        super().__init__(timeout=None)

    @discord.ui.select(
        cls=discord.ui.RoleSelect,
        custom_id="colour_roles_dropdown",
        placeholder="Type \N{KEYBOARD} name of a colour and select it.",
        min_values=0,
        max_values=1,
    )
    async def dropdown(self, interaction: AluInteraction, select: discord.ui.RoleSelect[Self]) -> None:
        """Dropdown Roles Select for color roles."""
        if not len(select.values):
            error_embed = discord.Embed(
                description=f"You've selected zero roles and thus I did nothing {const.Emote.peepoComfy}",
            )
            await interaction.response.send_message(embed=error_embed, ephemeral=True)
            return

        color_category_role = interaction.client.community.guild.get_role(const.Role.color_category)
        activity_category_role = interaction.client.community.guild.get_role(const.Role.activity_category)

        def is_color_role(role: discord.Role) -> bool:
            """Color roles should be out between those two in the server settings."""
            return activity_category_role < role < color_category_role

        role = select.values[0]
        if not is_color_role(role):
            error_embed = discord.Embed(
                color=const.Color.error,
                description="You are trying to choose a non-colour role, which I won't give.",
            )
            await interaction.response.send_message(embed=error_embed, ephemeral=True)
            return

        member = interaction.client.community.guild.get_member(interaction.user.id)
        if member is None:
            # not sure if this is possible since the dropdown will be directly in the server
            # i guess some cache memes
            await interaction.response.send_message("Something went wrong...", ephemeral=True)
            return

        if role in member.roles:
            # user clicked a color role in order to remove it from themselves
            await member.remove_roles(role)
            embed = discord.Embed(color=role.color, description=f"Removed {role.mention} colour role!")
            await interaction.response.send_message(embed=embed, ephemeral=True)
        else:
            # user clicked a new color role in order to get it
            for r in member.roles:
                if is_color_role(r):
                    # remove other color roles if present
                    await member.remove_roles(r)
            await member.add_roles(role)

            embed = discord.Embed(color=role.color, description=f"Added {role.mention} colour role!")
            await interaction.response.send_message(embed=embed, ephemeral=True)


class ColorRoles(AluCog):
    """Color Roles for the community server."""

    @commands.Cog.listener(name="on_ready")
    async def activate_color_roles(self) -> None:
        """Register/activate persistent view for Color Roles dropdown."""
        self.bot.add_view(ColorRolesView())

    @commands.is_owner()
    @commands.command(hidden=True)
    async def new_role_selection(self, ctx: AluGuildContext) -> None:
        """Create a view with color roles dropdown.

        Ideally, this should only be used once to setup the color roles menu.
        """
        await ctx.send(view=ColorRolesView())
        await asyncio.sleep(2.0)
        await ctx.message.delete()


async def setup(bot: AluBot) -> None:
    """Load AluBot extension. Framework of discord.py."""
    await bot.add_cog(ColorRoles(bot))
