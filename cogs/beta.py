from __future__ import annotations

import logging
from typing import TYPE_CHECKING, List

from discord import Embed, app_commands, Interaction
from discord.ext import commands, tasks

from .dota.const import ODOTA_API_URL
from .utils.var import *

from .utils.context import Context

if TYPE_CHECKING:
    from .utils.bot import AluBot

log = logging.getLogger(__name__)


import string
from discord.app_commands import AppCommandError, Transform, Transformer, Choice, command
from discord import app_commands, Interaction


class AlphabetTransformerError(AppCommandError):
    pass


class AlphabetTransformer(Transformer):
    # this could also be set in `__init__` to make this more generic
    options = list(string.ascii_lowercase)

    async def transform(self, interaction: Interaction, value: str, /) -> str:
        if value in self.options:
            # maybe convert this value to something else instead of using the raw value
            return value
        raise AlphabetTransformerError(f'"{value}" is not a valid option.\nValid options: {", ".join(self.options)}')

    async def autocomplete(self, interaction: Interaction, value: str, /) -> list[Choice[str]]:
        # build up to 25 choices
        # optionally use `difflib.get_close_matches` or similar to determine which choices to show
        return [Choice(name=letter, value=letter) for letter in self.options[:25]]


class BetaTest(commands.Cog):
    def __init__(self, bot: AluBot):
        self.bot: AluBot = bot
        self.reload_info.start()

    def cog_unload(self):
        return

    @app_commands.command()
    async def test(self, interaction: Interaction, letter: Transform[str, AlphabetTransformer]):
        await interaction.response.send_message(letter)

    @test.error
    async def test_error(self, interaction: Interaction, error: AppCommandError):
        if isinstance(error, AlphabetTransformerError):
            await interaction.response.send_message(str(error))
        # if you don't have your own tree error handler, you must handle other errors
        else:
            logging.error(f'Error in command {interaction.command}', exc_info=error)

    @app_commands.command()
    async def test_add_names(self, ntr: Interaction, name1: str, name2: str, name3: str):
        names = list(set([name for name in list(locals().values())[2:] if name is not None]))
        await ntr.response.send_message(', '.join(names))

    @commands.hybrid_command()
    async def allu(self, ctx: Context):
        await ctx.send_test()

    @tasks.loop(count=1)
    async def reload_info(self):
        """match_id = 6893851829

        url = f"{ODOTA_API_URL}/request/{match_id}"
        async with self.bot.ses.post(url) as resp:
            # print(resp)
            print(resp.ok)
            print(data := await resp.json())

        url = f"{ODOTA_API_URL}/request/{data['job']['jobId']}"
        async with self.bot.ses.get(url) as resp:
            # print(resp)
            print(resp.ok)
            print(await resp.json())

        jobid = 176580986

        url = f"{ODOTA_API_URL}/request/{jobid}"
        async with self.bot.ses.get(url) as resp:
            # print(resp)
            print(resp.ok)
            print(await resp.json())"""

        return
        # print('Query is completed')

    @reload_info.before_loop
    async def before(self):
        await self.bot.wait_until_ready()


async def setup(bot):
    # if bot.test_flag:
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