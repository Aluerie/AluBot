from __future__ import annotations

from typing import TYPE_CHECKING

from .code_run import CodeRun
from .control import Control
from .discord_management import DiscordManagement
from .jsk import AluJishaku
from .logs_via_webhook import LogsViaWebhook
from .reload import Reload
from .sync import Sync
from .testing import Testing
from .tools import Tools

if TYPE_CHECKING:
    from bot import AluBot


class Dev(
    CodeRun,
    Control,
    DiscordManagement,
    LogsViaWebhook,
    Reload,
    Sync,
    Testing,
    Tools,
):
    """Developer only commands.

    These commands are only to be used by Aluerie.
    """


async def setup(bot: AluBot) -> None:
    """Load AluBot extension. Framework of discord.py."""
    await bot.add_cog(Dev(bot))
    await bot.add_cog(AluJishaku(bot))
