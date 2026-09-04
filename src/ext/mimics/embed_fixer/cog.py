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

from .fixer import SUPPORTED_SITES_DISPLAY_NAMES, TEST_STRING, find_all_links_to_fix, subn_links_to_fix

if TYPE_CHECKING:
    from bot import AluBot, AluInteraction


__all__ = ("FixSocialLinks",)


log = logging.getLogger(__name__)
log.setLevel(logging.INFO)  # .DEBUG)


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


async def setup(bot: AluBot) -> None:
    """Load AluBot extension. Framework of discord.py."""
    await bot.add_cog(FixSocialLinks(bot))
