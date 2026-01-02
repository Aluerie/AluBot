from __future__ import annotations

import asyncio
import logging
import re
from typing import TYPE_CHECKING, Any, override

import discord
from discord import app_commands
from discord.ext import commands

from bot import AluCog
from utils import const, mimics

if TYPE_CHECKING:
    from bot import AluBot, AluInteraction


__all__ = ("FixSocialLinks",)


log = logging.getLogger(__name__)
log.setLevel(logging.INFO)  # .DEBUG)

FIX_DICT: dict[str, str] = {
    # mapping: social network -> better embed site,
    # note the "slash" absence in the end and "https://" are important
    "x": "https://fxtwitter.com",
    "twitter": "https://fxtwitter.com",
    "reddit": "https://rxddit.com",
    "instagram": "https://kkinstagram.com",
    "tiktok": "https://tnktok.com",
    "deviantart": "https://fixdeviantart.com",
    "tumblr": "https://tpmblr.com",
    "pixiv": "https://phixiv.net",
    "bsky": "https://bskyx.app",
    "twitch": "https://fxtwitch.seria.moe/clip",
    "clips": "https://fxtwitch.seria.moe/clip",
}
# PS. as of November 2024, I finally found out that some other people made the same bot/feature for Discord:
# * https://betterdiscord.app/plugin/SocialMediaLinkConverter
# * https://github.com/seriaati/embed-fixer
# So, check it out, they might find something better.

COMPILED_REGEX = re.compile(
    r"""
        http[s]?
        ://
        (?:www\.)?
        (# group 1 - the actual site
        x\.com|
        twitter\.com|
        reddit\.com|
        instagram\.com|
        tiktok\.com|
        deviantart\.com|
        tumblr\.com|
        pixiv\.net|
        bsky\.app|
        twitch\.tv/(?:[a-zA-Z]|[0-9]|[_])+/clip | clips\.twitch\.tv
        )
        (/ (?: [a-zA-Z] | [0-9] | [$-_@.&+] | [!*(),] | (?:% [0-9a-fA-F][0-9a-fA-F]) )+ )  # group 2 - the rest of url
    """,
    flags=re.VERBOSE | re.IGNORECASE,  # X = VERBOSE, I = IGNORECASE
)


def fix_social_links(text: str, *, omit_rest: bool = False) -> str | None:
    """Fix common social links by replacing them with links that provide better meta-embeds for Discord UI.

    Parameters
    ----------
    text: str
        Text to search social links in.
    omit_rest: bool = False
        Whether the final result should only include "better" links and exclude the rest of the text.

    Returns
    -------
    str | None
        Either
        * `str` text with new social links if a link to replace was found or `None` in case nothing was found;
        * `None` in case no match was found.

    Examples
    --------
    ```py
    text = "https://www.instagram.com/p/DBg0L6foRNW/ bla bla bla https://x.com/IceFrog/status/1718834746300719265"
    fix_social_links(text)
    "https://ddinstagram.com/p/DBg0L6foRNW/ bla bla bla https://fxtwitter.com/IceFrog/status/1718834746300719265"
    ```

    Sources
    ------
    * https://stackoverflow.com/a/15175239/19217368
    """
    if found := COMPILED_REGEX.findall(text):
        if omit_rest:
            # found is list[tuple[str, ...]], where tuple has 2 strings (because we have 2 matching groups in regex)
            #  i.e. [('instagram.com', '/p/DBg0L6foRNW/'), ('x.com', '/IceFrog/status/1718834746300719265')]
            return "\n".join([f"{FIX_DICT[group[0].lower().split('.')[0]]}{group[1]}" for group in found])
        return COMPILED_REGEX.sub(lambda mo: rf"{FIX_DICT[mo.group(1).lower().split('.')[0]]}{mo.group(2)}", text)
    return None


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

    def fix_links_helper(self, text_to_fix: str) -> str:
        """Helper function to fix social links."""
        res = fix_social_links(text_to_fix, omit_rest=True)
        if res is None:
            supported_sites = (
                "Twitter",
                "Reddit",
                "Instagram",
                "TikTok",
                "DeviantArt",
                "Tumblr",
                "Pixiv",
                "Bsky",
                "Twitch Clips",
            )
            joined = ";\n".join(f"* {site}" for site in supported_sites)
            msg = f'This message does not have any social links to "fix".\n\nCurrently supported:\n{joined}'
            raise commands.BadArgument(msg)
        return res

    async def context_menu_fix_links(self, interaction: AluInteraction, message: discord.Message) -> None:
        """Get better social links from a message."""
        content = self.fix_links_helper(message.content)
        await interaction.response.send_message(content)

    @app_commands.command(name="fix-links")
    async def slash_fix_links(self, interaction: AluInteraction, link: str) -> None:
        """\N{PICK} Enter Social link(-s) to "fix" with a better embed than original.

        Parameters
        ----------
        link: str
            Supported: Twitter, Reddit, Instagram, TikTok, DeviantArt, Tumblr, Pixiv, Bsky, Twitch Clips, etc.
        """
        content = self.fix_links_helper(link)
        await interaction.response.send_message(content)

    @commands.Cog.listener("on_message")
    async def community_fix_links(self, message: discord.Message) -> None:
        """(#Community Only!) Immediately fix messages with "wrong" social links with "better" ones.

        Currently only enabled in the community server.
        """
        if not message.guild or message.guild.id not in const.MY_GUILDS:
            return
        if message.author.bot:
            return

        fixed_links = fix_social_links(message.content)
        if fixed_links is None:
            return

        mirror = mimics.Mirror.from_message(bot=self.bot, message=message)
        msg = await mirror.send(message.author, content=fixed_links)
        await message.delete()
        await get_metadata_embed_links(msg)


async def setup(bot: AluBot) -> None:
    """Load AluBot extension. Framework of discord.py."""
    await bot.add_cog(FixSocialLinks(bot))


"""
# TESTING

text1 = (
    "https://www.instagram.com/p/DBg0L6foRNW/ bla bla bla bla bla bla bla "
    "https://x.com/IceFrog/status/1718834746300719265"
)

text2 = (
    "* https://clips.twitch.tv/CrispyAwkwardDragonEleGiggle-DUpiKHTVlyX-EgGp\n"
    "* https://twitch.tv/dinossindgeil/clip/CrispyAwkwardDragonEleGiggle-DUpiKHTVlyX-EgGp"
)

result = fix_social_links(text2)
print(result)  # noqa: T201
"""
