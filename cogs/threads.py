from __future__ import annotations

from datetime import time
from typing import TYPE_CHECKING

from discord import ForumChannel
from discord.ext import commands, tasks

from .utils.var import Sid, Ems

if TYPE_CHECKING:
    from discord import Thread
    from .utils.bot import AluBot

watched_threads_ids = []


class ThreadsManaging(commands.Cog):
    def __init__(self, bot: AluBot):
        self.bot: AluBot = bot

    async def cog_load(self) -> None:
        self.unarchive_threads.start()

    async def cog_unload(self) -> None:
        self.unarchive_threads.cancel()

    @commands.Cog.listener()
    async def on_thread_create(self, thread: Thread):
        if thread.owner.bot or isinstance(thread.parent, ForumChannel):
            return
        await thread.join()
        await thread.send(content=f'De fok, using threads {Ems.peepoWTF}')

    @tasks.loop(time=time(hour=12))
    async def unarchive_threads(self):
        guild = self.bot.get_guild(Sid.alu)
        for _id in watched_threads_ids:
            thread = guild.get_channel(_id)
            await thread.archive()  # type: ignore
            await thread.unarchive()  # type: ignore

    @unarchive_threads.before_loop
    async def before(self):
        await self.bot.wait_until_ready()


async def setup(bot: AluBot):
    await bot.add_cog(ThreadsManaging(bot))
