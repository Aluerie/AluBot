"""
The files in this folder are made for easier resetting of git-ignored `exts/beta.py` file 
where I do various beta testings in the test version of the bot.
"""
from __future__ import annotations

import asyncio
import datetime
import logging
import os
from typing import TYPE_CHECKING, Annotated, Any, Callable, Coroutine, Optional, Sequence, TypeVar, Union

import discord
from discord import app_commands
from discord.ext import commands, menus

from utils import AluCog, ExtCategory, aluloop, const, errors

log = logging.getLogger(__name__)

if TYPE_CHECKING:
    from utils import AluBot, AluContext

category = ExtCategory(
    name='Beta Features',
    emote=const.Emote.bedWTF,
    description='Beta Features',
)


class BetaCog(AluCog, category=category):
    async def cog_load(self):
        self.beta_task.start()

    @property
    def spam(self) -> discord.TextChannel:
        """Even lazier shortcut"""
        return self.hideout.spam

    async def beta_task(self):
        ...
