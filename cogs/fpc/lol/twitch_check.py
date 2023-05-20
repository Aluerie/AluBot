from .._fpc_utils.twitch_check import TwitchAccountCheckBase


class LoLTwitchAccountCheck(TwitchAccountCheckBase):
    def __init__(self, bot, *args, **kwargs):
        super().__init__(bot, "lol_players", 18, *args, **kwargs)


async def setup(bot):
    await bot.add_cog(LoLTwitchAccountCheck(bot))
