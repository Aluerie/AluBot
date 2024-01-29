"""
Slightly overcooked typing for OpenDota pulsefire-like client REST requests.

Note that it can be outdated, wrong, incomplete. 
"""

from typing import Literal, NamedTuple, NotRequired, Optional, TypedDict

__all__ = (
    "OpenDotaAPISchema",
    "StratzGraphQLQueriesSchema",
    "GameCoordinatorAPISchema",
)


class OpenDotaAPISchema:
    ### The following schemas are for GET /matches/{match_id} endpoint

    PermanentBuff = TypedDict(
        "PermanentBuff",
        {
            "permanent_buff": int,
            "stack_count": int,
            "grant_time": int,
        },
    )

    BenchMarkData = TypedDict(
        "BenchMarkData",
        {
            "raw": int,
            "pct": float,
        },
    )

    BenchMarks = TypedDict(
        "BenchMarks",
        {
            "gold_per_min": BenchMarkData,
            "xp_per_min": BenchMarkData,
            "kills_per_min": BenchMarkData,
            "last_hits_per_min": BenchMarkData,
            "hero_damage_per_min": BenchMarkData,
            "hero_healing_per_min": BenchMarkData,
            "tower_damage": BenchMarkData,
        },
    )

    Player = TypedDict(
        "Player",
        {
            "abandons": int,
            "ability_upgrades_arr": list[int],
            "account_id": NotRequired[int],  # Anonymous - do not have accounts
            "aghanims_scepter": Literal[0, 1],
            "aghanims_shard": Literal[0, 1],
            "assists": int,
            "backpack_0": int,
            "backpack_1": int,
            "backpack_2": int,
            "benchmarks": BenchMarks,
            "cluster": int,
            "deaths": int,
            "denies": int,
            "duration": int,
            "game_mode": int,
            "gold": int,
            "gold_per_min": int,
            "gold_spent": int,
            "hero_damage": int,
            "hero_healing": int,
            "hero_id": int,
            "isRadiant": bool,
            "is_contributor": bool,
            "is_subscriber": bool,
            "item_0": int,
            "item_1": int,
            "item_2": int,
            "item_3": int,
            "item_4": int,
            "item_5": int,
            "item_neutral": int,
            "kda": float,
            "kills": int,
            "kills_per_min": float,
            "last_hits": int,
            "last_login": str,
            "leaver_status": Literal[0, 1],
            "level": int,
            "lobby_type": int,
            "lose": Literal[0, 1],
            "moonshard": Literal[0, 1],  # cSpell: ignore moonshard
            "name": Optional[str],
            "net_worth": int,
            "party_id": int,
            "party_size": int,
            "patch": int,
            "permanent_buffs": list[PermanentBuff],
            "personaname": str,  # cSpell: ignore personaname
            "player_slot": str,
            "radiant_win": bool,
            "rank_tier": int,
            "region": int,
            "start_time": int,
            "team_number": Literal[0, 1],
            "team_slot": int,
            "total_gold": int,
            "total_xp": int,
            "tower_damage": int,
            "win": Literal[0, 1],
            "xp_per_min": int,
        },
    )

    PickBan = TypedDict(
        "PickBan",
        {
            "is_pick": bool,
            "hero_id": int,
            "team": int,
            "order": int,
        },
    )

    ODData = TypedDict(
        "ODData",
        {
            "has_api": bool,
            "has_gcdata": bool,  # cSpell:ignore gcdata
            "has_parsed": bool,
            "archive": bool,
        },
    )

    Match = TypedDict(
        "Match",
        {
            "barracks_status_dire": int,
            "barracks_status_radiant": int,
            "cluster": int,
            "dire_score": int,
            "duration": int,
            "engine": int,
            "first_blood_time": int,
            "flags": int,
            "game_mode": int,
            "human_players": int,
            "leagueid": int,  # cSpell:ignore leagueid
            "lobby_type": int,
            "match_id": int,
            "match_seq_num": int,
            "metadata": Optional[str],
            "od_data": ODData,
            "patch": int,
            "picks_bans": list[PickBan],
            "players": list[Player],
            "pre_game_duration": int,
            "radiant_score": int,
            "radiant_win": bool,
            "region": int,
            "replay_salt": int,
            "replay_url": str,  # "http://replay271.valve.net/570/7543512738_81106471.dem.bz2",
            "series_id": int,
            "series_type": int,
            "start_time": int,
            "tower_status_dire": int,
            "tower_status_radiant": int,
        },
    )

    ### The following schemas are for POST /request/{match_id} endpoint
    ParseJob = TypedDict(
        "ParseJob",
        {
            "jobId": int,
        },
    )

    RequestParse = TypedDict(
        "RequestParse",
        {
            "job": ParseJob,
        },
    )


