from __future__ import annotations

from typing import TYPE_CHECKING

import discord

if TYPE_CHECKING:
    from utils.bot import AluBot

COMMUNITY = 702561315478044804

ROLE_SELECTION = 1099742867947262093

LOGS = 731615128050598009
BOT_SPAM = 724986090632642653


class CommunityGuild:

    def __init__(self, bot: AluBot):
        self.guild: discord.Guild = bot.get_guild(COMMUNITY)  # type: ignore
    
    @property
    def role_selection(self) -> discord.TextChannel:
        return self.guild.get_channel(ROLE_SELECTION) # type: ignore

    @property
    def logs(self) -> discord.TextChannel:
        return self.guild.get_channel(LOGS)  # type: ignore
    
    @property
    def bot_spam(self) -> discord.TextChannel:
        return self.guild.get_channel(BOT_SPAM) # type: ignore
    

