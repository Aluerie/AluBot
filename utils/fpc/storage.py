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

from .. import const, fuzzy

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
PseudoVT = TypeVar("PseudoVT")


@dataclass
class Character:
    id: int
    display_name: str
    """A display name for the character, i.e. `"Dark Willow"`.

    This will include all the spaces, unusual symbols and everything.
    """
    emote: str

    @override
    def __repr__(self) -> str:
        return f"<{self.__class__.__name__} id={self.id} {self.display_name}>"


CharacterT = TypeVar("CharacterT", bound=Character)
PseudoCharacterT = TypeVar("PseudoCharacterT", bound=Character)


class CharacterTransformer(app_commands.Transformer, abc.ABC, Generic[CharacterT, PseudoCharacterT]):
    @property
    @override
    def type(self) -> discord.AppCommandOptionType:
        return discord.AppCommandOptionType.number

    @abc.abstractmethod
    def get_character_storage(
        self, interaction: discord.Interaction[AluBot]
    ) -> CharacterStorage[CharacterT, PseudoCharacterT]:
        ...

    @override
    async def transform(self, interaction: discord.Interaction[AluBot], hero_id: int) -> CharacterT | PseudoCharacterT:
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


class GameDataStorage(abc.ABC, Generic[VT, PseudoVT]):
    """Game Data Storage.

    Used for fetching and storing data from public API and JSONs.
    The concept is the data gets updated/refreshed once a day.

    if KeyError arises - there is an attempt to refresh the data, otherwise it's assumed that the data is fine enough
    (yes, it can backfire with an update where, for example, some item icon changes,
    but we still update storage once per day, so whatever).
    """

    if TYPE_CHECKING:
        cached_data: dict[int, VT]

    def __init__(self, bot: AluBot) -> None:
        """__init__.

        Parameters
        ----------
        bot
            need it just so @aluloop task can use `exc_manager` to send an error notification.
        """
        self.bot: AluBot = bot
        self.lock: asyncio.Lock = asyncio.Lock()

    def start(self) -> None:
        """Start the storage tasks."""
        # self.update_data.add_exception_type(errors.ResponseNotOK)
        # random times just so we don't have a possibility of all cache being updated at the same time
        self.update_data.change_interval(hours=24, minutes=random.randint(1, 59))
        self.update_data.start()

    def close(self) -> None:
        """Cancel the storage tasks."""
        self.update_data.cancel()

    async def fill_data(self) -> dict[int, VT]:
        """Fill self.cached_data with the data from various json data.

        This function is supposed to be implemented by subclasses.
        We get the data and sort it out into a convenient dictionary to cache.
        """
        ...

    @aluloop()
    async def update_data(self) -> None:
        """The task responsible for keeping the data up-to-date."""
        log.debug("Updating Cache %s.", self.__class__.__name__)
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
        """Get value by the `key` from `self.cached_data`."""
        try:
            return self.cached_data[id]
        except (KeyError, AttributeError):
            # let's try to update the cache in case it's a KeyError due to
            # * new patch or something
            # * the data is not initialized then we will get stuck in self.lock waiting for the data.
            await self.update_data()
            return self.cached_data[id]

    async def send_unknown_value_report(self, id: int) -> None:
        embed = discord.Embed(
            color=const.Colour.maroon,
            title=f"Unknown {self.__class__.__name__} appeared!",
            description=f"```py\nid={id}\n```",
        ).set_footer(text=f"Package: {__package__}")
        await self.bot.spam.send(embed=embed)

    @staticmethod
    @abc.abstractmethod
    def generate_unknown_object(id: int) -> PseudoVT:
        ...

    async def by_id(self, id: int) -> VT | PseudoVT:
        """Get storage object by its ID"""
        try:
            storage_object = await self.get_value(id)
        except KeyError:
            unknown_object = self.generate_unknown_object(id)
            return unknown_object
        else:
            return storage_object

    async def all(self) -> list[VT | PseudoVT]:
        data = await self.get_cached_data()
        return list(data.values())


class CharacterStorage(GameDataStorage[CharacterT, PseudoCharacterT]):
    ...
