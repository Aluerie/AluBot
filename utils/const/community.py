from __future__ import annotations

from typing import TYPE_CHECKING

import discord

if TYPE_CHECKING:
    from utils import AluBot

# GUILD ID
COMMUNITY = 702561315478044804

# CHANNEL IDS
ROLE_SELECTION = 1099742867947262093

WELCOME = 725000501690630257

EMOTE_SPAM = 730838697443852430
COMFY_SPAM = 727539910713671802
LOGS = 731615128050598009
BOT_SPAM = 724986090632642653

DOTA_NEWS = 724986688589267015

STREAM_ROOM = 766063288302698496

PATCH_NOTES = 731759693113851975
SUGGESTIONS = 724994495581782076

MY_TIME = 788915790543323156
TOTAL_PEOPLE = 795743012789551104
TOTAL_BOTS = 795743065787990066

# ROLES IDS
BOTS_ROLE = 724981475099017276
VOICE_ROLE = 761475276361826315
ROLLING_STONE_ROLE = 819096910848851988

class CommunityGuild:
    def __init__(self, bot: AluBot):
        self.bot: AluBot = bot
    
    @property
    def guild(self) -> discord.Guild:
        return self.bot.get_guild(COMMUNITY)  # type: ignore
    
    # channels
    @property
    def role_selection(self) -> discord.TextChannel:
        return self.bot.get_channel(ROLE_SELECTION)  # type: ignore

    @property
    def welcome(self) -> discord.TextChannel:
        return self.bot.get_channel(WELCOME)  # type: ignore
    @property
    def comfy_spam(self) -> discord.TextChannel:
        return self.bot.get_channel(COMFY_SPAM)  # type: ignore

    @property
    def emote_spam(self) -> discord.TextChannel:
        return self.bot.get_channel(EMOTE_SPAM)  # type: ignore
    
    @property
    def logs(self) -> discord.TextChannel:
        return self.bot.get_channel(LOGS)  # type: ignore

    @property
    def bot_spam(self) -> discord.TextChannel:
        return self.bot.get_channel(BOT_SPAM)  # type: ignore
    
    @property
    def stream_room(self) -> discord.VoiceChannel:
        return self.bot.get_channel(STREAM_ROOM)  # type: ignore
    
    @property
    def patch_notes(self) -> discord.TextChannel:
        return self.bot.get_channel(PATCH_NOTES)  # type: ignore
    
    @property
    def suggestions(self) -> discord.TextChannel:
        return self.bot.get_channel(SUGGESTIONS)  # type: ignore
    
    @property
    def dota_news(self) -> discord.TextChannel:
        return self.bot.get_channel(DOTA_NEWS)  # type: ignore
    
    @property
    def my_time(self) -> discord.VoiceChannel:
        return self.bot.get_channel(MY_TIME)  # type: ignore
    
    @property
    def total_people(self) -> discord.VoiceChannel:
        return self.bot.get_channel(TOTAL_PEOPLE)  # type: ignore

    @property
    def total_bots(self) -> discord.VoiceChannel:
        return self.bot.get_channel(TOTAL_BOTS)  # type: ignore

    # roles
    @property
    def voice_role(self) -> discord.Role:
        return self.bot.get_role(VOICE_ROLE)  # type: ignore
    
    @property
    def bots_role(self) -> discord.Role:
        return self.community.get_role(BOTS_ROLE)  # type: ignore 
    
    @property
    def rolling_stone_role(self) -> discord.Role:
        return self.community.get_role(BOTS_ROLE)  # type: ignore 
