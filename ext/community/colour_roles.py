from __future__ import annotations

from typing import TYPE_CHECKING, override

import discord
from discord.ext import commands

from utils import const

from ._base import CommunityCog

if TYPE_CHECKING:
    from bot import AluBot, AluGuildContext


class ColourRolesView(discord.ui.View):
    def __init__(self) -> None:
        super().__init__(timeout=None)
        # Adds the dropdown to our view object.
        self.add_item(ColourRolesDropdown())


class ColourRolesDropdown(discord.ui.RoleSelect[ColourRolesView]):
    def __init__(self) -> None:
        super().__init__(
            custom_id="colour_roles_dropdown",
            placeholder="Type \N{KEYBOARD} name of a colour and Select it.",
            min_values=0,
            max_values=1,
        )

    @override
    async def callback(self, interaction: discord.Interaction[AluBot]) -> None:
        if not len(self.values):
            embed = discord.Embed(
                description=f"You've selected zero roles and thus I did nothing {const.Emote.peepoComfy}",
            )
            return await interaction.response.send_message(embed=embed, ephemeral=True)

        colour_category_role = interaction.client.community.guild.get_role(const.Role.colour_category)
        activity_category_role = interaction.client.community.guild.get_role(const.Role.activity_category)

        def is_colour_role(role: discord.Role) -> bool:
            return activity_category_role < role < colour_category_role

        role = self.values[0]
        try:
            if is_colour_role(role):
                pass
            else:
                raise ValueError
        except ValueError:
            e = discord.Embed(color=const.Colour.error)
            e.description = "You are trying to choose non-colour role, which I won't give."
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
                        if is_colour_role(r):
                            await member.remove_roles(r)
                    await member.add_roles(role)

                    e = discord.Embed(color=role.color)
                    e.description = f"Added {role.mention} colour role!"
                    await interaction.response.send_message(embed=e, ephemeral=True)
            else:
                await interaction.response.send_message("Something went wrong...", ephemeral=True)
                return None


class ColourRoles(CommunityCog):
    @commands.Cog.listener()
    async def on_ready(self) -> None:
        """Register/activate persistent view for Colour Roles dropdown."""
        self.bot.add_view(ColourRolesView())

    @commands.is_owner()
    @commands.command(hidden=True)
    async def new_role_selection(self, ctx: AluGuildContext) -> None:
        await ctx.send(view=ColourRolesView())
        # await self.bot.community.role_selection.send(embed=e, view=ColourRolesView())


async def setup(bot: AluBot) -> None:
    """Load AluBot extension. Framework of discord.py."""
    await bot.add_cog(ColourRoles(bot))
