import logging

from dota2.client import Dota2Client
from steam.client import SteamClient

from config import STEAM_TEST_LGN, STEAM_TEST_PSW

logging.basicConfig(
    format='[%(asctime)s] %(levelname)s %(name)s: %(message)s',
    level=logging.DEBUG
)
log = logging.getLogger(__name__)

steam = SteamClient()
dota = Dota2Client(steam)


@dota.on('top_source_tv_games')
def top_source_tv_games_response(result):
    log.info(
        f"top_source_tv_games resp ng: {result.num_games} sg: {result.specific_games} "
        f"{result.start_game, result.game_list_index, len(result.game_list), result.game_list[0].players[0].account_id}"
    )
    # self.bot.dota.emit('top_games_response')


@dota.on('matches_minimal')
def matches_minimal_response(matches):
    log.info(f"{matches}")


@dota.on('ready')
def test_func():
    # dota.request_top_source_tv_games(start_game=90)
    dota.request_matches_minimal(match_ids=[6884832211])


steam.login(username=STEAM_TEST_LGN, password=STEAM_TEST_PSW)
dota.launch()
steam.run_forever()
