from __future__ import annotations

import time
import asyncio
import logging
from typing import TYPE_CHECKING, List

import discord
from discord import Embed, app_commands, Interaction
from discord.ext import commands, tasks

from .dota.const import ODOTA_API_URL
from .utils.var import *

from .utils.context import Context

if TYPE_CHECKING:
    from .utils.bot import AluBot

log = logging.getLogger(__name__)
log.setLevel(logging.DEBUG)

from discord.app_commands import AppCommandError, Transform, Transformer, Choice, command
from discord import app_commands, Interaction


class AlphabetTransformerError(AppCommandError):
    pass


class BetaTest(commands.Cog):
    def __init__(self, bot: AluBot):
        self.bot: AluBot = bot
        self.reload_info.start()

    def cog_unload(self):
        return

    @tasks.loop(count=1)
    async def reload_info(self):
        return

    @app_commands.command()
    async def welp(self, ntr: Interaction):
        await ntr.response.defer()
        await ntr.followup.send('allo')
        # ctx = await Context.from_interaction(ntr)
        # await ctx.typing()
        # await ctx.reply()

    @commands.hybrid_command()
    async def allu(self, ctx: Context):
        # print(ctx.prefix, ctx.clean_prefix)
        await ctx.send_test()

    @reload_info.before_loop
    async def before(self):
        await self.bot.wait_until_ready()


async def setup(bot):
    if bot.test:
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

--- recipe to get all column names
SELECT column_name
FROM information_schema.columns
WHERE table_name=$1;


---------
WITH foo AS (SELECT array(SELECT dotafeed_stream_ids
FROM guilds
WHERE id = 759916212842659850))
SELECT display_name
FROM dota_players p
WHERE NOT p.id=ANY(foo)
ORDER BY similarity(display_name, 'gorgc') DESC
LIMIT 12;
"""