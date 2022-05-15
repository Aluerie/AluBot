from discord import Embed
from aiohttp.client_exceptions import ClientConnectorError
from utils.var import Rgx
import re


async def replace_tco_links(session, embed: Embed) -> Embed:
    text = embed.description
    url_array = re.findall(Rgx.url_danny, str(text))
    try:
        for url in url_array:
            async with session.get(url) as resp:
                link_for_embed = f'[Redirect link]({resp.url})'
                text = text.replace(url, link_for_embed)
    except ClientConnectorError:
        # well sorry bro twitter is still banned it seems like
        pass
    embed.description = text
    return embed


def move_link_to_title(link, embed: Embed) -> Embed:
    embed.url = link
    embed.title = 'Twitter link'
    return embed


def get_links_from_str(string):
    # url_array = re.findall(Rgx.url_danny, str(string))
    # return [item for item in url_array if 'twitter' in item]
    return re.findall(Rgx.url_danny, str(string))
