from __future__ import annotations

import asyncio
import re

import discord

try:
    from .const import Regex
except ImportError:
    # testing stuff, regex is tough sometimes.
    import sys

    sys.path.append("D:/LAPTOP/AluBot")
    from utils.const import Regex


async def get_metadata_embed_links(message: discord.Message) -> discord.Message | None:
    """Get links from website metadata embeds and make them clickable by sending extra embed with links.

    Unfortunately `certified discord tm moment` where
    it does not allow links to be clickable in website metadata embeds
    thus we have to extract them ourselves after it's compiled on discord side.
    """
    # wait till website meta embed actually renders
    await asyncio.sleep(2.7)

    links = []
    colour = discord.Colour.pink()
    for e in message.embeds:
        links += re.findall(Regex.URL, str(e.description))
        colour = e.colour

    if links:
        embed = discord.Embed(
            color=colour,
            description="\n".join(links),
        ).set_author(name="links in the embed above in clickable format:")
        return await message.channel.send(embed=embed)


FIX_DICT: dict[str, str] = {
    # social network: better embed site,
    # note the "slash" in the end and "https://" are important
    "x.com": "https://fxtwitter.com",
    "twitter.com": "https://fxtwitter.com",
    "instagram.com": "https://ddinstagram.com",
    "tiktok.com": "https://tnktok.com",
}


def url_sub_regex(x: str) -> str:
    x = re.escape(x)
    return rf"""
        http[s]?
        ://
        (?:www\.)?
        ({x})                                                                              # group 1 - the actual site
        (/ (?: [a-zA-Z] | [0-9] | [$-_@.&+] | [!*(),] | (?:% [0-9a-fA-F][0-9a-fA-F]) )+ )  # group 2 - the rest of url
    """


COMPILED_REGEX = re.compile("%s" % "|".join([url_sub_regex(key) for key in FIX_DICT]), re.X)


def fix_social_links(text: str, omit_rest: bool = False) -> str | None:
    """Fix metadata embeds for social links with better embeds.

    Currently supported:
    * Twitter       - https://fxtwitter.com/
    * Instagram     - https://ddinstagram.com
    * Tiktok        - https://tnktok.com

    Parameters
    ----------
    text
        Text to search social links in.
    omit_rest
        Whether the final result should only include "better" links.

    Returns
    -------
        Either
        * `str` text with new social links if a link to replace was found or `None` in case nothing was found;
        * `None` in case no match was found.

    Examples
    --------
    ```py
    fix_social_links("XD https://x.com/IceFrog/status/1718834746300719265 XD https://x.com/IceFrog/status/1718834746300719265 XD")
    "XD https://fxtwitter.com/IceFrog/status/1718834746300719265 XD https://fxtwitter.com/IceFrog/status/1718834746300719265 XD"
    ```
    Sources
    ------
    * https://stackoverflow.com/a/15175239/19217368
    """
    if found := COMPILED_REGEX.findall(text):
        if omit_rest:
            # found is list[tuple[str, ...]], i.e.
            # [
            #   ('x.com', '/IceFrog/status/1718834746300719265', '', '', '', '', '', ''),
            #   ('x.com', '/IceFrog/status/1718834746300719265', '', '', '', '', '', '')
            # ]
            return "\n".join([f"{FIX_DICT[group[0]]}{group[1]}" for group in found])
        else:
            return COMPILED_REGEX.sub(lambda mo: rf"{FIX_DICT[mo.group(1).lower()]}{mo.group(2)}", text)
    else:
        return None


if __name__ == "__main__":
    text = "XD https://x.com/IceFrog/status/1718834746300719265 XD https://x.com/IceFrog/status/1718834746300719265 XD"
    result = fix_social_links(text, omit_rest=True)
    print(result)  # noqa: T201
