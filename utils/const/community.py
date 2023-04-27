from __future__ import annotations

from typing import TYPE_CHECKING

import discord

from ._enums import ChannelEnum, RoleEnum, UserEnum

if TYPE_CHECKING:
    from utils import AluBot

__all__ = (
    'Cid',
    'Rid',
    'CommunityGuild',
)

# GUILD ID
COMMUNITY = 702561315478044804


class Cid(ChannelEnum):
    rules = 724996010169991198
    role_selection = 1099742867947262093

    welcome = 725000501690630257
    bday_notifs = 748604236190842881
    stream_notifs = 724420415199379557
    clips = 770721052711845929

    general = 702561315478044807
    emote_spam = 730838697443852430
    comfy_spam = 727539910713671802
    pubs_talk = 731376390103892019
    logs = 731615128050598009
    confessions = 731703242597072896
    weebs = 731887442768166933
    bot_spam = 724986090632642653
    nsfw_bot_spam = 731607736155897978

    dota_news = 724986688589267015

    stream_room = 766063288302698496

    patch_notes = 731759693113851975
    suggestions = 724994495581782076

    my_time = 788915790543323156
    total_people = 795743012789551104
    total_bots = 795743065787990066


class Rid(RoleEnum):
    bots = 724981475099017276
    nsfw_bots = 959955573405777981
    voice = 761475276361826315
    rolling_stone = 819096910848851988
    live_stream = 760082390059581471
    birthday = 748586533627363469
    stream_lover = 760082003495223298
    discord_mods = 855839522620047420


class Uid(UserEnum):
    alu = 312204139751014400
    bot = 713124699663499274
    yen = 948934071432654929
    lala = 812763204010246174
    mango = 213476188037971968
    nqn = 559426966151757824


class CommunityGuild:
    def __init__(self, bot: AluBot):
        self.bot: AluBot = bot

    @property
    def guild(self) -> discord.Guild:
        return self.bot.get_guild(COMMUNITY)  # type: ignore

    # channels #########################################################
    @property
    def role_selection(self) -> discord.TextChannel:
        return self.bot.get_channel(Cid.role_selection.id)  # type: ignore

    @property
    def welcome(self) -> discord.TextChannel:
        return self.bot.get_channel(Cid.welcome.id)  # type: ignore

    @property
    def bday_notifs(self) -> discord.TextChannel:
        return self.bot.get_channel(Cid.bday_notifs.id)  # type: ignore

    @property
    def stream_notifs(self) -> discord.TextChannel:
        return self.bot.get_channel(Cid.stream_notifs.id)  # type: ignore

    @property
    def general(self) -> discord.TextChannel:
        return self.bot.get_channel(Cid.general.id)  # type: ignore

    @property
    def comfy_spam(self) -> discord.TextChannel:
        return self.bot.get_channel(Cid.comfy_spam.id)  # type: ignore

    @property
    def emote_spam(self) -> discord.TextChannel:
        return self.bot.get_channel(Cid.emote_spam.id)  # type: ignore

    @property
    def logs(self) -> discord.TextChannel:
        return self.bot.get_channel(Cid.logs.id)  # type: ignore

    @property
    def bot_spam(self) -> discord.TextChannel:
        return self.bot.get_channel(Cid.bot_spam.id)  # type: ignore

    @property
    def nsfw_bot_spam(self) -> discord.TextChannel:
        return self.bot.get_channel(Cid.nsfw_bot_spam.id)  # type: ignore

    @property
    def stream_room(self) -> discord.VoiceChannel:
        return self.bot.get_channel(Cid.stream_room.id)  # type: ignore

    @property
    def patch_notes(self) -> discord.TextChannel:
        return self.bot.get_channel(Cid.patch_notes.id)  # type: ignore

    @property
    def suggestions(self) -> discord.TextChannel:
        return self.bot.get_channel(Cid.suggestions.id)  # type: ignore

    @property
    def dota_news(self) -> discord.TextChannel:
        return self.bot.get_channel(Cid.dota_news.id)  # type: ignore

    @property
    def my_time(self) -> discord.VoiceChannel:
        return self.bot.get_channel(Cid.my_time.id)  # type: ignore

    @property
    def total_people(self) -> discord.VoiceChannel:
        return self.bot.get_channel(Cid.total_people.id)  # type: ignore

    @property
    def total_bots(self) -> discord.VoiceChannel:
        return self.bot.get_channel(Cid.total_bots.id)  # type: ignore

    # roles ############################################################
    @property
    def voice_role(self) -> discord.Role:
        return self.guild.get_role(Rid.voice.id)  # type: ignore

    @property
    def bots_role(self) -> discord.Role:
        return self.guild.get_role(Rid.bots.id)  # type: ignore

    @property
    def nsfw_bots_role(self) -> discord.Role:
        return self.guild.get_role(Rid.nsfw_bots.id)  # type: ignore

    @property
    def live_stream_role(self) -> discord.Role:
        return self.guild.get_role(Rid.live_stream.id)  # type: ignore

    @property
    def birthday_role(self) -> discord.Role:
        return self.guild.get_role(Rid.birthday.id)  # type: ignore

    @property
    def rolling_stone_role(self) -> discord.Role:
        return self.guild.get_role(Rid.rolling_stone.id)  # type: ignore

    @property
    def stream_lover_role(self) -> discord.Role:
        return self.guild.get_role(Rid.stream_lover.id)  # type: ignore
