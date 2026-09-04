"""
Embed Fixer.

This module aims to solve a common problem with social media websites, where
if a person shares a link from those social medias (i.e. an instagram reel, tweet, reddit post, spotify track) -
the resulting meta-embed in Discord app is so bad and uninformative that other people either
have to click the link to actually see what it's about or ignore.
Both results are bad.

And here comes this module which will try to solve this problem by replacing people's messages with mimics
and using better embed services.

Similar projects
----------------
* https://github.com/seriaati/embed-fixer
* https://betterdiscord.app/plugin/SocialMediaLinkConverter (Now deleted)

License
-------
* This Source Code Form is subject to the terms of the [Mozilla Public License v2.0](<http://mozilla.org/MPL/2.0/>).
* Copyright (C) 2020-present [Aluerie](<https://github.com/Aluerie>).
"""

from __future__ import annotations

import asyncio
import logging
import re
from typing import TYPE_CHECKING, Any, override

import discord
from discord import app_commands
from discord.ext import commands

from bot import AluCog, AluContext
from utils import const, mimics

if TYPE_CHECKING:
    from bot import AluBot, AluInteraction

__all__ = ("FixSocialLinks",)


log = logging.getLogger(__name__)
log.setLevel(logging.INFO)  # .DEBUG)

SUPPORTED_SITES_DISPLAY_NAMES = (
    # Also remember to edit doc-string for `slash_fix_links`
    "Twitter",
    "Reddit",
    "Instagram",
    "TikTok",
    "DeviantArt",
    "Tumblr",
    "Pixiv",
    "Bsky",
    "Twitch Clips",
    "Spotify",
)

FIX_DICT: dict[str, str] = {
    # mapping: social network -> better embed site,
    # note the "slash" absence in the end and "https://" are important
    # cSpell: disable
    "x": "fxtwitter.com",
    "twitter": "fxtwitter.com",
    "reddit": "rxddit.com",
    "instagram": "oginstagram.com",
    "tiktok": "tnktok.com",
    "deviantart": "fixdeviantart.com",
    "tumblr": "tpmblr.com",
    "pixiv": "phixiv.net",
    "bsky": "bskyx.app",
    "twitch": "fxtwitch.seria.moe/clip",
    "clips": "fxtwitch.seria.moe/clip",
    "spotify": "fxspotify.com",
    # cSpell: enable
}

EMBED_FIXER_REGEX_PATTERN = re.compile(
    r"""
        # group(0) - the whole URL
        # group(1) - pre URL stuff
        (
        http[s]?
        ://
        (?: [a-zA-Z]+ \.)?  # `www.` or some subdomains like `open.spotify.`
        )
        # group(2) - the actual site host
        (
        x\.com|
        twitter\.com|
        reddit\.com|
        instagram\.com|
        tiktok\.com|
        deviantart\.com|
        tumblr\.com|
        pixiv\.net|
        bsky\.app|
        twitch\.tv/(?:[a-zA-Z]|[0-9]|[_])+/clip|
        clips\.twitch\.tv|
        spotify\.com
        )
        # group(3) - the rest of url
        # it's taken from `?tag url regex` in discord.py server. In a nutshell:
        # letters | digits | some symbols | some more symbols | url %percent-encoded symbols, i.e. %20 for space
        (/ (?: [a-zA-Z] | [0-9] | [$-_@.&+] | [!*(),] | (?:% [0-9a-fA-F][0-9a-fA-F]) )+ )
    """,
    flags=re.VERBOSE | re.IGNORECASE,  # X = VERBOSE, I = IGNORECASE
)


def find_all_links_to_fix(text: str) -> str:
    """
    Find common social links in text.

    Parameters
    ----------
    text: str
        Text to search social links in.

    Returns
    -------
    str
        A list of fixed links joined with line-break.
    """

    # Just a reminder on what groups actually are:
    # text = "https://www.instagram.com/p/DBg0L6foRNW/ bla bla bla https://x.com/IceFrog/status/1718834746300719265"
    # for group in EMBED_FIXER_REGEX_PATTERN.findall(text):
    #     print(group)
    #     return
    # >>> ('https://www.', 'instagram.com', '/p/DBg0L6foRNW/'), e.g. `group[1] = 'instagram.com'`, etc
    return "\n".join(
        [
            group[0].replace("www.", "") + FIX_DICT[group[1].lower().split(".")[0]] + group[2]
            for group in EMBED_FIXER_REGEX_PATTERN.findall(text)
        ]
    )


def subn_links_to_fix(text: str) -> tuple[str, int]:
    """
    Fix common social links by replacing them with links that provide better meta-embeds for Discord UI.

    Parameters
    ----------
    text: str
        Text to search social links in.

    Returns
    -------
    tuple[str, int]
        `re.subn` returns tuple `(new_string, number_of_subs_made)` which can be useful.

    Sources
    ------
    * https://stackoverflow.com/a/15175239/19217368
    """

    # text = "https://www.instagram.com/p/DBg0L6foRNW/ bla bla bla https://x.com/IceFrog/status/1718834746300719265"
    # mo.group(0) is 'https://www.instagram.com/p/DBg0L6foRNW/'
    # mo.group(1) is 'instagram.com'
    # mo.group(2) is '/p/DBg0L6foRNW/'
    # So `.findall` doesn't include `group(0)` into its groups, which makes sense, but might be confusing.
    return EMBED_FIXER_REGEX_PATTERN.subn(
        lambda mo: mo.group(1).replace("www.", "") + FIX_DICT[mo.group(2).lower().split(".")[0]] + mo.group(3), text
    )


