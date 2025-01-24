"""BASE IMPORT FILE FOR BETA.PY SANDBOX TESTING.

The files in this folder are made for easier resetting of git-ignored `ext/beta.py` file
where I do various beta testings in the test version of the bot.
"""

# pyright: reportUnusedImport=false

from __future__ import annotations

import asyncio
import datetime
import enum
import logging
import os
import random
import sys
from dataclasses import dataclass
from typing import (
    TYPE_CHECKING,
    Annotated,
    Any,
    ClassVar,
    Literal,
    TypedDict,
    TypeVar,
    Unpack,
    cast,
    override,
    reveal_type,
)

import asyncpg
import discord  # noqa: TC002
from discord import app_commands
from discord.ext import commands, menus
from tabulate import tabulate

import config
from bot import AluBot, AluCog, ExtCategory, aluloop
from utils import cache, const, errors, formats, fuzzy, timezones
from utils.helpers import measure_time

if TYPE_CHECKING:
    from collections.abc import Callable, Coroutine, Sequence


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
