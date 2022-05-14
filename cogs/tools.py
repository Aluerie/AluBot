from discord import Embed, option
from discord.ext import commands, bridge

from utils.var import *
from utils.imgtools import url_to_img, img_to_file

from PIL import Image


class ToolsCog(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.hepl_category = 'Tools'

    @bridge.bridge_command(
        name='convert',
        description='Convert image from webp to png format',
        brief=Ems.slash
    )
    @option('url', description='url of image to convert')
    async def convert(self, ctx, *, url: str):
        """Convert image from webp to png format"""
        img = await url_to_img(url)
        maxsize = (112, 112)  # TODO: remake this function to have all possible fun flags
        img.thumbnail(maxsize, Image.ANTIALIAS)
        file = img_to_file(img, filename='converted.png', fmt='PNG')
        embed = Embed(colour=Clr.prpl)
        embed.description = 'Image was converted to png format'
        await ctx.respond(file=file)


def setup(bot):
    bot.add_cog(ToolsCog(bot))
