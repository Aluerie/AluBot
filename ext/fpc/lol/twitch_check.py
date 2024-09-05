from __future__ import annotations

from typing import TYPE_CHECKING, Any

from .._base.twitch_check import TwitchAccountCheckBase

if TYPE_CHECKING:
    from bot import AluBot


class TwitchAccountCheck(TwitchAccountCheckBase):
    def __init__(self, bot: AluBot, *args: Any, **kwargs: Any) -> None:
        super().__init__(bot, "lol_players", 18, *args, **kwargs)


async def setup(bot: AluBot) -> None:
    """Load AluBot extension. Framework of discord.py."""
    await bot.add_cog(TwitchAccountCheck(bot))
