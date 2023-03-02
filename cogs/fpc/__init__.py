"""
FPC is Favourite Player+Character
"""
from .dota import setup as dota_setup
from .lol import setup as lol_setup


async def setup(bot):
    await dota_setup(bot)
    await lol_setup(bot)
