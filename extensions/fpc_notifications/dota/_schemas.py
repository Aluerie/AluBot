from __future__ import annotations

from typing import TYPE_CHECKING, NamedTuple, Literal

if TYPE_CHECKING:
    # CMsgGCToClientFindTopSourceTVGamesResponse
    # all these types are fake and just a band-aid fix to ValvePython being bad at typing
    class Player(NamedTuple):
        account_id: int
        hero_id: int
        team: Literal[0, 1]
        team_slot: Literal[1, 2, 3, 4, 5]

    class CSourceTVGameSmall(NamedTuple):
        activate_time: int
        deactivate_time: int
        server_steam_id: int
        lobby_id: int
        league_id: int
        lobby_type: int
        game_time: int
        delay: int
        spectators: int
        game_mode: int
        average_mmr: int
        match_id: int
        series_id: int
        sort_score: int
        last_update_time: float
        radiant_lead: int
        radiant_score: int
        dire_score: int
        players: list[Player]
        building_state: int
        custom_game_difficulty: int

    class CMsgGCToClientFindTopSourceTVGamesResponse(NamedTuple):
        # fake type
        search_key: str
        league_id: int
        hero_id: int
        start_game: int
        num_games: int
        game_list_index: int
        game_list: list[CSourceTVGameSmall]
        specific_games: bool
