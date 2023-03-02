"""
These cogs are about my private one-person server
and provide features for only me
"""

from .channel_watcher import setup as cw_setup


async def setup(bot):
    await cw_setup(bot)
