from __future__ import annotations

import logging
import re
from typing import TYPE_CHECKING, Optional

import discord
from discord import app_commands
from discord.ext import commands

from utils import AluCog

if TYPE_CHECKING:
    from utils import AluContext

log = logging.getLogger(__name__)
log.setLevel(logging.INFO)  # .DEBUG)


def fix_link_worker(text_to_fix: str, omit_rest: bool = False) -> Optional[str]:
    """Fix embeds for twitter/instagram/more to come with better embeds."""

    def url_regex(x: str) -> str:
        return rf"http[s]?://(?:www\.)?{x}(?:[a-zA-Z]|[0-9]|[$-_@.&+]|[!*(),]|(?:%[0-9a-fA-F][0-9a-fA-F]))+"

    fix_dict = {
        # social network: better embed site,
        "x.com": "fxtwitter.com",
        "twitter.com": "fxtwitter.com",
        "instagram.com": "ddinstagram.com",
    }

    wrong_urls, fixed_urls = [], []
    for site, fixed_site in fix_dict.items():
        r_site = site.replace(".", r"\.")  # dot in regex needs to be slashed
        urls = re.findall(url_regex(r_site), text_to_fix)
        wrong_urls.extend(urls)
        fixed_urls += [u.replace(site, fixed_site) for u in urls]

    if not fixed_urls:
        return None
    elif omit_rest:
        return "\n".join(fixed_urls)
    else:
        answer = text_to_fix
        for u, f in zip(wrong_urls, fixed_urls):
            answer = answer.replace(u, f)
        return answer


class LinkUtilities(AluCog):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fix_link_ctx_menu = app_commands.ContextMenu(
            name="Fix Twitter/Insta link", callback=self.fix_link_ctx_menu_callback
        )

    async def cog_load(self) -> None:
        self.bot.tree.add_command(self.fix_link_ctx_menu)

    async def cog_unload(self) -> None:
        self.bot.tree.remove_command(self.fix_link_ctx_menu.name, type=self.fix_link_ctx_menu.type)

    def cog_fix_link_worker(self, text_to_fix: str) -> str:
        res = fix_link_worker(text_to_fix, omit_rest=True)
        if res is None:
            raise commands.BadArgument('This message does not have any twitter/instagram links to "fix".')
        return res

    async def fix_link_ctx_menu_callback(self, interaction: discord.Interaction, message: discord.Message):
        content = self.cog_fix_link_worker(message.content)
        await interaction.response.send_message(content)

    @commands.hybrid_command()
    @app_commands.describe(link='Enter Twitter/Instagram link to "fix"')
    async def fix_links(self, ctx: AluContext, *, link: str):
        """Fix twitter/instagram links with better embeds."""
        content = self.cog_fix_link_worker(link)
        await ctx.reply(content)
