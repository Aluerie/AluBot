# Copyright (C) 2020-present, Irene Adler ❤ (@Aluerie).
# Licensed under MPL-2.0, see the LICENSE file for details.
"""Const."""
# ruff: file-ignore[mixed-case-variable-in-class-scope]

from enum import Enum, IntEnum, auto
from typing import TYPE_CHECKING, ClassVar, Final, override

import discord

if TYPE_CHECKING:
    from core import Bot

__all__ = (
    "MY_GUILDS",
    "ChannelId",
    "Emoji",
    "Guild",
    "RoleId",
    "UserId",
    "load_emojis",
)

########################################################################################################################
# SPECIAL CONSTANTS
########################################################################################################################

NO_PINGS = discord.AllowedMentions.none()

########################################################################################################################
# GUILDS
########################################################################################################################


class Guild(IntEnum):
    """Discord guild ids."""

    community = 702561315478044804
    hideout = 759916212842659850


MY_GUILDS: Final = (Guild.community, Guild.hideout)
"""Guilds where the bot's private/community commands are registered."""


########################################################################################################################
# EMOJIS
########################################################################################################################


_RESOLVED_EMOTES: dict[str, str] = {}


class Emoji(Enum):
    """Application Emojis.

    Names must match the names in both bots' (production and test version) Developer Portals.
    """

    # Logos
    Discord = auto()
    GitHub = auto()

    # Bugtracker
    reopened = auto()
    opened = auto()
    commented = auto()
    closed = auto()
    assigned = auto()

    # Non-animated Dank Emojis
    bubuChrist = auto()
    bubuGun = auto()
    DankApprove = auto()
    DankHey = auto()
    DankLove = auto()
    hu = auto()
    peepoComfy = auto()
    peepoNiceDay = auto()
    peepoPolice = auto()
    peepoRoseDank = auto()
    PepoBeliever = auto()
    PepoDetective = auto()
    PepoG = auto()
    WeirdChamp = auto()

    # Animated
    SmogeInTheRain = auto()

    @override
    def __str__(self) -> str:
        try:
            return _RESOLVED_EMOTES[self.name]
        except KeyError:
            msg = f"Emojis not loaded yet (tried accessing {self.name!r} before load_emojis)"
            raise RuntimeError(msg) from None


async def load_emojis(bot: Bot) -> None:
    """Fetch the bot's Application Emojis and make them available to `Emoji` enum.

    Must be awaited once (e.g. in `setup_hook`) before any `Emoji` member is converted to a string, since the markdown
    strings depend on which bot account (test or production) is logged in.

    Parameters
    ----------
    bot
        The bot whose Application Emojis are fetched.

    Raises
    ------
    RuntimeError
        If any `Emoji` member has no Application Emoji of the same name on this bot.
    """
    _RESOLVED_EMOTES.update({e.name: str(e) for e in await bot.fetch_application_emojis()})
    if missing := {e.name for e in Emoji} - _RESOLVED_EMOTES.keys():
        msg = f"Application emojis missing on this bot: {sorted(missing)}"
        raise RuntimeError(msg)


########################################################################################################################
# MENTIONABLE IDS
########################################################################################################################


class DiscordId(int):
    """Base class for Discord snowflake IDs that behave like plain integers.

    Subclasses must set `_mention_template` and `_object_type`. Instances can be
    used anywhere an `int` is accepted, for example as dict keys or in comparisons.
    """

    __slots__ = ()

    _mention_template: ClassVar[str]
    _object_type: ClassVar[type[discord.abc.Snowflake]]

    @property
    def mention(self) -> str:
        """Mention string that Discord renders as a clickable reference."""
        return self._mention_template.format(self)

    @property
    def object(self) -> discord.Object:
        """Lightweight `discord.Object` for this ID, usable in API calls that accept a snowflake.

        A new object is created on every access.
        """
        return discord.Object(self, type=self._object_type)


class ChannelId(DiscordId):
    """ID of a Discord channel.

    The `mention` property renders as ``<#id>`` and `object` is typed as a guild channel.
    """

    __slots__ = ()

    _mention_template = "<#{}>"
    _object_type = discord.abc.GuildChannel  # ty: ignore[invalid-assignment]


class RoleId(DiscordId):
    """ID of a Discord role.

    The `mention` property renders as ``<@&id>`` and `object` is typed as a role.
    """

    __slots__ = ()

    _mention_template = "<@&{}>"
    _object_type = discord.Role


class UserId(DiscordId):
    """ID of a Discord user or guild member.

    The `mention` property renders as ``<@id>`` and `object` is typed as a user.
    """

    __slots__ = ()

    _mention_template = "<@{}>"
    _object_type = discord.abc.User
