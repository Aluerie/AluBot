from __future__ import annotations

from typing import TYPE_CHECKING

import discord
from discord.ext import tasks

from utils import AluCog
from utils.const import Colour, Guild
from utils.dota.const import DOTA_LOGO

if TYPE_CHECKING:
    pass


class Dota2Com(AluCog):
    def cog_load(self) -> None:
        self.patch_checker.start()

    def cog_unload(self) -> None:
        self.patch_checker.cancel()

    @tasks.loop(minutes=10)
    async def patch_checker(self):
        url = "https://www.dota2.com/datafeed/patchnoteslist"
        async with self.bot.session.get(url) as resp:
            data = await resp.json()

        # db.set_value(db.b, Guild.community, dota_patch='sadge')
        last_patch = data["patches"][-1]
        patch_number, patch_name = last_patch["patch_number"], last_patch["patch_name"]

        query = """ UPDATE botinfo 
                        SET dota_patch=$1
                        WHERE id=$2 
                        AND dota_patch IS DISTINCT FROM $1
                        RETURNING True
                    """
        val = await self.bot.pool.fetchval(query, patch_number, Guild.community)
        if not val:
            return

        e = discord.Embed(
            title="Patch Notes", url=f'https://www.dota2.com/patches/{patch_number}', colour=Colour.prpl()
        )
        e.description = f"Hey chat, I think new patch {patch_name} is out!"
        e.set_footer(text="I'm checking Valve's datafeed every 10 minutes")
        e.set_author(name=f"Patch {patch_number} is out", icon_url=DOTA_LOGO)
        msg = await self.bot.community.dota_news.send(embed=e)
        await msg.publish()

    @patch_checker.before_loop
    async def before(self):
        await self.bot.wait_until_ready()


async def setup(bot):
    await bot.add_cog(Dota2Com(bot))
