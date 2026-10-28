# Copyright (C) 2020-present, Irene Adler ❤ (@Aluerie).
# Licensed under MPL-2.0, see the LICENSE file for details.
"""Contains base class for BetaCog for `ext.beta.py`.

In `ext.beta.py` I quickly beta-test some things.

It might be a bit silly, but the purpose of the current file is to minimize amount of imports and lines of code
for anything we're going to do in `ext.beta.py`. The performance cost of extra imports is probably
negligible compared to annoyance of typing them manually out every time we need them.

For an example of how starting template for `ext.beta.py` looks - you can look in the `templates` folder.
"""

# ruff: file-ignore[unused-import, typing-only-third-party-import]

from __future__ import annotations

import abc
import asyncio
import datetime as dt
import enum
import logging
import os
import pprint
import random
import sys
from dataclasses import dataclass
from typing import (
    TYPE_CHECKING,
    Annotated,
    Any,
    ClassVar,
    Literal,
    NamedTuple,
    Self,
    TypedDict,
    TypeVar,
    Unpack,
    cast,
    override,
    reveal_type,
)

import asyncpg
import discord
from discord import app_commands
from discord.ext import commands

from config import env
from core import Bot, Cog
from shared.concepts import loop
from utils import const

if TYPE_CHECKING:
    from collections.abc import Callable, Coroutine, Sequence

    from core import Context, Interaction


log = logging.getLogger(__name__)


class BetaCog(Cog):
    """Base Class for BetaTest cog."""

    @override
    async def cog_load(self) -> None:
        self.beta_task.start()

    @loop(count=1)
    async def beta_task(self) -> None:
        """Task that is supposed to run just once to test stuff out."""
        await self.task_test()

    async def task_test(self) -> None:
        """Worker function for `self.beta_test` task."""
        raise NotImplementedError

    @commands.Cog.listener("on_message")
    async def beta_event(self, message: discord.Message) -> None:
        """Event made for quick testing."""
        if message.guild is None:
            return
        if message.guild.id != const.Guild.hideout:
            return
        if message.author.bot or message.webhook_id:
            return
        if not message.content.lower().startswith("test"):
            return

        await self.event_test(message)

    async def event_test(self, message: discord.Message) -> None:
        """Worker function for `self.beta_event` event."""
        raise NotImplementedError
