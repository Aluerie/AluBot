from __future__ import annotations

import itertools
from typing import TYPE_CHECKING

from discord import Embed, app_commands
from discord.ext import commands

from cogs.twitter import download_twitter_images
from utils.imgtools import url_to_img, img_to_file
from utils.var import *

from PIL import Image

if TYPE_CHECKING:
    from utils.context import Context
    from utils.bot import AluBot


class ToolsCog(commands.Cog, name='Tools'):
    """
    Some useful stuff

    Maybe one day it gonna be helpful for somebody.
    """
    def __init__(self, bot):
        self.bot: AluBot = bot
        self.help_emote = Ems.DankFix
        self.players_by_group = []

    @commands.hybrid_command(
        name='convert',
        description='Convert image from webp to png format',
    )
    @app_commands.describe(url='Url of image to convert')
    async def convert(self, ctx: Context, *, url: str):
        """Convert image from webp to png format"""
        img = await url_to_img(self.bot.ses, url)
        maxsize = (112, 112)  # TODO: remake this function to have all possible fun flags
        img.thumbnail(maxsize, Image.ANTIALIAS)
        file = img_to_file(img, filename='converted.png', fmt='PNG')
        em = Embed(colour=Clr.prpl, description='Image was converted to png format')
        await ctx.reply(embed=em, file=file)

    @commands.hybrid_command()
    @app_commands.describe(tweet_ids='Number(-s) in the end of tweet link')
    async def twitter_image(self, ctx: Context, *, tweet_ids: str):
        """
        Download image from tweets. \
        Useful for Aluerie because Twitter is banned in Russia.
        • `<tweet_ids>` are tweet ids - it's just numbers in the end of tweet links.
        """
        await download_twitter_images(self.bot.ses, ctx, tweet_ids=tweet_ids)

    def dota_request_matchmaking_stats(self):
        self.bot.steam_dota_login()
        self.players_by_group = []
        # @dota.on('ready')

        def ready_function():
            self.bot.dota.request_matchmaking_stats()

        # @dota.on('top_source_tv_games')
        def response(message):
            print(message)
            self.players_by_group = message.legacy_searching_players_by_group_source2
            self.bot.dota.emit('matchmaking_stats_response')

        # dota.on('ready', ready_function)
        self.bot.dota.once('matchmaking_stats', response)
        ready_function()
        self.bot.dota.wait_event('matchmaking_stats_response', timeout=20)
        return self.players_by_group

    @commands.hybrid_command()
    async def matchmaking_stats(self, ctx: Context):
        """Get Dota 2 matchmaking stats"""
        await ctx.typing()

        players_by_group = self.dota_request_matchmaking_stats()
        region_arr = [
            'Russia', 'Europe East', 'Europe West',
            'Dubai', 'India', 'SE Asia',
            'Japan', 'US East', 'South Africa',
            'US West',
            'Brazil', 'Peru', 'Argentina'
        ]
        ranked_dict, unranked_dict = {}, {}
        for count, i in enumerate(players_by_group):
            if count < 13:
                ranked_dict[region_arr[count]] = i
            else:
                unranked_dict[region_arr[count-13]] = i

        em = Embed(
            colour=Clr.prpl,
        ).add_field(
            name='Unranked',
            value='\n'.join([f'{k}: {v}' for k, v in ranked_dict.items()])
        ).add_field(
            name='Ranked',
            value='\n'.join([f'{k}: {v}' for k, v in unranked_dict.items()])
        )
        await ctx.reply("there:" + ' '.join([str(x) for x in players_by_group]))


async def setup(bot):
    await bot.add_cog(ToolsCog(bot))
