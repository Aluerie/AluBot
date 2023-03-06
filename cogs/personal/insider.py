from __future__ import annotations

from typing import TYPE_CHECKING
import re

import feedparser
import discord
from discord.ext import tasks

from utils.var import Sid, Cid

from ._base import PersonalBase


if TYPE_CHECKING:
    pass


class Insider(PersonalBase):
    def cog_load(self) -> None:
        self.insider_checker.start()

    def cog_unload(self) -> None:
        self.insider_checker.cancel()

    @tasks.loop(minutes=10)
    async def insider_checker(self):

        url = "https://blogs.windows.com/windows-insider/feed/"
        rss = feedparser.parse(url)

        for entry in rss.entries:
            if re.findall(r'25[0-9]{3}', entry.title): # dev entry check
                p = entry
                break
        else:
            return

        query = """ UPDATE botinfo 
                        SET insider_vesion=$1
                        WHERE id=$2 
                        AND insider_vesion IS DISTINCT FROM $1
                        RETURNING True
                    """
        val = await self.bot.pool.fetchval(query, p.title, Sid.alu)
        if not val:
            return

        e = discord.Embed(title=p.title, url=p.link, colour=0x0179d4)
        e.set_image(
            url='https://blogs.windows.com/wp-content/themes/microsoft-stories-theme/img/theme/windows-placeholder.jpg'
        )
        msg = await self.bot.get_channel(Cid.repost).send(embed=e)
        # await msg.publish()

    @insider_checker.before_loop
    async def before(self):
        await self.bot.wait_until_ready()


async def setup(bot):
    await bot.add_cog(Insider(bot))
