from __future__ import annotations

from typing import TYPE_CHECKING, Any

import discord
from discord.ext import commands

if TYPE_CHECKING:
    from utils import const

    from .. import AluBot

__all__ = ("AluCog",)


class AluCog(commands.Cog):
    """Base cog class for all AluBot cogs.

    Attributes
    ----------
    bot: AluBot
        The bot instance.

    """

    if TYPE_CHECKING:
        emote: discord.PartialEmoji | None
        brief: str | None
        hidden: bool

    def __init_subclass__(
        cls: type[AluCog],
        *,
        emote: str | None = None,
        brief: str | None = None,
        hidden: bool = False,
        **kwargs: Any,
    ) -> None:
        cls.emote = discord.PartialEmoji.from_str(emote) if emote else None
        cls.brief = brief
        cls.hidden = hidden
        return super().__init_subclass__(**kwargs)

    def __init__(self, bot: AluBot, *args: Any, **kwargs: Any) -> None:
        self.bot: AluBot = bot

        next_in_mro = next(iter(self.__class__.__mro__))
        if hasattr(next_in_mro, "__is_jishaku__") or isinstance(next_in_mro, self.__class__):
            kwargs["bot"] = bot

        super().__init__(*args, **kwargs)

    @property
    def community(self) -> const.CommunityGuild:
        """Shortcut to get Community Guild object."""
        return self.bot.community

    @property
    def hideout(self) -> const.HideoutGuild:
        """Shortcut to get Hideout Guild object."""
        return self.bot.hideout
