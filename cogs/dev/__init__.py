from .coderun import CodeRun
from .error_handlers import setup as eh_setup, teardown as eh_teardown
from .other import AdminTools
from .sync import UmbraSyncCommandCog


class Development(AdminTools, CodeRun, UmbraSyncCommandCog):
    """
    Tools to simplify the bot development.

    Made to be used by the bot devs and only by them.
    """


async def setup(bot):
    await bot.add_cog(Development(bot))
    await eh_setup(bot)


async def teardown(bot):
    await eh_teardown(bot)
