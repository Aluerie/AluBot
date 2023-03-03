"""
FPC is Favourite Player+Character
"""
from .dota import DOTA_COGS
from .lol import LOL_COGS
from .trusted import FPCTrusted


async def setup(bot):
    for C in DOTA_COGS + LOL_COGS + (FPCTrusted,):
        await bot.add_cog(C(bot))
