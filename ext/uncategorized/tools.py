from __future__ import annotations

from typing import TYPE_CHECKING

import discord
from discord import app_commands
from PIL import Image

from bot import AluCog
from utils import const

if TYPE_CHECKING:
    from bot import AluBot, AluInteraction


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


async def setup(bot: AluBot) -> None:
    """Load AluBot extension. Framework of discord.py."""
    await bot.add_cog(ImageTools(bot))
