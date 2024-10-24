from __future__ import annotations

import logging
from typing import TYPE_CHECKING, Any, override

import discord
from discord import app_commands
from discord.ext import commands

from bot import AluCog
from utils import links

if TYPE_CHECKING:
    from bot import AluBot

log = logging.getLogger(__name__)
log.setLevel(logging.INFO)  # .DEBUG)


class LinkUtilities(AluCog):
    def __init__(self, *args: Any, **kwargs: Any) -> None:
        super().__init__(*args, **kwargs)
        self.fix_link_ctx_menu = app_commands.ContextMenu(
            name="Fix Twitter/Insta/TikTok links",
            callback=self.fix_link_ctx_menu_callback,
        )

    @override
    async def cog_load(self) -> None:
        self.bot.tree.add_command(self.fix_link_ctx_menu)

    @override
    async def cog_unload(self) -> None:
        c = self.fix_link_ctx_menu
        self.bot.tree.remove_command(c.name, type=c.type)

    def fix_link_worker(self, text_to_fix: str) -> str:
        res = links.fix_social_links(text_to_fix, omit_rest=True)
        if res is None:
            msg = (
                'This message does not have any social links to "fix".\n\n'
                "Currently supported:\n"
                "* Twitter;\n"
                "* Instagram;\n"
                "* TikTok."
            )
            raise commands.BadArgument(msg)
        return res

    async def fix_link_ctx_menu_callback(self, interaction: discord.Interaction, message: discord.Message) -> None:
        content = self.fix_link_worker(message.content)
        await interaction.response.send_message(content)

    @app_commands.command()
    async def fix_links(self, interaction: discord.Interaction[AluBot], link: str) -> None:
        """Enter Twitter/Instagram/TikTok link(-s) to "fix"."""
        content = self.fix_link_worker(link)
        await interaction.response.send_message(content)
