from __future__ import annotations

from typing import TYPE_CHECKING

from PIL import Image
from discord import Embed, app_commands
from discord.ext import commands

from cogs.twitter import download_twitter_images
from .utils.var import Clr, Ems

if TYPE_CHECKING:
    from .utils.bot import AluBot
    from .utils.context import Context

server_regions_order = [
    'USWest', 'USEast', 'Europe', 'Korea', 'Singapore', 'Dubai', 'Australia', 'Stockholm', 'Austria', 'Brazil',
    'SouthAfrica', 'PerfectWorldTelecom', 'PerfectWorldUnicom', 'Chile', 'Peru', 'India',
    'PerfectWorldTelecomGuangdong', 'PerfectWorldTelecomZhejian', 'Japan', 'PerfectWorldTelecomWuhan',
    'PerfectWorldUnicomTianjin',  # 'Taiwan
]

server_regions = [
    'USWest', 'USEast', 'Europe', 'Korea', 'Singapore', 'Dubai', 'PerfectWorldTelecom', 'PerfectWorldTelecomGuangdong',
    'PerfectWorldTelecomZhejian', 'PerfectWorldTelecomWuha', 'PerfectWorldUnicom', 'PerfectWorldUnicomTianjin',
    'Stockholm', 'Brazil', 'Austria', 'Australia', 'SouthAfrica', 'Chile', 'Peru', 'India', 'Japan',  # 'Taiwan',
]

server_regions_video = [
    'US West', 'US East', 'SE Asia', 'EU West', 'EU East', 'Russia', 'Australia', 'South Africa', 'Dubai',
    'Brazil', 'Chile', 'Peru', 'Argentina', 'India', 'Japan', 'China TC Shanghai', 'China UC',
    'China TC Guangdong', 'China TC Zhejiang', 'China TC Wuhan', '???'
]


class ToolsCog(commands.Cog, name='Tools'):
    """
    Some useful stuff

    Maybe one day it's going to be helpful for somebody.
    """

    def __init__(self, bot: AluBot):
        self.bot: AluBot = bot
        self.help_emote = Ems.DankFix

        self.players_by_group = []

    def cog_load(self) -> None:
        self.bot.ini_steam_dota()
        self.bot.ini_twitter()

    @commands.hybrid_command(
        name='convert',
        description='Convert image from webp to png format',
    )
    @app_commands.describe(url='Url of image to convert')
    async def convert(self, ctx: Context, *, url: str):
        """Convert image from webp to png format"""
        img = await self.bot.url_to_img(url)
        maxsize = (112, 112)  # TODO: remake this function to have all possible fun flags
        img.thumbnail(maxsize, Image.ANTIALIAS)
        file = self.bot.img_to_file(img, filename='converted.png', fmt='PNG')
        em = Embed(colour=Clr.prpl, description='Image was converted to `.png` format')
        await ctx.reply(embed=em, file=file)

    @commands.hybrid_command()
    @app_commands.describe(tweet_ids='Number(-s) in the end of tweet link')
    async def twitter_image(self, ctx: Context, *, tweet_ids: str):
        """
        Download image from tweets. \
        Useful for Aluerie because Twitter is banned in Russia.
        • `<tweet_ids>` are tweet ids - it's just numbers in the end of tweet links.
        """
        await download_twitter_images(self.bot.session, ctx, tweet_ids=tweet_ids)

    def dota_request_matchmaking_stats(self):
        self.bot.steam_dota_login()
        self.players_by_group = []

        # @dota.on('ready')

        def ready_function():
            self.bot.dota.request_matchmaking_stats()

        # @dota.on('top_source_tv_games')
        def response(message):
            # print(message)
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
        players_by_group = [x for x in players_by_group if x]

        answer = '\n'.join([
            f'{i}. {y}: {x}'
            for i, (x, y) in enumerate(zip(players_by_group, server_regions_order), start=1)
        ])
        em = Embed(colour=Clr.prpl, title='Dota 2 Matchmaking stats', description=answer)
        em.set_footer(text='These regions are completely wrong. idk how to relate numbers from valve to actual regions')
        # print(len(players_by_group), len(server_regions_order))
        await ctx.reply(embed=em)


async def setup(bot):
    # while twitter is banned in russia # TODO: Remove this
    import platform
    if platform.system() == 'Windows':
        return
    await bot.add_cog(ToolsCog(bot))
