"""
Glossary:
* platform - RiotGames routing platform names with numbers like `na1`. Name matches PyOT docs.
* region - RiotGames routing region names like `americas`. Name matches PyOT docs.
* server - Normal regions like 'na' in lower case. Name does not exist in PyOT docs.
"""
from typing import Literal

__all__ = (
    'LiteralPlatform',
    'LiteralRegion',
    'LiteralServer',
    'LiteralServerUpper',
    'server_to_platform',
    'platform_to_server',
    'platform_to_region',
    'SOLO_RANKED_5v5_QUEUE_ENUM',
    'LOL_GAME_CATEGORY_TWITCH_ID'
)

LiteralPlatform = Literal['br1', 'eun1', 'euw1', 'jp1', 'kr', 'la1', 'la2', 'na1', 'oc1', 'ru', 'tr1']
LiteralRegion = Literal['americas', 'asia', 'europe']
LiteralServerUpper = Literal['BR', 'EUN', 'EUW', 'JP', 'KR', 'LAN', 'LAS', 'NA', 'OC', 'RU', 'TR']
LiteralServer = Literal[
    'BR', 'EUN', 'EUW', 'JP', 'KR', 'LAN', 'LAS', 'NA', 'OC', 'RU', 'TR',
    'br', 'eun', 'euw', 'jp', 'kr', 'lan', 'las', 'na', 'oc', 'ru', 'tr'
]


platform_to_region_dict = {
    'br1': 'americas',
    'eun1': 'europe',
    'euw1': 'europe',
    'jp1': 'asia',
    'kr': 'asia',
    'la1': 'americas',
    'la2': 'americas',
    'na1': 'americas',
    'oc1': 'asia',
    'ru': 'europe',
    'tr1': 'europe'
}

server_to_platform_dict = {
    'br': 'br1',
    'eun': 'eun1',
    'euw': 'euw1',
    'jp': 'jp1',
    'kr': 'kr',
    'lan': 'la1',
    'las': 'la2',
    'na': 'na1',
    'oc': 'oc1',
    'ru': 'ru',
    'tr': 'tr1'
}

platform_to_server_dict = {
    v: k
    for k, v in server_to_platform_dict.items()
}


def server_to_platform(server: LiteralServer) -> LiteralPlatform:
    """Convert server to platform"""
    return server_to_platform_dict[server.lower()]


def platform_to_server(platform: LiteralPlatform) -> LiteralServer:
    """Convert platform to server"""
    return platform_to_server_dict[platform.lower()]


def platform_to_region(platform: LiteralPlatform) -> LiteralRegion:
    """Convert platform to routing"""
    return platform_to_region_dict[platform]


# https://static.developer.riotgames.com/docs/lol/queues.json
# says 420 is 5v5 Ranked Solo games
SOLO_RANKED_5v5_QUEUE_ENUM = 420

# just manually figured out
LOL_GAME_CATEGORY_TWITCH_ID = 21779
