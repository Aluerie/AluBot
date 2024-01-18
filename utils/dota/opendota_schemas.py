"""
Slightly overcooked typing for OpenDota pulsefire-like client REST requests.

Note that it can be outdated, wrong, incomplete. 
"""

from typing import Any, Literal, Mapping, NotRequired, Optional, TypedDict

__all__ = ("OpenDotaAPISchema",)


class OpenDotaAPISchema:
    ### The following schemas are for GET /matches/{match_id} endpoint

    ObjectiveEvent = TypedDict(
        "ObjectiveEvent",
        {  # I'm not diving into those too much.
            "time": int,
            "type": str,
            "unit": NotRequired[str],
            "key": NotRequired[str],
            "slot": NotRequired[int],
            "player_slot": NotRequired[int],
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

    TeamfightPlayer = TypedDict(
        "TeamfightPlayer",
        {
            "deaths_pos": dict[str, dict[str, int]],
            "ability_uses": Mapping[str, int],
            "ability_targets": dict,
            "item_uses": Mapping[str, int],
            "killed": Mapping[str, int],
            "deaths": int,
            "buybacks": int,
            "damage": int,
            "healing": int,
            "gold_delta": int,
            "xp_delta": int,
            "xp_start": int,
            "xp_end": int,
        },
    )

    TeamFight = TypedDict(
        "TeamFight",
        {
            "start": int,
            "end": int,
            "last_death": int,
            "deaths": int,
            "players": list,
        },
    )

    MaxHeroHit = TypedDict(
        "MaxHeroHit",
        {
            "type": str,
            "time": int,
            "max": bool,
            "inflictor": str,
            "unit": str,
            "key": str,
            "value": int,
            "slot": int,
            "player_slot": int,
        },
    )

    PermanentBuff = TypedDict(
        "PermanentBuff",
        {
            "permanent_buff": int,
            "stack_count": int,
            "grant_time": int,
        },
    )

    PurchaseLogEvent = TypedDict(
        "PurchaseLogEvent",
        {
            "time": int,
            "key": str,
        },
    )

    RuneLogEvent = TypedDict(
        "PurchaseLogEvent",
        {
            "time": int,
            "key": int,
        },
    )

    BenchMarkData = TypedDict(
        "BenchMarkData",
        {
            "raw": int,
            "pct": float,
        },
    )
    BenchMark = TypedDict(
        "BenchMark",
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
            "player_slot": int,
            "ability_targets": dict[str, Mapping[str, int]],
            "ability_upgrades_arr": list[int],
            "ability_uses": Mapping[str, int],
            "account_id": Optional[int],
            "actions": dict[str, int],
            "additional_units": Optional[dict[str, int]],
            "assists": int,
            "backpack_0": int,
            "backpack_1": int,
            "backpack_2": int,
            "backpack_3": Optional[int],
            "buyback_log": list[ObjectiveEvent],
            "camps_stacked": int,
            "connection_log": list[Any],
            "creeps_stacked": int,
            "damage": Mapping[str, int],
            "damage_inflictor": Mapping[str, int],
            "damage_inflictor_received": Mapping[str, int],
            "damage_taken": Mapping[str, int],
            "damage_targets": dict[str, Mapping[str, int]],
            "deaths": int,
            "denies": int,
            "dn_t": list[int],
            "firstblood_claimed": int,  # cSpell:ignore firstblood
            "gold": int,
            "gold_per_min": int,
            "gold_reasons": Mapping[str, int],
            "gold_spent": int,
            "gold_t": list[int],
            "hero_damage": int,
            "hero_healing": int,
            "hero_hits": Mapping[str, int],
            "hero_id": int,
            "item_0": int,
            "item_1": int,
            "item_2": int,
            "item_3": int,
            "item_4": int,
            "item_5": int,
            "item_neutral": int,
            "item_uses": Mapping[str, int],
            "kill_streaks": Mapping[str, int],
            "killed": Mapping[str, int],
            "killed_by": Mapping[str, int],
            "kills": int,
            "kills_log": list[ObjectiveEvent],
            "lane_pos": dict[str, dict[str, int]],
            "last_hits": int,
            "leaver_status": int,
            "level": int,
            "lh_t": list[int],
            "life_state": Mapping[str, int],
            "max_hero_hit": MaxHeroHit,
            "multi_kills": Mapping[str, int],
            "net_worth": int,
            "obs": dict[str, dict[str, int]],
            "obs_left_log": list[dict[Any, Any]],
            "obs_log": list[dict[Any, Any]],
            "obs_placed": int,
            "party_id": int,
            "party_size": int,
            "performance_others": Optional[Any],
            "permanent_buffs": list[PermanentBuff],
            "pings": int,
            "pred_vict": bool,  # cSpell:ignore vict
            "purchase": dict[str, int],
            "purchase_log": list[PurchaseLogEvent],
            "randomed": bool,  # cSpell:ignore randomed
            "repicked": Optional[bool],  # cSpell:ignore repicked
            "roshans_killed": int,  # cSpell:ignore roshans
            "rune_pickups": int,
            "runes": dict[str, int],
            "runes_log": list[RuneLogEvent],
            "sen": dict[str, dict[str, int]],
            "sen_left_log": list[dict[Any, Any]],
            "sen_log": list[dict[Any, Any]],
            "sen_placed": int,
            "stuns": float,
            "teamfight_participation": float,
            "times": list[int],
            "tower_damage": int,
            "towers_killed": int,
            "xp_per_min": int,
            "xp_reasons": dict[str, int],
            "xp_t": list[int],
            "team_number": int,
            "team_slot": int,
            "aghanims_scepter": Literal[0, 1],  # cSpell:ignore aghanims
            "aghanims_shard": Literal[0, 1],  # cSpell:ignore aghanims
            "moonshard": Literal[0, 1],  # cSpell:ignore moonshard
            "radiant_win": bool,
            "start_time": int,
            "duration": int,
            "cluster": int,
            "lobby_type": int,
            "game_mode": int,
            "is_contributor": bool,
            "patch": int,
            "region": int,
            "isRadiant": bool,
            "win": Literal[0, 1],
            "lose": Literal[0, 1],
            "total_gold": int,
            "total_xp": int,
            "kills_per_min": float,
            "kda": float,
            "abandons": int,
            "neutral_kills": int,
            "tower_kills": int,
            "courier_kills": int,
            "lane_kills": int,
            "hero_kills": int,
            "observer_kills": int,
            "sentry_kills": int,
            "roshan_kills": int,
            "necronomicon_kills": int,  # cSpell:ignore necronomicon
            "ancient_kills": int,
            "buyback_count": int,
            "observer_uses": int,
            "sentry_uses": int,
            "lane_efficiency": float,
            "lane_efficiency_pct": int,
            "lane": int,
            "lane_role": int,
            "is_roaming": bool,
            "purchase_time": dict[str, int],
            "first_purchase_time": dict[str, int],
            "item_win": dict[str, int],
            "item_usage": dict[str, int],
            "purchase_tpscroll": int,  # cSpell:ignore tpscroll
            "actions_per_min": int,
            "life_state_dead": int,
            "rank_tier": Optional[int],
            "is_subscriber": bool,
            "cosmetics": list[str],
            "benchmarks": BenchMark,
        },
    )

    ODData = TypedDict(
        "OData",
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
            "match_id": int,
            "barracks_status_dire": int,
            "barracks_status_radiant": int,
            "chat": list[ObjectiveEvent],
            "cluster": int,
            "cosmetics": list[Any],
            "dire_score": int,
            "dire_team_id": Optional[int],
            "draft_timings": list[Any],
            "duration": int,
            "engine": int,
            "first_blood_time": int,
            "game_mode": int,
            "human_players": int,
            "leagueid": int,  # cSpell:ignore leagueid
            "lobby_type": int,
            "match_seq_num": int,
            "negative_votes": Optional[int],
            "objectives": list[ObjectiveEvent],
            "picks_bans": list[PickBan],
            "positive_votes": Optional[int],
            "radiant_gold_adv": list[int],
            "radiant_score": int,
            "radiant_team_id": Optional[int],
            "radiant_win": bool,
            "radiant_xp_adv": list[int],
            "skill": Optional[str],
            "start_time": int,
            "teamfights": list[TeamFight],  # cSpell:ignore teamfights
            "tower_status_dire": int,
            "tower_status_radiant": int,
            "version": int,
            "players": list[Player],
            "pre_game_duration": int,
            "flags": int,
            "od_data": ODData,
            "metadata": Optional[Any],
            "patch": int,
            "region": int,
            "all_word_counts": dict[str, int],
            "my_word_counts": dict[str, int],
            "throw": int,
            "loss": int,
        },
    )

    ### The following schemas are for POST /request/{match_id} endpoint
    ParseJob = TypedDict(
        "RequestJob",
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
