"""BASE IMPORT FILE FOR BETA.PY SANDBOX TESTING.

The files in this folder are made for easier resetting of git-ignored `ext/beta.py` file
where I do various beta testings in the test version of the bot.
"""

# pyright: reportUnusedImport=false

from __future__ import annotations

import logging
from typing import (
    override,
)

import discord  # noqa TCH002

from bot import AluCog, ExtCategory, aluloop
from utils import const

log = logging.getLogger(__name__)


category = ExtCategory(
    name="Beta Features",
    emote=const.Emote.bedWTF,
    description="Beta Features",
)


class BetaCog(AluCog, category=category):
    """Base Class for BetaTest cog."""

    @override
    async def cog_load(self) -> None:
        self.beta_task.clear_exception_types()
        self.beta_task.start()

    @property
    def spam(self) -> discord.TextChannel:
        """Even lazier shortcut."""
        return self.hideout.spam

    @aluloop()
    async def beta_task(self) -> None:
        """Task that is supposed to run just once to test stuff out."""
