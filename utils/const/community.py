from __future__ import annotations

from typing import TYPE_CHECKING

import discord

if TYPE_CHECKING:
    from utils.bot import AluBot

# GUILD ID
COMMUNITY = 702561315478044804

# CHANNEL IDS
ROLE_SELECTION = 1099742867947262093

LOGS = 731615128050598009
BOT_SPAM = 724986090632642653

STREAM_ROOM_CHANNEL = 766063288302698496

# ROLES IDS
VOICE_MEMBER = 761475276361826315


class CommunityGuild:
    def __init__(self, bot: AluBot):
        self.guild: discord.Guild = bot.get_guild(COMMUNITY)  # type: ignore

    # text channels
    @property
    def role_selection(self) -> discord.TextChannel:
        return self.guild.get_channel(ROLE_SELECTION)  # type: ignore

    @property
    def logs(self) -> discord.TextChannel:
        return self.guild.get_channel(LOGS)  # type: ignore

    @property
    def bot_spam(self) -> discord.TextChannel:
        return self.guild.get_channel(BOT_SPAM)  # type: ignore

    # voice channels
    @property
    def stream_room(self) -> discord.VoiceChannel:
        return self.guild.get_channel(STREAM_ROOM_CHANNEL)  # type: ignore

    # roles
    @property
    def voice_role(self) -> discord.Role:
        return self.guild.get_role(VOICE_MEMBER)  # type: ignore
