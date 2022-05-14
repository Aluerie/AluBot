from discord import Embed, Member, TextChannel, option
from discord.ext import commands, tasks, bridge

from utils.var import *
from utils.imgtools import img_to_file
from utils.format import humanize_time

from datetime import datetime, timezone, timedelta, time
import platform
from typing import Union
from wordcloud import WordCloud


class StatsCommands(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.help_category = 'Stats'

    async def wordcloud_work(self, ctx, cm, limit):
        cm = cm or []  # idk i don't like mutable default argument warning
        members = [x for x in cm if isinstance(x, Member)] or [ctx.author]
        channels = [x for x in cm if isinstance(x, TextChannel)] or [ctx.channel]
        await ctx.defer()
        text = ''
        for ch in channels:
            text += ''.join([f'{msg.content}\n' async for msg in ch.history(limit=limit) if msg.author in members])
        wordcloud = WordCloud(width=640, height=360, max_font_size=40).generate(text)
        await ctx.respond(file=img_to_file(wordcloud.to_image(), filename='wordcloud.png'))

    @commands.slash_command(
        name='wordcloud',
        description='Get `@member wordcloud over last total `limit` messages in requested `#channel`'
    )
    @option('member', description='Choose member')
    @option('channel', description='Choose channel')
    async def wordcloud_slh(self, ctx, member: Member, channel: TextChannel, limit: int = 2000):
        cm = [member, channel]
        await self.wordcloud_work(ctx, cm, limit)

    @commands.command(
        name='wordcloud',
        brief=Ems.slash,
        usage='[channel(s)=curr] [member(s)=you] [limit=2000]'
    )
    async def wordcloud_ext(self, ctx, cm: commands.Greedy[Union[Member, TextChannel]] = None, limit: int = 2000):
        """
        Get `@member`'s wordcloud over last total `limit` messages in requested `#channel`.
        Can accept multiple members/channels \
        Note that it's quite slow function or even infinitely slow with bigger limits ;
        """
        await self.wordcloud_work(ctx, cm, limit)

    @bridge.bridge_command(
        name='summary',
        brief=Ems.slash,
        description='Summary stats for the bot'
    )
    async def summary(self, ctx):
        """Summary stats for the bot ;"""
        embed = Embed(colour=Clr.prpl, title='Summary bot stats')
        embed.set_thumbnail(url=self.bot.user.avatar.url)
        embed.add_field(name="Server Count", value=str(len(self.bot.guilds)))
        embed.add_field(name="User Count", value=str(len(self.bot.users)))
        embed.add_field(name="Ping", value=f"{self.bot.latency * 1000:.2f}ms")
        embed.add_field(name='Uptime',
                        value=humanize_time(datetime.now(timezone.utc) - self.bot.launch_time, full=False))
        await ctx.respond(embed=embed)


class Stats(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.mytime.start()
        self.mymembers.start()
        self.mybots.start()

    @tasks.loop(time=[time(hour=x) for x in range(0, 24)])
    async def mytime(self):
        symbol = '#' if platform.system() == 'Windows' else '-'
        new_name = f'⏰ {datetime.now(timezone(timedelta(hours=3))).strftime(f"%{symbol}I %p")}, MSK, Irene time'
        await self.bot.get_channel(Cid.my_time).edit(name=new_name)

    @mytime.before_loop
    async def before(self):
        await self.bot.wait_until_ready()

    @tasks.loop(hours=5)
    async def mymembers(self):
        irene_server = self.bot.get_guild(Sid.irene)
        bots_role = irene_server.get_role(Rid.bots)
        new_name = f'🏡 Members: {irene_server.member_count-len(bots_role.members)}'
        await irene_server.get_channel(795743012789551104).edit(name=new_name)

    @mymembers.before_loop
    async def before(self):
        await self.bot.wait_until_ready()

    @tasks.loop(hours=5)
    async def mybots(self):
        irene_server = self.bot.get_guild(Sid.irene)
        bots_role = irene_server.get_role(Rid.bots)
        new_name = f'🤖 Bots: {len(bots_role.members)}'
        await irene_server.get_channel(795743065787990066).edit(name=new_name)

    @mybots.before_loop
    async def before(self):
        await self.bot.wait_until_ready()


def setup(bot):
    bot.add_cog(Stats(bot))
    bot.add_cog(StatsCommands(bot))
