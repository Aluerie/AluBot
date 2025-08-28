from __future__ import annotations

from typing import TYPE_CHECKING

from utils.const import Emote

from .birthdays import Birthdays
from .chatter import Chatter
from .color_roles import ColorRoles
from .confessions import Confessions
from .emote_stats import EmoteStats
from .levels import Levels
from .logger import Logger
from .moderation import Moderation
from .old_timers import OldTimers
from .stats import StatsVoiceChannels
from .suggestions import Suggestions
from .twitch_notifications import TwitchNotifications
from .welcome import Welcome

if TYPE_CHECKING:
    from bot import AluBot


class Community(
    Birthdays,
    Chatter,
    ColorRoles,
    Confessions,
    EmoteStats,
    Levels,
    Logger,
    Moderation,
    OldTimers,
    StatsVoiceChannels,
    Suggestions,
    TwitchNotifications,
    Welcome,
):
    """Aluerie's community server commands.

    This bot is centered around Aluerie's community so a lot of features and commands
    are made exclusively for our community discord server.
    """


async def setup(bot: AluBot) -> None:
    """Load AluBot extension. Framework of discord.py."""
    await bot.add_cog(Community(bot, emote=Emote.peepoComfy))
