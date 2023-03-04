from __future__ import annotations

import logging
from typing import TYPE_CHECKING

from twitchio.ext import commands

from config import TWITCH_TOKEN

if TYPE_CHECKING:
    from utils.bot import AluBot


log = logging.getLogger(__name__)


class TwitchBot(commands.Bot):

    def __init__(self, discord_bot: AluBot):
        # prefix can be a callable, which returns a list of strings or a string...
        # initial_channels can also be a callable which returns a list of strings...
        super().__init__(token=TWITCH_TOKEN, prefix=['!', '?'], initial_channels=['Aluerie'])
        self.discord_bot: AluBot = discord_bot

    async def event_ready(self):
        log.info(f'TwitchBot Ready as {self.nick} | user_id = {self.user_id}')

    @commands.command()
    async def hello(self, ctx: commands.Context):
        await ctx.send(f'Hello @{ctx.author.name}!')


if __name__ == '__main__':
    # bot = TwitchBot()
    # bot.run()
    pass
