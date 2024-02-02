from __future__ import annotations

from typing import TYPE_CHECKING, Any

from .._base.twitch_check import TwitchAccountCheckBase

if TYPE_CHECKING:
    from bot import AluBot


class DotaTwitchAccountCheck(TwitchAccountCheckBase):
    def __init__(self, bot: AluBot, *args: Any, **kwargs: Any) -> None:
        super().__init__(bot, "dota_players", 16, *args, **kwargs)


async def setup(bot: AluBot) -> None:
    await bot.add_cog(DotaTwitchAccountCheck(bot))
