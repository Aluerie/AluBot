from __future__ import annotations

import asyncio
import re
from typing import TYPE_CHECKING

import aiohttp
import discord

from .const import Regex

if TYPE_CHECKING:
    from discord import Embed


async def replace_tco_links(session: aiohttp.ClientSession, embed: Embed) -> Embed:
    text = embed.description
    if text:
        url_array = re.findall(Regex.URL, str(text))
        try:
            for url in url_array:
                async with session.get(url) as resp:
                    link_for_embed = f"[Redirect link]({resp.url})"
                    text = text.replace(url, link_for_embed)
        except aiohttp.ClientConnectorError:
            pass
        embed.description = text
    return embed


def move_link_to_title(embed: Embed) -> Embed:
    # embed.url = link
    embed.title = "Twitter link"
    return embed


def get_links_from_str(string: str) -> list[str]:
    # url_array = re.findall(REGEX_URL_LINK, str(string))
    # return [item for item in url_array if 'twitter' in item]
    return re.findall(Regex.URL, str(string))


async def extra_send_fxtwitter_links(message: discord.Message) -> discord.Message | None:
    """Unfortunately `certified discord tm moment` where
    it does not allow links to be clickable in website embeds
    thus we have to extract them ourselves.
    """

    # wait till website meta embed actually renders
    await asyncio.sleep(2.7)

    # Okay discord is a bit stupid and does not allow hyperlinks from website embeds
    # this is why I will have to do the job myself.
    links = []
    colour = discord.Colour.pink()
    for e in message.embeds:
        links += re.findall(Regex.URL, str(e.description))
        colour = e.colour

    if links:
        e = discord.Embed(color=colour)
        e.description = "\n".join(links)
        return await message.channel.send(embed=e)
