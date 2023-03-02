from .copy import CopypasteLeague
from lol_com import LoLCom


async def setup(bot):
    await bot.add_cog(CopypasteLeague(bot))
    await bot.add_cog(LoLCom(bot))
