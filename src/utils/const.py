"""Const.

Notices
-------
* MPL-2.0 License, see LICENSE file for more details.
* Copyright (C) 2020-present @Aluerie.
"""

from enum import Enum, IntEnum, auto
from typing import TYPE_CHECKING, override

if TYPE_CHECKING:
    from core import AluBot


class Guild(IntEnum):
    """Discord guild ids."""

    community = 702561315478044804
    hideout = 759916212842659850


_RESOLVED_EMOTES: dict[str, str] = {}


class Emoji(Enum):
    """Application Emojis.

    Names must match the names in both bots' (production and test version) Developer Portals.
    """

    Discord = auto()
    GitHub = auto()

    @override
    def __str__(self) -> str:
        try:
            return _RESOLVED_EMOTES[self.name]
        except KeyError:
            msg = f"Emojis not loaded yet (tried accessing {self.name!r} before load_emojis)"
            raise RuntimeError(msg) from None


async def load_emojis(bot: AluBot) -> None:
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
