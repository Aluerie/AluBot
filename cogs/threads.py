from __future__ import annotations
from typing import TYPE_CHECKING

from discord.ext import commands, tasks

from utils.var import Sid, Ems

from datetime import time

if TYPE_CHECKING:
    from discord import Thread

watched_threads_ids = []


class ThreadsManaging(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.unarchive_threads.start()

    @commands.Cog.listener()
    async def on_thread_create(self, thread: Thread):
        if thread.owner.bot or thread.guild.id == Sid.emote:
            return
        await thread.join()
        await thread.send(content=f'De fok, using threads {Ems.peepoWTF}')

    @tasks.loop(time=time(hour=12))
    async def unarchive_threads(self):
        guild = self.bot.get_guild(Sid.alu)
        for _id in watched_threads_ids:
            thread = guild.get_channel(_id)
            await thread.archive()
            await thread.unarchive()

    @unarchive_threads.before_loop
    async def before(self):
        await self.bot.wait_until_ready()


async def setup(bot):
    await bot.add_cog(ThreadsManaging(bot))
