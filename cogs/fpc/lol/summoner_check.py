from __future__ import annotations
from typing import TYPE_CHECKING

import datetime

from discord.ext import commands, tasks

# need to import the last because in import above we activate 'lol' model
from pyot.models import lol  # isort: skip

if TYPE_CHECKING:
    from utils import AluBot


class LoLSummonerNameCheck(commands.Cog):
    def __init__(self, bot: AluBot):
        self.bot: AluBot = bot
        self.check_acc_renames.start()

    @tasks.loop(time=datetime.time(hour=12, minute=11, tzinfo=datetime.timezone.utc))
    async def check_acc_renames(self):
        if datetime.datetime.now(datetime.timezone.utc).day != 17:
            return

        query = 'SELECT id, platform, accname FROM lolaccs'
        rows = await self.bot.pool.fetch(query)

        for row in rows:
            person = await lol.summoner.Summoner(id=row.id, platform=row.platform).get()
            if person.name != row.accname:
                query = 'UPDATE lolaccs SET accname=$1 WHERE id=$2'
                await self.bot.pool.execute(query, person.name, row.id)

    @check_acc_renames.before_loop
    async def before(self):
        await self.bot.wait_until_ready()
