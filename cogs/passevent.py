from __future__ import annotations

from typing import TYPE_CHECKING

from discord import Message
from discord.ext import commands, tasks
from datetime import datetime, timezone, timedelta
from utils.var import Uid, umntn

if TYPE_CHECKING:
    from utils.bot import AluBot

start_errors = 948936198733328425
game_feed = 966316773869772860


class PassEvent(commands.Cog):
    def __init__(self, bot):
        self.bot: AluBot = bot
        self.lastupdated = datetime.now(timezone.utc)
        self.crashed = True
        self.botcheck.start()

    def cog_unload(self) -> None:
        self.botcheck.cancel()

    @commands.Cog.listener()
    async def on_message(self, msg: Message):
        if msg.channel.id == game_feed:
            self.lastupdated = datetime.now(timezone.utc)
            self.crashed = False
        if msg.channel.id == start_errors:
            self.crashed = True

    @tasks.loop(hours=2)
    async def botcheck(self):
        if self.crashed:
            return
        if datetime.now(timezone.utc) - self.lastupdated > timedelta(minutes=70):
            await self.bot.get_channel(start_errors).send(
                content=f'{umntn(Uid.alu)} I think the bot crashed but did not even send the message'
            )

    @botcheck.before_loop
    async def before(self):
        await self.bot.wait_until_ready()


async def setup(bot):
    await bot.add_cog(PassEvent(bot))
