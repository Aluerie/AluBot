from __future__ import annotations

from typing import TYPE_CHECKING, override

import discord
from discord import app_commands
from discord.ext import commands
from PIL import Image

from core import AluCog
from utils import const

if TYPE_CHECKING:
    from core import AluBot, AluInteraction


class ButtonRolesView(discord.ui.View):
    def __init__(self, roles: list[discord.Role]) -> None:
        super().__init__(timeout=None)
        for role in roles:
            self.add_item(RoleButton(role))


class RoleButton(discord.ui.Button):
    def __init__(self, role: discord.Role) -> None:
        super().__init__(
            label=role.name,
            style=discord.ButtonStyle.blurple,
        )
        self.role: discord.Role = role
        self.custom_id = str(role.id)

    @override
    async def callback(self, interaction: AluInteraction):
        assert self.view is not None
        assert isinstance(interaction.user, discord.Member)
        if self.role in interaction.user.roles:
            await interaction.user.remove_roles(self.role)
            await interaction.response.send_message(f"Removed {self.role.mention}", ephemeral=True)
        else:
            await interaction.user.add_roles(self.role)
            await interaction.response.send_message(f"Added {self.role.mention}", ephemeral=True)


class ImageTools(AluCog):
    """Some useful stuff.

    Maybe one day it's going to be helpful for somebody.
    """

    @app_commands.command()
    @app_commands.describe(url="Url of image to convert")
    async def convert(self, interaction: AluInteraction, url: str) -> None:
        """Convert image from webp to png format.

        Parameters
        ----------
        url:
            Image url.
        """
        await interaction.response.defer()
        img = await self.bot.transposer.url_to_image(url)
        maxsize = (112, 112)  # TODO: remake this function to have all possible fun flags
        img.thumbnail(maxsize, Image.Resampling.LANCZOS)
        file = self.bot.transposer.image_to_file(img, filename="converted.png", extension="PNG")
        e = discord.Embed(color=const.Color.prpl, description="Image was converted to `.png` format")
        await interaction.followup.send(embed=e, file=file)

    @commands.Cog.listener(name="on_ready")
    async def activate_color_roles(self) -> None:
        """Register/activate persistent view for Color Roles dropdown."""
        query = """SELECT guild_id, role_id FROM button_roles"""
        rows = await self.bot.pool.fetch(query)
        roles = [self.bot.get_guild(row["guild_id"]).get_role(row["role_id"]) for row in rows]
        self.bot.add_view(ButtonRolesView(roles))

    @app_commands.command()
    @app_commands.default_permissions(manage_roles=True)
    async def create_button_roles(
        self,
        interaction: AluInteraction,
        role_1: discord.Role | None = None,
        role_2: discord.Role | None = None,
        role_3: discord.Role | None = None,
        role_4: discord.Role | None = None,
        role_5: discord.Role | None = None,
        role_6: discord.Role | None = None,
        role_7: discord.Role | None = None,
        role_8: discord.Role | None = None,
        role_9: discord.Role | None = None,
        role_10: discord.Role | None = None,
        role_11: discord.Role | None = None,
        role_12: discord.Role | None = None,
        role_13: discord.Role | None = None,
        role_14: discord.Role | None = None,
    ) -> None:
        await interaction.response.send_message("Sending", ephemeral=True)
        roles = [
            role_1,
            role_2,
            role_3,
            role_4,
            role_5,
            role_6,
            role_7,
            role_8,
            role_9,
            role_10,
            role_11,
            role_12,
            role_13,
            role_14,
        ]
        roles = [r for r in roles if r is not None]
        query = """
            INSERT INTO button_roles
            (guild_id, role_id)
            VALUES ($1, $2)
            ON CONFLICT DO NOTHING
        """
        await self.bot.pool.executemany(query, [(interaction.guild.id, role.id) for role in roles])
        await interaction.channel.send(view=ButtonRolesView(roles))


async def setup(bot: AluBot) -> None:
    """Load AluBot extension. Framework of discord.py."""
    await bot.add_cog(ImageTools(bot))
