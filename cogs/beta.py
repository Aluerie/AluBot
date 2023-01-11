from __future__ import annotations
from typing import TYPE_CHECKING

import logging

import discord
from discord import app_commands
from discord.ext import commands, tasks, menus

from .utils.context import Context
from .utils import pagination
from .utils.var import Cid

if TYPE_CHECKING:
    from .utils.bot import AluBot

log = logging.getLogger(__name__)
log.setLevel(logging.DEBUG)


class MySource(menus.ListPageSource):
    async def format_page(self, menu, entries):
        return f"This is number {entries}."


class PrefixView(discord.ui.View):
    def __init__(self, cog, pages) -> None:
        super().__init__()
        self.cog = cog
        self.pages = pages

    @discord.ui.button(label='\N{HOUSE BUILDING}', style=discord.ButtonStyle.blurple)
    async def home_page(self, ntr: discord.Interaction, _btn: discord.ui.Button):
        await ntr.response.send_message('Pepega', ephemeral=True)


class BetaTest(commands.Cog):
    """Beta commands"""
    def __init__(self, bot: AluBot):
        self.bot: AluBot = bot
        self.test_task.start()

    async def setup_info(self):
        e = discord.Embed()
        e.description = 'beta beta beta beta'
        return e

    async def setup_state(self, ctx: Context):
        e = discord.Embed()
        e.description = 'Your current prefix is $'
        return e

    async def setup_view(self, pages):
        return PrefixView(self, pages)

    @tasks.loop(count=1)
    async def test_task(self):
        return
        link = 'https://i.imgur.com/8Y92Gdk.png'
        # 'https://i.imgur.com/nsUP5fI.png' # 'https://i.imgur.com/MtT6oKS.png' #'https://i.imgur.com/uT8CJHt.png'
        word = 'dota'
        e = discord.Embed(title=word)
        e.set_author(name=word, icon_url=link)
        e.set_footer(text=word, icon_url=link)
        e.set_thumbnail(url=link)
        e.set_image(url=link)
        await self.bot.get_channel(Cid.spam_me).send(embed=e)
        return

    @app_commands.command()
    async def welp(self, ntr: discord.Interaction):
        await ntr.response.send_message('allo')

    @commands.hybrid_command()
    async def allu(self, ctx: Context):
        # e1 = discord.Embed(description='1')
        # e2 = discord.Embed(description='2')
        # await ctx.reply('PepeLaugh')

        # menu = MyMenu()
        # await menu.start(ctx)

        data = [1, 2, 3, 4, 5, 6, 7, 8, 9, 10]
        formatter = MySource(data, per_page=1)
        menu = pagination.Paginator(formatter, ctx=ctx)
        await menu.start()

    @test_task.before_loop
    async def before(self):
        await self.bot.wait_until_ready()


async def setup(bot):
    if bot.test:
        await bot.add_cog(BetaTest(bot))
