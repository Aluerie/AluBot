"""Schemas representing data structure for Steam WEB API."""
from __future__ import annotations

from typing import Literal, TypedDict

__all__ = (
    "MatchDetailsResponse",
    "RealTimeStatsResponse",
)


# 1. GET MATCH DETAILS
class MatchDetailsResponse(TypedDict):
    result: Result


class Result(TypedDict):
    players: list[Player]
    duration: int
    pre_game_duration: int
    start_time: int
    match_id: int
    match_seq_num: int
    tower_status_radiant: int
    tower_status_dire: int
    barracks_status_radiant: int
    barracks_status_dire: int
    cluster: int
    first_blood_time: int
    lobby_type: int
    human_players: int
    leagueid: int
    game_mode: int
    flags: int
    engine: int
    radiant_score: int
    dire_score: int
    picks_bans: list[PickBan]


class PickBan(TypedDict):
    is_pick: bool
    hero_id: int
    team: int
    order: int


class Player(TypedDict):
    account_id: int
    player_slot: int
    team_number: int
    team_slot: int
    hero_id: int
    item_0: int
    item_1: int
    item_2: int
    item_3: int
    item_4: int
    item_5: int
    backpack_0: int
    backpack_1: int
    backpack_2: int
    item_neutral: int
    kills: int
    deaths: int
    assists: int
    leaver_status: int
    last_hits: int
    denies: int
    gold_per_min: int
    xp_per_min: int
    level: int
    net_worth: int
    aghanims_scepter: int
    aghanims_shard: int
    moonshard: int
    hero_damage: int
    tower_damage: int
    hero_healing: int
    gold: int
    gold_spent: int
    scaled_hero_damage: int
    scaled_tower_damage: int
    scaled_hero_healing: int
    ability_upgrades: list[AbilityUpgrades]


class AbilityUpgrades(TypedDict):
    ability: int
    time: int
    level: int


# 2. GET REAL TIME STATS


class RealTimeStatsResponse(TypedDict):
    match: Match
    teams: list[Team]
    buildings: list[Building]
    graph_data: GraphData


class Match(TypedDict):
    server_steam_id: str
    match_id: str
    timestamp: int
    game_time: int
    game_mode: int
    league_id: int
    league_node_id: int
    game_state: int
    lobby_type: int
    start_timestamp: int


class Team(TypedDict):
    team_number: Literal[2, 3]
    team_id: int
    team_name: str
    team_tag: str
    team_logo: str
    score: int
    net_worth: int
    team_logo_url: str
    players: list[TeamPlayer]


class TeamPlayer(TypedDict):
    accountid: int
    playerid: Literal[0, 1, 2, 3, 4, 5, 6, 7, 8, 9]
    name: str
    team: Literal[2, 3]
    heroid: int
    level: int
    kill_count: int
    death_count: int
    assists_count: int
    denies_count: int
    lh_count: int
    gold: int
    x: float
    y: float
    net_worth: int
    abilities: list[int]
    items: list[int]
    team_slot: Literal[0, 1, 2, 3, 4]


class Building(TypedDict):
    team: Literal[2, 3]
    heading: float
    type: int
    lane: int
    tier: int
    x: float
    y: float
    destroyed: bool


class GraphData(TypedDict):
    graph_gold: list[int]
