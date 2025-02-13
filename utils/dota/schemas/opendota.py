"""Slightly overcooked typing for OpenDota pulsefire-like client REST requests.

Note that it can be outdated, wrong, incomplete.
"""
from __future__ import annotations

from typing import Literal, NotRequired, TypedDict

__all__ = (
    "MatchResponse",
    "ParseResponse",
)

# GET /matches/{match_id}


class MatchResponse(TypedDict):
    barracks_status_dire: int
    barracks_status_radiant: int
    cluster: int
    dire_score: int
    duration: int
    engine: int
    first_blood_time: int
    flags: int
    game_mode: int
    human_players: int
    leagueid: int
    lobby_type: int
    match_id: int
    match_seq_num: int
    metadata: str | None
    od_data: ODData
    patch: int
    picks_bans: list[PickBan]
    players: list[Player]
    pre_game_duration: int
    radiant_score: int
    radiant_win: bool
    region: int
    replay_salt: int
    replay_url: str
    series_id: int
    series_type: int
    start_time: int
    tower_status_dire: int
    tower_status_radiant: int


class ODData(TypedDict):
    has_api: bool
    has_gcdata: bool
    has_parsed: bool
    archive: bool


class PickBan(TypedDict):
    is_pick: bool
    hero_id: int
    team: int
    order: int


class Player(TypedDict):
    abandons: int
    ability_upgrades_arr: list[int]
    account_id: NotRequired[int]
    aghanims_scepter: Literal[0, 1]
    aghanims_shard: Literal[0, 1]
    assists: int
    backpack_0: int
    backpack_1: int
    backpack_2: int
    benchmarks: BenchMarks
    cluster: int
    deaths: int
    denies: int
    duration: int
    game_mode: int
    gold: int
    gold_per_min: int
    gold_spent: int
    hero_damage: int
    hero_healing: int
    hero_id: int
    isRadiant: bool
    is_contributor: bool
    is_subscriber: bool
    item_0: int
    item_1: int
    item_2: int
    item_3: int
    item_4: int
    item_5: int
    item_neutral: int
    kda: float
    kills: int
    kills_per_min: float
    last_hits: int
    last_login: str
    leaver_status: Literal[0, 1]
    level: int
    lobby_type: int
    lose: Literal[0, 1]
    moonshard: Literal[0, 1]
    name: str | None
    net_worth: int
    party_id: int
    party_size: int
    patch: int
    permanent_buffs: list[PermanentBuff]
    personaname: str
    player_slot: str
    radiant_win: bool
    rank_tier: int
    region: int
    start_time: int
    team_number: Literal[0, 1]
    team_slot: int
    total_gold: int
    total_xp: int
    tower_damage: int
    win: Literal[0, 1]
    xp_per_min: int


class BenchMarks(TypedDict):
    gold_per_min: BenchMarkData
    xp_per_min: BenchMarkData
    kills_per_min: BenchMarkData
    last_hits_per_min: BenchMarkData
    hero_damage_per_min: BenchMarkData
    hero_healing_per_min: BenchMarkData
    tower_damage: BenchMarkData


class BenchMarkData(TypedDict):
    raw: int
    pct: float


class PermanentBuff(TypedDict):
    permanent_buff: int
    stack_count: int
    grant_time: int


# POST /request/{match_id}


class ParseResponse(TypedDict):
    job: ParseJob


class ParseJob(TypedDict):
    jobId: int
