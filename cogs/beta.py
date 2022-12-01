from __future__ import annotations

import logging
from typing import TYPE_CHECKING

from discord.ext import commands, tasks

from .utils.var import *

if TYPE_CHECKING:
    from .utils.bot import AluBot, Context

log = logging.getLogger(__name__)


class BetaTest(commands.Cog):
    def __init__(self, bot):
        self.bot: AluBot = bot
        self.reload_info.start()

    def cog_unload(self):
        return

    @commands.hybrid_command()
    async def allu(self, ctx: Context):
        await ctx.send(f'Did we do it')

    @tasks.loop(count=1)
    async def reload_info(self):
        log.info('hehe')
        return
        # print('Query is completed')

    @reload_info.before_loop
    async def before(self):
        await self.bot.wait_until_ready()


async def setup(bot):
    #if bot.test_flag:
    await bot.add_cog(BetaTest(bot))


# SQL RECIPES BCS I ALWAYS FORGET
""" 
--- recipe for converting column to tz aware 
ALTER TABLE botinfo ALTER COLUMN git_checked_dt
TYPE TIMESTAMPTZ USING git_checked_dt AT TIME ZONE 'UTC' ;

-- recipe to set default 
ALTER TABLE users ALTER COLUMN lastseen
SET DEFAULT (now() at time zone 'utc');

-- recipe to INSERT and return True/None if it was success
INSERT INTO users (id, name) 
VALUES ($1, $2) 
ON CONFLICT DO NOTHING
RETURNING True;
-- ### value = await self.bot.pool.fetchval(query, 333356, 'hihihi')

--- recipe to add a new column
ALTER TABLE dfmatches
ADD COLUMN live BOOLEAN DEFAULT TRUE;

"""