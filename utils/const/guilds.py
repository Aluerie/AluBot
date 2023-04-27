from __future__ import annotations

from enum import Enum
from typing import TYPE_CHECKING

import discord

if TYPE_CHECKING:
    from utils import AluBot

__all__ = ('Sid', 'Cid', 'Rid', 'Uid', 'CommunityGuild', 'HideoutGuild')


class EnumID(Enum):
    def __int__(self) -> int:
        return self.value

    def __str__(self) -> str:
        return self.mention

    @property
    def id(self):
        return self.value

    @property
    def mention(self) -> str:
        raise NotImplemented


class ChannelEnum(EnumID):
    @property
    def mention(self) -> str:
        return f'<#{self.value}>'


class RoleEnum(EnumID):
    @property
    def mention(self) -> str:
        return f'<@&{self.value}>'


class UserEnum(EnumID):
    @property
    def mention(self) -> str:
        return f'<@{self.value}>'


class Sid:
    community = 702561315478044804
    hideout = 759916212842659850


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

    # HIDEOUT
    global_logs = 997149550324240465
    daily_report = 1066406466778566801

    spam_me = 970823670702411810
    test_spam = 1066379298363166791

    repost = 971504469995049041

    copy_dota_info = 873430376033452053
    copy_dota_steam = 881843565251141632
    copy_dota_tweets = 963954743644934184

    event_pass = 966316773869772860


class Rid(RoleEnum):
    # COMMUNITY
    bots = 724981475099017276
    nsfw_bots = 959955573405777981
    voice = 761475276361826315
    rolling_stone = 819096910848851988
    live_stream = 760082390059581471
    birthday = 748586533627363469
    stream_lover = 760082003495223298
    discord_mods = 855839522620047420
    level_zero = 852663921085251585

    # HIDEOUT
    event = 1090274008680902667
    jailed_bots = 1090428532162822234

    @staticmethod
    def is_category_role(role_id: int) -> bool:
        return role_id in [
            856589983707693087,  # moderation
            852199351808032788,  # activity
            852193537067843634,  # subscription
            852199851840372847,  # special
            851786344354938880,  # games
            852192240306618419,  # notification
            852194400922632262,  # pronoun
            727492782196916275,  # plebs
        ]

    @staticmethod
    def is_ignored_for_logs(role_id: int) -> bool:
        return role_id in [Rid.voice.id, Rid.live_stream.id] or Rid.is_category_role(role_id)


class Uid(UserEnum):
    alu = 312204139751014400
    bot = 713124699663499274
    yen = 948934071432654929
    lala = 812763204010246174
    mango = 213476188037971968
    nqn = 559426966151757824


class SavedGuild:
    def __init__(self, bot: AluBot, guild_id: int):
        self.bot: AluBot = bot
        self.id: int = guild_id

    @property
    def guild(self) -> discord.Guild:
        return self.bot.get_guild(self.id)  # type: ignore


class CommunityGuild(SavedGuild):
    def __init__(self, bot: AluBot):
        super().__init__(bot, Sid.community)

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


class HideoutGuild(SavedGuild):
    """
    My (probably wrong) way to combat
    absurd amount of "type: ignore" in the code
    with `get_channel` and similar methods for channels with known ids.

    This class basically mirrors my HideOut guild and tells the type checker
    known channels and their type, known roles, etc.
    """

    def __init__(self, bot: AluBot):
        super().__init__(bot, Sid.hideout)

    # channels
    @property
    def global_logs(self) -> discord.TextChannel:
        return self.bot.get_channel(Cid.global_logs.id)  # type: ignore

    @property
    def daily_report(self) -> discord.TextChannel:
        return self.bot.get_channel(Cid.daily_report.id)  # type: ignore

    @property
    def spam_channel_id(self) -> int:
        return Cid.test_spam.id if self.bot.test else Cid.spam_me.id

    @property
    def spam(self) -> discord.TextChannel:
        return self.bot.get_channel(self.spam_channel_id)  # type: ignore

    @property
    def repost(self) -> discord.TextChannel:
        return self.bot.get_channel(Cid.repost.id)  # type: ignore

    @property
    def copy_dota_tweets(self) -> discord.TextChannel:
        return self.bot.get_channel(Cid.copy_dota_tweets.id)  # type: ignore

    # roles
    @property
    def jailed_bots(self) -> discord.Role:
        return self.guild.get_role(Rid.jailed_bots.id)  # type: ignore
