from __future__ import annotations

from typing import TYPE_CHECKING, Any, NamedTuple, Optional, Type

import discord
from discord.ext import commands

if TYPE_CHECKING:
    from bot import AluBot

__all__ = (
    "AluCog",
    "ExtCategory",
    "EXT_CATEGORY_NONE",
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
        category: ExtCategory

    def __init_subclass__(
        cls: Type[AluCog],
        emote: Optional[str] = None,
        category: Optional[ExtCategory] = None,
        **kwargs: Any,
    ) -> None:
        cls.emote = discord.PartialEmoji.from_str(emote) if emote else None
        parent_category: Optional[ExtCategory] = getattr(cls, "category", None)
        if isinstance(parent_category, ExtCategory):
            cls.category = category or parent_category or EXT_CATEGORY_NONE
        elif parent_category is None:
            cls.category = category or EXT_CATEGORY_NONE
        else:
            raise TypeError("`parent_category` is not of ExtCategory class when subclassing AluCog.")
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

    # @property
    # def pool(self):
    #     return self.bot.pool


class ExtCategory(NamedTuple):
    name: str
    emote: str
    description: str
    sort_back: bool = False


EXT_CATEGORY_NONE = ExtCategory(
    name="No category",
    emote="\N{THINKING FACE}",
    description="These commands belong nowhere, prob dev fault",
)
