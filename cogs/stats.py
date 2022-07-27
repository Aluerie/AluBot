from __future__ import annotations
from typing import TYPE_CHECKING

from discord import Embed, Member, TextChannel, app_commands
from discord.ext import commands, tasks

from utils.var import *
from utils.imgtools import img_to_file
from utils.format import humanize_time

from datetime import datetime, timezone, timedelta, time
import platform
from typing import Union
from wordcloud import WordCloud

if TYPE_CHECKING:
    pass


class StatsCommands(commands.Cog, name='Stats'):
    """
    Some stats/infographics/diagrams/info

    More to come.
    """
    def __init__(self, bot):
        self.bot = bot
        self.help_emote = Ems.Smartge

    @commands.hybrid_command(
        name='wordcloud',
        description='Get `@member wordcloud over last total `limit` messages in requested `#channel`',
        usage='[channel(s)=curr] [member(s)=you] [limit=2000]'
    )
    @app_commands.describe(channel_or_and_member='List channel(-s) or/and member(-s)')
    async def wordcloud(
            self,
            ctx,
            channel_or_and_member: commands.Greedy[Union[Member, TextChannel]] = None,
            limit: int = 2000
    ):
        """
        Get `@member`'s wordcloud over last total `limit` messages in requested `#channel`.
        Can accept multiple members/channels \
        Note that it's quite slow function or even infinitely slow with bigger limits ;
        """
        cm = channel_or_and_member or []  # idk i don't like mutable default argument warning
        members = [x for x in cm if isinstance(x, Member)] or [ctx.author]
        channels = [x for x in cm if isinstance(x, TextChannel)] or [ctx.channel]
        await ctx.defer()
        text = ''
        for ch in channels:
            text += ''.join([f'{msg.content}\n' async for msg in ch.history(limit=limit) if msg.author in members])
        wordcloud = WordCloud(width=640, height=360, max_font_size=40).generate(text)
        em = Embed(
            colour=Clr.prpl,
            description=
            f"Members: {', '.join([m.mention for m in members])}\n"
            f"Channels: {', '.join([c.mention for c in channels])}\n"
            f"Limit: {limit}"
        )
        await ctx.reply(embed=em, file=img_to_file(wordcloud.to_image(), filename='wordcloud.png'))

    @commands.hybrid_command(
        name='summary',
        description='Summary stats for the bot'
    )
    async def summary(self, ctx):
        """Summary stats for the bot ;"""
        em = Embed(
            colour=Clr.prpl,
            title='Summary bot stats'
        ).set_thumbnail(
            url=self.bot.user.avatar.url
        ).add_field(
            name="Server Count",
            value=str(len(self.bot.guilds))
        ).add_field(
            name="User Count",
            value=str(len(self.bot.users))
        ).add_field(
            name="Ping",
            value=f"{self.bot.latency * 1000:.2f}ms"
        ).add_field(
            name='Uptime',
            value=humanize_time(datetime.now(timezone.utc) - self.bot.launch_time, full=False)
        )
        await ctx.reply(embed=em)


class StatsChannels(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.mytime.start()
        self.mymembers.start()
        self.mybots.start()

    @tasks.loop(time=[time(hour=x) for x in range(0, 24)])
    async def mytime(self):
        symbol = '#' if platform.system() == 'Windows' else '-'
        new_name = f'⏰ {datetime.now(timezone(timedelta(hours=3))).strftime(f"%{symbol}I %p")}, MSK, Aluerie time'
        await self.bot.get_channel(Cid.my_time).edit(name=new_name)

    @mytime.before_loop
    async def before(self):
        await self.bot.wait_until_ready()

    @tasks.loop(hours=5)
    async def mymembers(self):
        guild = self.bot.get_guild(Sid.alu)
        bots_role = guild.get_role(Rid.bots)
        new_name = f'🏡 Members: {guild.member_count-len(bots_role.members)}'
        await guild.get_channel(795743012789551104).edit(name=new_name)

    @mymembers.before_loop
    async def before(self):
        await self.bot.wait_until_ready()

    @tasks.loop(hours=5)
    async def mybots(self):
        guild = self.bot.get_guild(Sid.alu)
        bots_role = guild.get_role(Rid.bots)
        new_name = f'🤖 Bots: {len(bots_role.members)}'
        await guild.get_channel(795743065787990066).edit(name=new_name)

    @mybots.before_loop
    async def before(self):
        await self.bot.wait_until_ready()


async def setup(bot):
    await bot.add_cog(StatsChannels(bot))
    await bot.add_cog(StatsCommands(bot))
