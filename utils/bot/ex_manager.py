"""
ex_manager.py - yes, it is for managing my exes.
"""

from __future__ import annotations

import asyncio
from typing import TYPE_CHECKING, Any, Dict, Generator, List, Optional, Tuple

import discord

if TYPE_CHECKING:
    from bot import AluBot


class AluExceptionManager:
    """A simple exception handler that sends all exceptions to a error
    Webhook and then logs them to the console.
    """

    # licensed MPL v2 from DuckBot-Discord/DuckBot
    # https://github.com/DuckBot-Discord/DuckBot/blob/rewrite/utils/errorhandler.py

    __slots__: Tuple[str, ...] = ()

    def __init__(self) -> None:
        pass
    

