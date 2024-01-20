"""
Glossary:
* platform 
    RiotGames routing platform names with numbers like `na1`.
* continent 
    RiotGames routing continent names like `americas`.
* region 
    Garbage term, because Riot API uses it as both platform and region.
    So in pulsefire riot api client calls we use both continent and platform for `region=` keyword argument.
* server 
    Normal human-readable server abbreviations like 'na'. 
    Name does not exist in riot api calls and only used for display purposes.
"""
from typing import Literal

__all__ = (
    "LiteralPlatform",
    "LiteralContinent",
    "LiteralServer",
    "PLATFORM_TO_CONTINENT",
    "SERVER_TO_PLATFORM",
    "PLATFORM_TO_SERVER",
    "SERVER_TO_CONTINENT",
)


LiteralPlatform = Literal[
    "BR1", "EUN1", "EUW1", "JP1", "KR", "LA1", "LA2", "NA1", "OC1", "PH2", "RU", "SG2", "TH2", "TR1", "TW2", "VN2"
] #todo: maybe fix all other regions
LiteralContinent = Literal["AMERICAS", "ASIA", "EUROPE"]
LiteralServer = Literal["BR", "EUN", "EUW", "JP", "KR", "LAN", "LAS", "NA", "OC", "RU", "TR"]


PLATFORM_TO_CONTINENT: dict[LiteralPlatform, LiteralContinent] = {
    "BR1": "AMERICAS",
    "EUN1": "EUROPE",
    "EUW1": "EUROPE",
    "JP1": "ASIA",
    "KR": "ASIA",
    "LA1": "AMERICAS",
    "LA2": "AMERICAS",
    "NA1": "AMERICAS",
    "OC1": "ASIA",
    "RU": "EUROPE",
    "TR1": "EUROPE",
}

SERVER_TO_PLATFORM: dict[LiteralServer, LiteralPlatform] = {
    "BR": "BR1",
    "EUN": "EUN1",
    "EUW": "EUW1",
    "JP": "JP1",
    "KR": "KR",
    "LAN": "LA1",
    "LAS": "LA2",
    "NA": "NA1",
    "OC": "OC1",
    "RU": "RU",
    "TR": "TR1",
}

PLATFORM_TO_SERVER: dict[LiteralPlatform, LiteralServer] = {
    platform: server for server, platform in SERVER_TO_PLATFORM.items()
}

SERVER_TO_CONTINENT: dict[LiteralServer, LiteralContinent] = {
    server: PLATFORM_TO_CONTINENT[platform] for server, platform in SERVER_TO_PLATFORM.items()
}
