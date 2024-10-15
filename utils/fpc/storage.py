from __future__ import annotations

import abc
import asyncio
import logging
import random
import time
from dataclasses import dataclass
from typing import TYPE_CHECKING, Generic, TypeVar, override

import discord
from discord import app_commands

from bot import aluloop

from .. import fuzzy

if TYPE_CHECKING:
    from bot import AluBot

__all__ = (
    "GameDataStorage",
    "Character",
    "CharacterStorage",
    "CharacterTransformer",
)

log = logging.getLogger(__name__)
log.setLevel(logging.INFO)

VT = TypeVar("VT")


@dataclass
class Character:
    id: int
    display_name: str
    """A display name for the character, i.e. `"Dark Willow"`"""
    emote: str

    @override
    def __repr__(self) -> str:
        return f"<{self.__class__.__name__} {self.display_name} id={self.id}>"


CharacterT = TypeVar("CharacterT", bound=Character)


class CharacterTransformer(app_commands.Transformer, abc.ABC, Generic[CharacterT]):
    @property
    @override
    def type(self) -> discord.AppCommandOptionType:
        return discord.AppCommandOptionType.number

    @abc.abstractmethod
    def get_character_storage(self, interaction: discord.Interaction[AluBot]) -> CharacterStorage[CharacterT]:
        ...

    @override
    async def transform(self, interaction: discord.Interaction[AluBot], hero_id: int) -> CharacterT:
        storage = self.get_character_storage(interaction)
        character = await storage.by_id(hero_id)
        return character

    @override
    async def autocomplete(
        self, interaction: discord.Interaction[AluBot], current: str
    ) -> list[app_commands.Choice[int]]:
        storage = self.get_character_storage(interaction)
        characters = await storage.all()

        options = fuzzy.finder(current, characters, key=lambda x: x.display_name)
        if not options:
            characters.sort(key=lambda x: x.display_name)
            options = characters[:5]
        else:
            options = options[:5]

        return [app_commands.Choice(name=character.display_name, value=character.id) for character in options]


class GameDataStorage(Generic[VT]):
    if TYPE_CHECKING:
        cached_data: dict[int, VT]

    def __init__(self, bot: AluBot) -> None:
        """_summary_

        Parameters
        ----------
        bot
            need it just so @aluloop task can use `exc_manager` to send an error notification.
        """
        self.bot: AluBot = bot
        self.lock: asyncio.Lock = asyncio.Lock()

    def start(self) -> None:
        # self.update_data.add_exception_type(errors.ResponseNotOK)
        # random times just so we don't have a possibility of all cache being updated at the same time
        self.update_data.change_interval(hours=24, minutes=random.randint(1, 59))
        self.update_data.start()

    def close(self) -> None:
        """Closes the keys cache."""
        self.update_data.cancel()

    async def fill_data(self) -> dict[int, VT]:
        ...

    @aluloop()
    async def update_data(self) -> None:
        async with self.lock:
            start_time = time.perf_counter()
            self.cached_data = await self.fill_data()
            log.info("Cache %s is updated in %.3fs", self.__class__.__name__, time.perf_counter() - start_time)

    async def get_cached_data(self) -> dict[int, VT]:
        """Get the whole cached data."""
        try:
            return self.cached_data
        except AttributeError:
            await self.update_data()
            return self.cached_data

    async def get_value(self, id: int) -> VT:
        try:
            return self.cached_data[id]
        except (KeyError, AttributeError):
            await self.update_data()
            return self.cached_data[id]


class CharacterStorage(abc.ABC, GameDataStorage[CharacterT]):
    @abc.abstractmethod
    async def by_id(self, character_id: int) -> CharacterT:
        ...

    @abc.abstractmethod
    async def all(self) -> list[CharacterT]:
        ...
