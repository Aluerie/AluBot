from .._base.twitch_check import TwitchAccountCheckBase


class DotaTwitchAccountCheck(TwitchAccountCheckBase):
    def __init__(self, bot, *args, **kwargs) -> None:
        super().__init__(bot, "dota_players", 16, *args, **kwargs)


async def setup(bot) -> None:
    await bot.add_cog(DotaTwitchAccountCheck(bot))
