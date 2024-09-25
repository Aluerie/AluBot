"""Slightly overcooked typing for OpenDota pulsefire-like client REST requests.

Note that it can be outdated, wrong, incomplete.
"""

from typing import Literal, NamedTuple, NotRequired, TypedDict

# ruff: noqa: UP013, UP014

__all__ = (
    "OpenDotaAPI",
    "StratzGraphQL",
    "GameCoordinatorAPI",
    "ODotaConstantsJson",
    "SteamWebAPI",
)


class OpenDotaAPI:
    """Schema representing OpenDota API."""

    class GetMatch:
        """GET /matches/{match_id} endpoint."""

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
                "name": str | None,
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
                "metadata": str | None,
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

    class PostRequest:
        """POST /request/{match_id} endpoint."""

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


class StratzGraphQL:
    """Schemas representing data structure for my GraphQL calls."""

    class GetFPCMatchToEdit:
        """Type-hinting for my GetFPCMatchToEdit query."""

        BuffEvent = TypedDict(
            "BuffEvent",
            {
                "itemId": int | None,
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
                "variant": int,
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


class GameCoordinatorAPI:
    """Duck typing for ValvePython stuff (they don't do any typing stuff)."""

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


class ODotaConstantsJson:
    """Schemas matching structure in OpenDota constants json files."""

    # heroes.json
    Hero = TypedDict(
        "Hero",
        {
            "id": int,
            "name": str,
            "primary_attr": str,
            "attack_type": str,
            "roles": list[str],
            "img": str,
            "icon": str,
            "base_health": int,
            "base_health_regen": float,
            "base_mana": int,
            "base_mana_regen": int,
            "base_armor": int,
            "base_mr": int,
            "base_attack_min": int,
            "base_attack_max": int,
            "base_str": int,
            "base_agi": int,
            "base_int": int,
            "str_gain": float,
            "agi_gain": float,
            "int_gain": float,
            "attack_range": int,
            "projectile_speed": int,
            "attack_rate": float,
            "base_attack_time": int,
            "attack_point": float,
            "move_speed": int,
            "turn_rate": float | None,
            "cm_enabled": bool,
            "legs": int | None,
            "day_vision": int,
            "night_vision": int,
            "localized_name": str,
        },
    )
    Heroes = dict[str, Hero]

    # get_ability_ids
    AbilityIDs = dict[str, str]

    # get_abilities
    AbilityAttrib = TypedDict(
        "AbilityAttrib",
        {
            "key": str,
            "header": str,
            "value": str,
            "generated": NotRequired[bool],
        },
    )
    Ability = TypedDict(
        "Ability",
        {
            "dname": str,
            "behavior": list[str],
            "dmg_type": str,
            "bkbpierce": str,
            "target_team": str,
            "target_type": list[str],
            "desc": str,
            "attrib": list[AbilityAttrib],
            "lore": str,
            "mc": list[str],  # mana cost
            "cd": list[str],  # cooldown
            "img": str,
        },
    )
    Talent = TypedDict(
        "Talent",
        {
            "dname": str,
        },
    )
    Abilities = dict[str, Ability | Talent]
    # get_hero_abilities
    HeroTalent = TypedDict(
        "HeroTalent",
        {
            "name": str,
            "level": int,
        },
    )
    HeroFacet = TypedDict(
        "HeroFacet",
        {
            "name": str,
            "icon": str,
            "color": str,
            "title": str,
            "gradient_id": int,
            "description": str,
        },
    )
    HeroAbilities = TypedDict(
        "HeroAbilities",
        {
            "abilities": list[str],
            # note that talents are ordered like this (it's exactly list of length 8):
            # 8 7
            # 6 5
            # 4 3
            # 2 1
            # so if it's even - it's left talent, if it's odd - right
            # level with help with... level :D
            "talents": list[HeroTalent],
            "facets": list[HeroFacet],
        },
    )
    HeroAbilitiesData = dict[str, HeroAbilities]

    # get items
    ItemAttrib = TypedDict(
        "ItemAttrib",
        {
            "key": str,
            "header": str,
            "value": str,
            "generated": NotRequired[bool],
        },
    )
    Item = TypedDict(
        "Item",
        {
            "hint": list[str],
            "id": int,
            "img": str,
            "dname": str,
            "qual": str,
            "cost": int,
            "notes": str,
            "attrib": list[ItemAttrib],
            "mc": Literal[False] | int,
            "cd": float,
            "lore": str,
            "components": list[str],
            "created": bool,
            "charges": bool,
        },
    )
    Items = dict[str, Item]


class SteamWebAPI:
    """Schemas for Steam Web API."""

    # 1. GET MATCH DETAILS

    MatchDetailsAbilityUpgrades = TypedDict(
        "MatchDetailsAbilityUpgrades",
        {
            "ability": int,
            "time": int,
            "level": int,
        },
    )
    MatchDetailsPlayer = TypedDict(
        "MatchDetailsPlayer",
        {
            "account_id": int,
            "player_slot": int,  # 0-9
            "team_number": int,  # 0-1
            "team_slot": int,  # 0-4
            "hero_id": int,
            "item_0": int,
            "item_1": int,
            "item_2": int,
            "item_3": int,
            "item_4": int,
            "item_5": int,
            "backpack_0": int,
            "backpack_1": int,
            "backpack_2": int,
            "item_neutral": int,
            "kills": int,
            "deaths": int,
            "assists": int,
            "leaver_status": int,  # 0-1
            "last_hits": int,
            "denies": int,
            "gold_per_min": int,
            "xp_per_min": int,
            "level": int,
            "net_worth": int,
            "aghanims_scepter": int,
            "aghanims_shard": int,
            "moonshard": int,
            "hero_damage": int,
            "tower_damage": int,
            "hero_healing": int,
            "gold": int,
            "gold_spent": int,
            "scaled_hero_damage": int,
            "scaled_tower_damage": int,
            "scaled_hero_healing": int,
            "ability_upgrades": list[MatchDetailsAbilityUpgrades],
        },
    )

    MatchDetailsPickBan = TypedDict(
        "MatchDetailsPickBan",
        {
            "is_pick": bool,
            "hero_id": int,
            "team": int,
            "order": int,
        },
    )
    MatchDetailsResult = TypedDict(
        "MatchDetailsResult",
        {
            "players": list[MatchDetailsPlayer],
            "duration": int,
            "pre_game_duration": int,
            "start_time": int,
            "match_id": int,
            "match_seq_num": int,
            "tower_status_radiant": int,
            "tower_status_dire": int,
            "barracks_status_radiant": int,
            "barracks_status_dire": int,
            "cluster": int,
            "first_blood_time": int,
            "lobby_type": int,
            "human_players": int,
            "leagueid": int,
            "game_mode": int,
            "flags": int,
            "engine": int,
            "radiant_score": int,
            "dire_score": int,
            "picks_bans": list[MatchDetailsPickBan],
        },
    )

    MatchDetails = TypedDict(
        "MatchDetails",
        {
            "result": MatchDetailsResult,
        },
    )

    # 2. GET REAL TIME STATS

    RealtimeStatsGraphData = TypedDict(
        "RealtimeStatsGraphData",
        {
            "graph_gold": list[int]
        }
    )

    RealtimeStatsBuilding = TypedDict(
        "RealtimeStatsBuilding",
        {
            "team": Literal[2, 3],
            "heading": float,
            "type": int,
            "lane": int,
            "tier": int,
            "x": float,
            "y": float,
            "destroyed": bool,
        },
    )

    RealtimeStatsTeamPlayer = TypedDict(
        "RealtimeStatsTeamPlayer",
        {
            "accountid": int,  # cSpell: ignore accountid
            "playerid": Literal[0, 1, 2, 3, 4, 5, 6, 7, 8, 9],  # cSpell: ignore playerid
            "name": str,
            "team": Literal[2, 3],
            "heroid": int,  # cSpell: ignore heroid
            "level": int,
            "kill_count": int,
            "death_count": int,
            "assists_count": int,
            "denies_count": int,
            "lh_count": int,
            "gold": int,
            "x": float,
            "y": float,
            "net_worth": int,
            "abilities": list[int],
            "items": list[int],
            "team_slot": Literal[0, 1, 2, 3, 4],
        },
    )

    RealtimeStatsTeam = TypedDict(
        "RealtimeStatsTeam",
        {
            "team_number": Literal[2, 3],
            "team_id": int,
            "team_name": str,
            "team_tag": str,
            "team_logo": str,  # string-number
            "score": int,
            "net_worth": int,
            "team_logo_url": str,
            "players": list[RealtimeStatsTeamPlayer],
        },
    )

    RealtimeStatsMatch = TypedDict(
        "RealtimeStatsMatch",
        {
            "server_steam_id": str,  # string-number, my favourite
            "match_id": str,  # string-number
            "timestamp": int,
            "game_time": int,
            "game_mode": int,
            "league_id": int,
            "league_node_id": int,
            "game_state": int,
            "lobby_type": int,
            "start_timestamp": int,
        },
    )

    RealtimeStats = TypedDict(
        "RealtimeStats",
        {
            "match": RealtimeStatsMatch,
            "teams": list[RealtimeStatsTeam],
            "buildings": list[RealtimeStatsBuilding],
            "graph_data": RealtimeStatsGraphData,
        },
    )