TEST_STRING = """
* https://www.instagram.com/taylorswift/p/DXrxObojod9/?hl=en - Taylor Swift;
* https://instagram.com/reel/CsfO_chhPEe/ - Kuru Cosplay;
* https://instagram.com/p/DBg0L6foRNW/ - Pale Waves;
* https://x.com/IceFrog/status/1718834746300719265 - IceFrog;
* https://open.spotify.com/track/42VUCXerQ5qTr4Qp6PhKo4 - Sabrina Carpenter;
* https://www.twitch.tv/irene_adler__/clip/SincereCuteOtterBudBlast-tFLu0wQZE6WgrlvD - E33 clip;
* https://clips.twitch.tv/SincereCuteOtterBudBlast-tFLu0wQZE6WgrlvD - E33 clip;
"""

# Copy-paste for alpha.py
"""
from ext.mimics.embed_fixer import TEST_STRING, find_all_links_to_fix, subn_links_to_fix

result = x = find_all_links_to_fix(TEST_STRING)
print(result)

result = x = subn_links_to_fix(TEST_STRING)
print(result[0])
print(result[1])
"""


async def get_metadata_embed_links(message: discord.Message) -> None:
    """Get links from website metadata embeds and make them clickable by sending extra embed with links.

    Unfortunately `certified discord tm moment` where
    it does not allow links to be clickable in website metadata embeds
    thus we have to extract them ourselves after it's compiled on discord side.
    """
    # wait till website meta embed actually renders
    await asyncio.sleep(2.7)

    links: list[str] = []
    color = discord.Color.pink()
    for embed in message.embeds:
        links += re.findall(const.Regex.URL, str(embed.description))
        color = embed.color

    if not links:
        return

    embed = discord.Embed(color=color, description="\n".join(links)).set_author(
        name="links in the embed above in a clickable format:"
    )
    await message.channel.send(embed=embed)


class FixSocialLinks(AluCog):
    """Fix Social Links."""

    def __init__(self, *args: Any, **kwargs: Any) -> None:
        super().__init__(*args, **kwargs)
        self.fix_links = app_commands.ContextMenu(
            name="Fix Social Links",
            callback=self.context_menu_fix_links,
        )

    @override
    async def cog_load(self) -> None:
        self.bot.tree.add_command(self.fix_links)

    @override
    async def cog_unload(self) -> None:
        c = self.fix_links
        self.bot.tree.remove_command(c.name, type=c.type)

    def slash_context_menu_embed_fixer_helper(self, text: str) -> str:
        """Helper function to fix embed.

        This function is for slash commands and context menu.
        """
        res = find_all_links_to_fix(text)
        if not res:
            joined = ";\n".join(f"* {site}" for site in SUPPORTED_SITES_DISPLAY_NAMES)
            msg = f'This message does not have any social links to "fix".\n\nCurrently supported:\n{joined}'
            raise commands.BadArgument(msg)
        return res

    async def context_menu_fix_links(self, interaction: AluInteraction, message: discord.Message) -> None:
        """Get better social links from a message."""
        await interaction.response.send_message(self.slash_context_menu_embed_fixer_helper(message.content))

    @app_commands.command(name="fix-links")
    async def slash_fix_links(self, interaction: AluInteraction, link: str) -> None:
        """\N{PICK} Enter Social link(-s) to "fix" with a better embed than original.

        Parameters
        ----------
        link: str
            Supported: Twitter, Reddit, Instagram, TikTok, DeviantArt, Tumblr, Pixiv, Bsky, Twitch Clips, Spotify.
        """
        await interaction.response.send_message(self.slash_context_menu_embed_fixer_helper(link))

    @commands.Cog.listener("on_message")
    async def community_fix_links(self, message: discord.Message) -> None:
        """(#Community Only!) Immediately fix messages with "wrong" social links with "better" ones.

        Currently only enabled in the community and hideout servers.
        """
        if not message.guild or message.guild.id not in const.MY_GUILDS or message.channel.id == const.Channel.jailed_bots:
            # Don't allow outside of community/hideout servers.
            # Don't allow in #jailed_bots as this is where I test other embed fix bots.
            return
        if message.author.bot:
            return

        fixed_message = subn_links_to_fix(message.content)
        if fixed_message[1] == 0:
            # Message doesn't have any links to fix
            return

        mirror = mimics.Mirror.from_message(bot=self.bot, message=message)
        msg = await mirror.send(message.author, content=fixed_message[0])
        await message.delete()
        await get_metadata_embed_links(msg)

    @commands.command()
    async def test_fix_links_examples(self, ctx: AluContext) -> None:
        """Test Fix Link Examples.

        Contains random links that are supposed to be fixed by this cog if they were to be sent by a human."""
        await ctx.send(TEST_STRING, suppress_embeds=True)
        await ctx.send(subn_links_to_fix(TEST_STRING)[0])


async def setup(bot: AluBot) -> None:
    """Load AluBot extension. Framework of discord.py."""
    await bot.add_cog(FixSocialLinks(bot))
