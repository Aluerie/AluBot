from .._base import TwitchAccountCheckBase


class LoLTwitchAccountCheck(TwitchAccountCheckBase):
    def __init__(self, bot):
        super().__init__(bot, "lol_players", 18)


async def setup(bot):
    await bot.add_cog(LoLTwitchAccountCheck(bot))
