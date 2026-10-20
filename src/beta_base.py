"""Contains base class for BetaCog for `ext.beta.py`.

In `ext.beta.py` I quickly beta-test some things.

It might be a bit silly, but the purpose of the current file is to minimize amount of imports and lines of code
for anything we're going to do in `ext.beta.py`. The performance cost of extra imports is probably
negligible compared to annoyance of typing them manually out every time we need them.

For an example of how starting template for `ext.beta.py` looks - you can look in the `templates` folder.

Notices
-------
* MPL-2.0 License, see LICENSE file for more details.
* Copyright (C) 2020-present @Aluerie.
"""

# ruff: file-ignore[unused-import]

from __future__ import annotations

import abc
import asyncio
import datetime
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
from core import AluBot, AluCog
from shared.concepts import loop
from utils import cache, const, errors, fmt, fuzzy, timezones
from utils.helpers import measure_time

if TYPE_CHECKING:
    from collections.abc import Callable, Coroutine, Sequence

    from core import AluContext, AluInteraction


log = logging.getLogger(__name__)


class BetaCog(AluCog):
    """Base Class for BetaTest cog."""

    @override
    async def cog_load(self) -> None:
        self.beta_test.start()

    @loop(count=1)
    async def beta_test(self) -> None:
        """Task that is supposed to run just once to test stuff out."""
        await self.beta_test_task_count_1()

    async def beta_test_task_count_1(self) -> None:
        """Worker function for `self.beta_test` task."""
        raise NotImplementedError
