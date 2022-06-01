from __future__ import annotations
from typing import TYPE_CHECKING, Annotated, Union

from discord import Embed, app_commands, Role, Member, Colour
from discord.ext import commands

from utils.var import *
from utils import time

from dateparser.search import search_dates
import asyncio

if TYPE_CHECKING:
    from utils.context import Context, Message


class BetaTest(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @commands.command()
    async def timezeta(self, ctx, *, when: str):
        em = Embed(colour=Clr.prpl)
        try:
            my_time = time.Time(when)
            dt = my_time.dt
            em.add_field(
                inline=False,
                name='time.HumanTime',
                value=f'{time.format_tdR(dt)}\n'
                      f'{dt.tzname()} is GMT {dt.utcoffset().seconds / 3600:+.1f} | dls: {dt.dst()}'
            )
        except:
            em.add_field(
                inline=False,
                name='time.HumanTime',
                value='Failed'
            )

        pdates = search_dates(when)
        if pdates is None:
            em.add_field(
                inline=False,
                name='search dates',
                value='Failed'
            )
        else:
            for pdate in pdates:
                dt = pdate[1]
                if dt.utcoffset() is not None:
                    tzone = f'{dt.utcoffset().seconds / 3600:+.1f}'
                else:
                    tzone = '+0.0'
                em.add_field(
                    inline=False,
                    name='search_dates',
                    value=f'{time.format_tdR(dt)}\n'
                          f'{dt.tzname()} is GMT {tzone} | dls: {dt.dst()}'
                )

        await ctx.send(embed=em)


async def setup(bot):
    # if bot.yen:
    await bot.add_cog(BetaTest(bot))
