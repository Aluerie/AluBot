from .._base.twitch_check import TwitchAccountCheckBase


class LoLTwitchAccountCheck(TwitchAccountCheckBase):
    def __init__(self, bot, *args, **kwargs) -> None:
        super().__init__(bot, "lol_players", 18, *args, **kwargs)


async def setup(bot) -> None:
    await bot.add_cog(LoLTwitchAccountCheck(bot))
