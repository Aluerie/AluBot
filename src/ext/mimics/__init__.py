from __future__ import annotations

from typing import TYPE_CHECKING

from utils.const import Emote

from .fix_social_links import FixSocialLinks
from .manage_mimics import MimicManagement
from .webhooks import WebhookMaintenance

if TYPE_CHECKING:
    from bot import AluBot


class Mimics(
    FixSocialLinks,
    MimicManagement,
    WebhookMaintenance,
    # emote=Emote.FeelsDankManLostHisHat,
):
    """Mimics."""


async def setup(bot: AluBot) -> None:
    """Load AluBot extension. Framework of discord.py."""
    await bot.add_cog(Mimics(bot))
