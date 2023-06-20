from __future__ import annotations

from typing import TYPE_CHECKING, Any, Optional, Type

import discord
from discord.ext import commands

if TYPE_CHECKING:
    from bot import AluBot

__all__ = (
    'AluCog',
    'ExtCategory',
)


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

    def __init__(self, bot: AluBot, category: Optional[ExtCategory] = None, *args: Any, **kwargs: Any) -> None:
        self.bot: AluBot = bot
        self.category:  Optional[ExtCategory] = category

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


class ExtCategory:
    """Extension Category

    This class is made purely for $help command purposes.

    emote - to go to Select menu.
    name - to go as category choice in Select menu.
    description - to go as description in Select menu.
    help_embed - to go as front page embed for the said category.
    """

    if TYPE_CHECKING:
        name: str
        emote: Optional[discord.PartialEmoji]

    def __init_subclass__(cls: Type[ExtCategory], name: str, emote: str) -> None:
        cls.name = name
        cls.emote = discord.PartialEmoji.from_str(emote) if emote else None

    @property
    def help_embed(self) -> discord.Embed:
        raise NotImplemented