class StratzGraphQLQueriesSchema:
    class GetFPCMatchToEdit:
        # GET FPC MATCH TO EDIT
        BuffEvent = TypedDict(
            "BuffEvent",
            {
                "itemId": Optional[int],
            },
        )

        Stats = TypedDict(
            "Stats",
            {
                "matchPlayerBuffEvent": list[BuffEvent],
            },
        )

        PurchaseEvent = TypedDict(
            "PurchaseEvent",
            {
                "time": int,
                "itemId": int,
            },
        )

        AbilityLearnEvent = TypedDict(
            "AbilityLearnEvent",
            {
                "abilityId": int,
            },
        )

        PlaybackData = TypedDict(
            "PlaybackData",
            {
                "abilityLearnEvents": list[AbilityLearnEvent],
                "purchaseEvents": list[PurchaseEvent],
            },
        )

        Player = TypedDict(
            "Player",
            {
                "isVictory": bool,
                "heroId": int,
                "kills": int,
                "deaths": int,
                "assists": int,
                "item0Id": int,
                "item1Id": int,
                "item2Id": int,
                "item3Id": int,
                "item4Id": int,
                "item5Id": int,
                "neutral0Id": int,
                "playbackData": PlaybackData,
                "stats": Stats,
            },
        )

        Match = TypedDict(
            "Match",
            {
                "statsDateTime": int,
                "players": list[Player],
            },
        )

        Data = TypedDict(
            "Data",
            {
                "match": Match,
            },
        )

        ResponseDict = TypedDict(
            "ResponseDict",
            {
                "data": Data,
            },
        )


class GameCoordinatorAPISchema:
    # all these types are fake and they only serve as a band-aid fix for
    # ValvePython being extremely bad at type-hinting

    Player = NamedTuple(
        "Player",
        [
            ("account_id", int),
            ("hero_id", int),
            ("team", Literal[0, 1]),
            ("team_slot", Literal[1, 2, 3, 4, 5]),
        ],
    )

    CSourceTVGameSmall = NamedTuple(
        "CSourceTVGameSmall",
        [
            ("activate_time", int),
            ("deactivate_time", int),
            ("server_steam_id", int),
            ("lobby_id", int),
            ("league_id", int),
            ("lobby_type", int),
            ("game_time", int),
            ("delay", int),
            ("spectators", int),
            ("game_mode", int),
            ("average_mmr", int),
            ("match_id", int),
            ("series_id", int),
            ("sort_score", int),
            ("last_update_time", float),
            ("radiant_lead", int),
            ("radiant_score", int),
            ("dire_score", int),
            ("players", list[Player]),
            ("building_state", int),
            ("custom_game_difficulty", int),
        ],
    )

    GCToClientFindTopSourceTVGamesResponse = NamedTuple(
        "GCToClientFindTopSourceTVGamesResponse",
        [
            ("search_key", str),
            ("league_id", int),
            ("hero_id", int),
            ("start_game", int),
            ("num_games", int),
            ("game_list_index", int),
            ("game_list", list[CSourceTVGameSmall]),
            ("specific_games", bool),
        ],
    )
