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
    "reddit.com": "https://rxddit.com",
    "instagram.com": "https://ddinstagram.com",
    "tiktok.com": "https://tnktok.com",
    "twitch.tv": "https://fxtwitch.seria.moe",
    "deviantart.com": "https://fixdeviantart.com",
    "tumblr.com": "https://tpmblr.com",
    "pixiv.net": "https://phixiv.net",
}
# PS. in November 2024 I finally found out that some other people made the same bot/feature for Discord:
# * https://betterdiscord.app/plugin/SocialMediaLinkConverter
# * https://github.com/seriaati/embed-fixer
# So, check it out, they might find something better.

COMPILED_REGEX = re.compile(
    rf"""
        http[s]?
        ://
        (?:www\.)?
        ({'|'.join(re.escape(x) for x in FIX_DICT)})                                       # group 1 - the actual site
        (/ (?: [a-zA-Z] | [0-9] | [$-_@.&+] | [!*(),] | (?:% [0-9a-fA-F][0-9a-fA-F]) )+ )  # group 2 - the rest of url
    """,
    flags=re.X | re.I,  # X = VERBOSE, I = IGNORECASE
)


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
    text = (
        "https://www.instagram.com/p/DBg0L6foRNW/ bla bla bla bla bla bla bla"
        "https://x.com/IceFrog/status/1718834746300719265"
    )
    fix_social_links(text)
    "https://ddinstagram.com/p/DBg0L6foRNW/ bla bla bla bla bla bla bla https://fxtwitter.com/IceFrog/status/1718834746300719265"
    ```
    Sources
    ------
    * https://stackoverflow.com/a/15175239/19217368
    """
    if found := COMPILED_REGEX.findall(text):
        if omit_rest:
            # found is list[tuple[str, ...]], where tuple has 2 strings (because we have 2 matching groups in regex)
            #  i.e. [('instagram.com', '/p/DBg0L6foRNW/'), ('x.com', '/IceFrog/status/1718834746300719265')]
            return "\n".join([f"{FIX_DICT[group[0]]}{group[1]}" for group in found])
        else:
            return COMPILED_REGEX.sub(lambda mo: rf"{FIX_DICT[mo.group(1).lower()]}{mo.group(2)}", text)
    else:
        return None


if __name__ == "__main__":
    text = (
        "https://www.instagram.com/p/DBg0L6foRNW/ bla bla bla bla bla bla bla "
        "https://x.com/IceFrog/status/1718834746300719265"
    )
    result = fix_social_links(text)
    print(result)  # noqa: T201
