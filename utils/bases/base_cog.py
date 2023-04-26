from __future__ import annotations

from typing import TYPE_CHECKING, Any, Optional, Type

import discord
from discord.ext import commands

if TYPE_CHECKING:
    from bot import AluBot

__all__ = ('AluCog',)


class AluCog(commands.Cog):
    """Base cog class for all AluBot cogs

    Attributes
    ----------
    bot: AluBot
        The bot instance.
    """

    if TYPE_CHECKING:
        emote: Optional[discord.PartialEmoji]

    def __init_subclass__(cls: Type[AluCog], **kwargs: Any) -> None:
        emote = kwargs.pop("emote", None)
        cls.emote = discord.PartialEmoji.from_str(emote) if emote else None
        return super().__init_subclass__(**kwargs)

    def __init__(self, bot: AluBot, *args: Any, **kwargs: Any) -> None:
        self.bot: AluBot = bot

        next_in_mro = next(iter(self.__class__.__mro__))
        if hasattr(next_in_mro, "__is_jishaku__") or isinstance(next_in_mro, self.__class__):
            kwargs["bot"] = bot

        super().__init__(*args, **kwargs)

    # shortcuts
    @property
    def community(self):
        return self.bot.community

    @property
    def hideout(self):
        return self.bot.hideout
