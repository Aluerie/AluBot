"""
The files in this folder are made for easier resetting of git-ignored `extensions/beta.py` file 
where I do various beta testings in the test version of the bot.
"""
from __future__ import annotations

import asyncio
import datetime
import enum
import logging
import os
from typing import TYPE_CHECKING, Annotated, Any, Callable, Coroutine, Literal, Optional, Sequence, TypeVar, Union

import discord
from discord import app_commands
from discord.ext import commands, menus

from bot import AluBot
from utils import AluCog, AluContext, ExtCategory, aluloop, const, errors, timezones

log = logging.getLogger(__name__)

if TYPE_CHECKING:
    pass

category = ExtCategory(
    name="Beta Features",
    emote=const.Emote.bedWTF,
    description="Beta Features",
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
