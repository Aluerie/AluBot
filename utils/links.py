from __future__ import annotations

import re
from typing import TYPE_CHECKING

from aiohttp.client_exceptions import ClientConnectorError

from .const import REGEX_URL_LINK

if TYPE_CHECKING:
    from discord import Embed


async def replace_tco_links(session, embed: Embed) -> Embed:
    text = embed.description
    if text:
        url_array = re.findall(REGEX_URL_LINK, str(text))
        try:
            for url in url_array:
                async with session.get(url) as resp:
                    link_for_embed = f'[Redirect link]({resp.url})'
                    text = text.replace(url, link_for_embed)
        except ClientConnectorError:
            # well sorry bro twitter is still banned it seEmote like
            pass
        embed.description = text
    return embed


def move_link_to_title(embed: Embed) -> Embed:
    # embed.url = link
    embed.title = 'Twitter link'
    return embed


def get_links_from_str(string):
    # url_array = re.findall(REGEX_URL_LINK, str(string))
    # return [item for item in url_array if 'twitter' in item]
    return re.findall(REGEX_URL_LINK, str(string))
