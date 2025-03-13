from __future__ import annotations

import abc
import asyncio
import logging
import random
import time
from dataclasses import dataclass
from typing import TYPE_CHECKING, TypeVar, override

import discord
from discord import app_commands

from bot import aluloop
from utils import const, errors, fuzzy

if TYPE_CHECKING:
    from bot import AluBot, AluInteraction

__all__ = (
    "Character",
    "CharacterStorage",
    "CharacterTransformer",
    "GameDataStorage",
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


class CharacterTransformer[CharacterT: Character, PseudoCharacterT: Character](app_commands.Transformer, abc.ABC):
    @property
    @override
    def type(self) -> discord.AppCommandOptionType:
        return discord.AppCommandOptionType.number

    @abc.abstractmethod
    def get_character_storage(self, interaction: AluInteraction) -> CharacterStorage[CharacterT, PseudoCharacterT]: ...

    @override
    async def transform(self, interaction: AluInteraction, hero_id: int) -> CharacterT | PseudoCharacterT:
        storage = self.get_character_storage(interaction)
        return await storage.by_id(hero_id)

    @override
    async def autocomplete(self, interaction: AluInteraction, current: str) -> list[app_commands.Choice[int]]:
        storage = self.get_character_storage(interaction)
        characters = await storage.all()

        options = fuzzy.finder(current, characters, key=lambda x: x.display_name)
        if not options:
            characters.sort(key=lambda x: x.display_name)
            options = characters[:5]
        else:
            options = options[:5]

        return [app_commands.Choice(name=character.display_name, value=character.id) for character in options]


class GameDataStorage[VT, PseudoVT](abc.ABC):
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

    @abc.abstractmethod
    async def fill_data(self) -> dict[int, VT]:
        """Fill self.cached_data with the data from various json data.

        This function is supposed to be implemented by subclasses.
        We get the data and sort it out into a convenient dictionary to cache.
        """

    @aluloop()
    async def update_data(self) -> None:
        """The task responsible for keeping the data up-to-date."""
        log.debug("Updating Storage %s.", self.__class__.__name__)
        async with self.lock:
            start_time = time.perf_counter()
            self.cached_data = await self.fill_data()
            log.debug(
                "Storage %s %s is updated in %.3fs",
                __package__.split(".")[-1].capitalize() if __package__ else "",
                self.__class__.__name__,
                time.perf_counter() - start_time,
            )

    async def get_cached_data(self) -> dict[int, VT]:
        """Get the whole cached data."""
        try:
            return self.cached_data
        except AttributeError:
            await self.update_data()
            return self.cached_data

    async def get_value(self, object_id: int) -> VT:
        """Get value by the `key` from `self.cached_data`."""
        try:
            return self.cached_data[object_id]
        except (KeyError, AttributeError):
            # let's try to update the cache in case it's a KeyError due to
            # * new patch or something
            # * the data is not initialized then we will get stuck in self.lock waiting for the data.
            await self.update_data()
            return self.cached_data[object_id]

    async def send_unknown_value_report(self, object_id: int) -> None:
        embed = discord.Embed(
            color=const.Color.error,
            title=f"Unknown {self.__class__.__name__} appeared!",
            description=f"```py\nid={object_id}\n```",
        ).set_footer(text=f"Package: {__package__}")
        await self.bot.spam_webhook.send(embed=embed)

    @staticmethod
    @abc.abstractmethod
    def generate_unknown_object(object_id: int) -> PseudoVT: ...

    async def by_id(self, object_id: int) -> VT | PseudoVT:
        """Get storage object by its ID."""
        try:
            return await self.get_value(object_id)
        except KeyError:
            return self.generate_unknown_object(object_id)

    async def all(self) -> list[VT | PseudoVT]:
        data = await self.get_cached_data()
        return list(data.values())


class CharacterStorage(GameDataStorage[CharacterT, PseudoCharacterT]):
    async def create_character_emote_helper(
        self,
        *,
        character_id: int,
        table: str,
        emote_name: str,
        emote_source_url: str,
        guild_id: int,
    ) -> str:
        """Helper function to create a new discord emote for a game character and remember it in the database."""
        guild = self.bot.get_guild(guild_id)
        if guild is None:
            msg = f"Guild id={guild_id} is `None`."
            raise errors.SomethingWentWrong(msg)

        existing_emote = discord.utils.find(lambda e: e.name == emote_name, guild.emojis)
        if existing_emote:
            query = f"INSERT INTO {table} (id, emote) VALUES ($1, $2)"
            await self.bot.pool.execute(query, character_id, str(existing_emote))
            return str(existing_emote)

        new_emote = await guild.create_custom_emoji(
            name=emote_name,
            image=await self.bot.transposer.url_to_bytes(emote_source_url),
        )

        # str(emote) is full emote representation, i.e. "<:AntiMage:1202019770787176529>"
        query = f"INSERT INTO {table} (id, emote) VALUES ($1, $2)"
        await self.bot.pool.execute(query, character_id, str(new_emote))

        embed = (
            discord.Embed(
                color=const.Color.prpl,
                title=f"New emote was added to `{table}` table.",
                description=f'```py\n{new_emote.name} = "{new_emote}"```',
            )
            .set_thumbnail(url=emote_source_url)
            .add_field(name="Emote", value=str(new_emote))
            .add_field(name="ID", value=str(character_id))
        )
        await self.bot.hideout.global_logs.send(embed=embed)
        return str(new_emote)
