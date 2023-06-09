from __future__ import annotations

import logging
import re
from typing import TYPE_CHECKING

import discord
from discord import app_commands
from discord.ext import commands

from utils import AluCog

if TYPE_CHECKING:
    from utils import AluContext

log = logging.getLogger(__name__)
log.setLevel(logging.INFO)  # .DEBUG)


class LinkUtilities(AluCog):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fix_link_ctx_menu = app_commands.ContextMenu(
            name='Fix Twitter/Insta link', callback=self.fix_link_ctx_menu_callback
        )

    def cog_load(self) -> None:
        self.bot.tree.add_command(self.fix_link_ctx_menu)

    async def cog_unload(self) -> None:
        self.bot.tree.remove_command(self.fix_link_ctx_menu.name, type=self.fix_link_ctx_menu.type)

    def fix_link_worker(self, message_content: str) -> str:
        """Fix embeds for twitter/instagram/more to come with better embeds."""

        def url_regex(x: str) -> str:
            return fr"http[s]?://(?:www\.)?{x}(?:[a-zA-Z]|[0-9]|[$-_@.&+]|[!*(),]|(?:%[0-9a-fA-F][0-9a-fA-F]))+"

        fix_dict = {
            # social network: better embed site,
            'twitter.com': 'fxtwitter.com',
            'instagram.com': 'ddinstagram.com',
        }
        answer_urls = []
        for site, fix_site in fix_dict.items():
            r_site = site.replace('.', r'\.')  # dot in regex needs to be slashed
            urls = re.findall(url_regex(r_site), message_content)
            answer_urls += [re.sub(site, fix_site, u) for u in urls]

        log.debug(answer_urls)
        if not len(answer_urls):
            # TODO: BETTER ERROR GOD DAMN IT
            raise commands.BadArgument('This message does not have any twitter/instagram links to "fix".')
        return '\n'.join(answer_urls)

    async def fix_link_ctx_menu_callback(self, ntr: discord.Interaction, message: discord.Message):
        content = self.fix_link_worker(message.content)
        await ntr.response.send_message(content)

    @commands.hybrid_command()
    @app_commands.describe(link="Enter Twitter/Instagram link to \"fix\"")
    async def fix_links(self, ctx: AluContext, *, link: str):
        """Fix twitter/instagram links with better embeds."""
        content = self.fix_link_worker(link)
        await ctx.reply(content)
