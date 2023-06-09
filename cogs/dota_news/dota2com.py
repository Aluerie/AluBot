from __future__ import annotations

from typing import TYPE_CHECKING, Any, Optional

import discord
from discord.ext import commands, tasks

from utils import AluCog, const
from utils.checks import is_owner
from utils.dota.const import DOTA_LOGO

if TYPE_CHECKING:
    from utils import AluBot, AluGuildContext


class Dota2Com(AluCog):
    def __init__(self, bot: AluBot, *args: Any, **kwargs: Any) -> None:
        super().__init__(bot, *args, **kwargs)
        self.is_today_patch_day: bool = False

    def cog_load(self) -> None:
        self.patch_checker.start()

    def cog_unload(self) -> None:
        self.patch_checker.cancel()

    @is_owner()
    @commands.command(name='patchday', aliases=['patch_day'])
    async def patch_day(self, ctx: AluGuildContext, yes_no: Optional[bool]):
        """Start checking for Dota 2 patches more/less frequently from dota2.com page."""
        is_today_patch_day = not self.is_today_patch_day if yes_no is None else yes_no
        new_frequency = {'seconds': 10} if is_today_patch_day else {'minutes': 10}
        self.patch_checker.change_interval(**new_frequency)
        e = discord.Embed(colour=const.Colour.prpl())
        t = ','.join([f'{k}={v}' for k, v in new_frequency.items()])  # seconds=30
        e.description = f"Changed frequency to `{t}`"
        await ctx.reply(embed=e)

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
        val = await self.bot.pool.fetchval(query, patch_number, const.Guild.community)
        if not val:
            return

        e = discord.Embed(title=f"New patch out {const.Emote.PogChampPepe}", colour=const.Colour.prpl())
        e.url = f'https://www.dota2.com/patches/{patch_number}'
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
