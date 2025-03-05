from __future__ import annotations

from typing import TYPE_CHECKING, override

import discord
from discord.ext import commands

from utils import const

from ._base import CommunityCog

if TYPE_CHECKING:
    from bot import AluBot, AluGuildContext, AluInteraction


class ColorRolesView(discord.ui.View):
    def __init__(self) -> None:
        super().__init__(timeout=None)
        # Adds the dropdown to our view object.
        self.add_item(ColorRolesDropdown())


class ColorRolesDropdown(discord.ui.RoleSelect[ColorRolesView]):
    def __init__(self) -> None:
        super().__init__(
            custom_id="colour_roles_dropdown",
            placeholder="Type \N{KEYBOARD} name of a colour and Select it.",
            min_values=0,
            max_values=1,
        )

    @override
    async def callback(self, interaction: AluInteraction) -> None:
        if not len(self.values):
            embed = discord.Embed(
                description=f"You've selected zero roles and thus I did nothing {const.Emote.peepoComfy}",
            )
            return await interaction.response.send_message(embed=embed, ephemeral=True)

        color_category_role = interaction.client.community.guild.get_role(const.Role.color_category)
        activity_category_role = interaction.client.community.guild.get_role(const.Role.activity_category)

        def is_color_role(role: discord.Role) -> bool:
            return activity_category_role < role < color_category_role

        role = self.values[0]
        try:
            if is_color_role(role):
                pass
            else:
                raise ValueError
        except ValueError:
            e = discord.Embed(color=const.Color.error)
            e.description = "You are trying to choose a non-colour role, which I won't give."
            await interaction.response.send_message(embed=e, ephemeral=True)
        else:
            member = interaction.client.community.guild.get_member(interaction.user.id)
            if member is not None:
                if role in member.roles:
                    await member.remove_roles(role)

                    e = discord.Embed(color=role.color)
                    e.description = f"Removed {role.mention} colour role!"
                    await interaction.response.send_message(embed=e, ephemeral=True)
                else:
                    for r in member.roles:
                        if is_color_role(r):
                            await member.remove_roles(r)
                    await member.add_roles(role)

                    e = discord.Embed(color=role.color)
                    e.description = f"Added {role.mention} colour role!"
                    await interaction.response.send_message(embed=e, ephemeral=True)
            else:
                await interaction.response.send_message("Something went wrong...", ephemeral=True)
                return None


class ColorRoles(CommunityCog):
    @commands.Cog.listener()
    async def on_ready(self) -> None:
        """Register/activate persistent view for Color Roles dropdown."""
        self.bot.add_view(ColorRolesView())

    @commands.is_owner()
    @commands.command(hidden=True)
    async def new_role_selection(self, ctx: AluGuildContext) -> None:
        await ctx.send(view=ColorRolesView())
        # await self.bot.community.role_selection.send(embed=e, view=ColorRolesView())


async def setup(bot: AluBot) -> None:
    """Load AluBot extension. Framework of discord.py."""
    await bot.add_cog(ColorRoles(bot))
