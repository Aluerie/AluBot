from .._base import TwitchAccountCheckBase


class DotaTwitchAccountCheck(TwitchAccountCheckBase):
    def __init__(self, bot):
        super().__init__(bot, "dota_players", 16)


async def setup(bot):
    await bot.add_cog(DotaTwitchAccountCheck(bot))
