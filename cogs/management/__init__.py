from .owner import AdminTools
from .coderun import CodeRun
from .sync import SyncCommandCog


class Management(AdminTools, CodeRun, SyncCommandCog):
    """
    Tools for the bot devs and only for them.
    """


async def setup(bot):
    await bot.add_cog(Management(bot))
