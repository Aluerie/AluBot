from __future__ import annotations

import logging
from typing import TYPE_CHECKING

from pyot.core.exceptions import NotFound

from utils import aluloop

from .._category import FPCCog
from ._models import PostMatchPlayer

# need to import the last because in import above we activate 'lol' model
from pyot.models import lol  # isort: skip

if TYPE_CHECKING:
    from utils import AluBot

log = logging.getLogger(__name__)
log.setLevel(logging.DEBUG)


class LoLFeedPostMatchEdit(FPCCog):
    def __init__(self, bot: AluBot, *args, **kwargs):
        super().__init__(bot, *args, **kwargs)
        self.postmatch_players: list[PostMatchPlayer] = []

    async def cog_load(self) -> None:
        await self.bot.ini_twitch()
        self.postmatch_edits.start()
        return await super().cog_load()

    async def cog_unload(self) -> None:
        self.postmatch_edits.stop()  # .cancel()
        return await super().cog_unload()

    async def fill_postmatch_players(self):
        """Fill `self.postmatch_players` -  data about players who have just finished their matches"""
        self.postmatch_players = []

        query = "SELECT * FROM lol_matches WHERE is_finished=TRUE"
        for row in await self.bot.pool.fetch(query):
            try:
                match = await lol.Match(id=f'{row.platform.upper()}_{row.match_id}', region=row.region).get()
            except NotFound:
                continue
            except ValueError as error:  # gosu incident ValueError: '' is not a valid platform
                raise error
                # continue

            query = 'SELECT * FROM lol_messages WHERE match_id=$1'
            for r in await self.bot.pool.fetch(query, row.match_id):
                for participant in match.info.participants:
                    if participant.champion_id == r.champ_id:
                        self.postmatch_players.append(
                            PostMatchPlayer(
                                player_data=participant,
                                channel_id=r.channel_id,
                                message_id=r.message_id,
                            )
                        )
            query = 'DELETE FROM lol_matches WHERE match_id=$1'
            await self.bot.pool.fetch(query, row.match_id)

    @aluloop(seconds=59)
    async def postmatch_edits(self):
        # log.debug(f'LE | --- Task is starting now ---')
        await self.fill_postmatch_players()
        for player in self.postmatch_players:
            await player.edit_the_embed(self.bot)
        # log.debug(f'LE | --- Task is finished ---')


async def setup(bot):
    await bot.add_cog(LoLFeedPostMatchEdit(bot))
