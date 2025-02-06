from __future__ import annotations

from enum import IntEnum
from typing import TYPE_CHECKING, TypeVar, override

import discord

from ._meta import CONSTANTS

if TYPE_CHECKING:
    from bot import AluBot

T = TypeVar("T")


class SnowflakeEnum(IntEnum):
    """Snowflake Enum boilerplate class.

    Enum classes for Discord models should subclass this.
    These classes provide bare-bone minimum functionality with IDs
    without utilizing actual models from discord.py
    """

    @override
    def __str__(self) -> str:
        return self.mention

    @property
    def mention(self) -> str:
        """Get Discord mention string.

        Usually allows various interactions within Discord.
        """
        raise NotImplementedError


class ChannelEnum(SnowflakeEnum):
    """Discord Channel."""

    @property
    @override
    def mention(self) -> str:
        return f"<#{self.value}>"


class RoleEnum(SnowflakeEnum):
    """Discord Role."""

    @property
    @override
    def mention(self) -> str:
        return f"<@&{self.value}>"


class UserEnum(SnowflakeEnum):
    """Discord User."""

    @property
    @override
    def mention(self) -> str:
        return f"<@{self.value}>"


class Guild:
    """Discord known guild ids."""

    community = 702561315478044804
    hideout = 759916212842659850

    # friends
    stone = 773607529879699497

    # emotes

    brand1 = 1125050799572131982
    brand2 = 1125050890777268355


MY_GUILDS = [Guild.hideout, Guild.community]
PREMIUM_GUILDS = [Guild.community, Guild.hideout, Guild.stone]


class EmoteGuilds(CONSTANTS):
    """Discord IDs for Bot Emote Servers."""  # TODO: remove this when we sort out app emojis.

    DOTA = (1123282491294359563, 1123897964700643399, 1123898231198339083, 1123898374387662909)
    LOL = (1123898479308185691, 1123898578843205692, 1123899243304861718, 1123899449857548408)
    EMOTE = (1123901376435589173, 1123901447277379644, 1123901514289774632, 1123901546409762896)
    BRAND = (1125050799572131982, 1125050890777268355)


class Channel(ChannelEnum):
    """Discord IDs for known/special channels."""

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
    bugtracker_news = 1119041743002800138
    steamdb_news = 1101299663459590164

    stream_room = 766063288302698496

    patch_notes = 731759693113851975
    suggestions = 1133711868612059147

    my_time = 788915790543323156
    total_people = 795743012789551104
    total_bots = 795743065787990066

    # HIDEOUT
    global_logs = 997149550324240465

    alu_spam = 970823670702411810
    yen_spam = 1066379298363166791
    alu_logs = 1075497084075130880

    repost = 971504469995049041

    hideout_logs = 869735263209947228
    dota_updates = 873430376033452053
    alubot_github = 1107050162628595742


class Role(RoleEnum):
    """Discord IDs for known/special roles."""

    # COMMUNITY
    sister_of_the_veil = 821051642443071498
    bots = 724981475099017276
    nsfw_bots = 959955573405777981
    live_stream = 760082390059581471
    discord_mods = 855839522620047420
    level_zero = 852663921085251585
    birthday_lover = 1106342236100243499

    colour_category = 851786344354938880
    activity_category = 852199351808032788

    # activity roles
    birthday = 748586533627363469
    voice = 761475276361826315

    # special roles
    blacklisted = 1180423070343757855
    rolling_stone = 819096910848851988

    # notification roles
    stream_lover = 760082003495223298

    # HIDEOUT
    event = 1090274008680902667
    jailed_bots = 1090428532162822234
    error = 1116171071528374394
    test_error = 1337106675433340990


CATEGORY_ROLES = [
    856589983707693087,  # moderation
    852199351808032788,  # activity
    852193537067843634,  # subscription
    852199851840372847,  # special
    851786344354938880,  # games
    852192240306618419,  # notification
    727492782196916275,  # plebs
]

IGNORED_FOR_LOGS = [Role.voice, Role.live_stream, *CATEGORY_ROLES]


class User(UserEnum):
    """Discord IDs for known/special users/bots."""

    aluerie = 312204139751014400
    alubot = 713124699663499274
    yenbot = 1001856865631748159
    lala = 812763204010246174
    mango = 213476188037971968
    nqn = 559426966151757824


MY_BOTS = [User.alubot, User.yenbot]


class SavedGuild:
    """Represents a Discord Saved guild.

    Type-hint friendly way to get my desired channels out of bot cache.

    This class is supposed to be subclassed in order
    to mirror structure of known Discord Guild with correct typing, i.e.
    >>> self.bot.community.spam # typechecker knows it's discord.TextChannel

    For more look info look into subclasses below.
    * CommunityGuild
    * HideoutGuild

    Attributes
    ----------
    bot
        The bot instance to initiate all snowflakes into discord Objects
    id
        Snowflake ID for the guild itself.

    """

    def __init__(self, bot: AluBot, guild_id: int) -> None:
        self.bot: AluBot = bot
        self.id: int = guild_id

    @override
    def __repr__(self) -> str:
        return f"<{self.__class__.__name__} id={self.id}>"

    @property
    def guild(self) -> discord.Guild:
        """Get guild object."""
        guild = self.bot.get_guild(self.id)
        if guild is None:
            msg = f"{self} not in cache."
            raise RuntimeError(msg)
        return guild

    def get_channel(self, channel_id: int, channel_type: type[T]) -> T:
        """Get channel object by id."""
        channel = self.guild.get_channel(channel_id)
        if channel:
            if isinstance(channel, channel_type):
                return channel
            msg = f"Channel id={channel_id} was type: {type(channel)} expected: {channel_type}"
            raise TypeError(msg)

            # the other way for this is
            #   >>> # this line omitted from runtime when python is run with - O
            #   >>> assert isinstance(channel, typ)
            #   >>> return channel
        msg = f"Channel id={channel_id} from {self} not in cache"
        raise RuntimeError(msg)

    def get_role(self, role_id: int) -> discord.Role:
        """Get role object by id."""
        role = self.guild.get_role(role_id)
        if role is None:
            msg = f"Role id={role_id} from {self} not in cache"
            raise RuntimeError(msg)
        return role

    def get_member(self, user_id: int) -> discord.Member:
        """Get member object by id."""
        member = self.guild.get_member(user_id)
        if member is None:
            msg = f"Member id={user_id} from {self} not in cache"
            raise RuntimeError(msg)
        return member

    @property
    def aluerie(self) -> discord.Member:
        """Get member object for @Aluerie."""
        return self.get_member(User.aluerie)


class CommunityGuild(SavedGuild):
    """Community Server.

    Just a small comfy server for my community that somehow find it across the Internet.
    """

    def __init__(self, bot: AluBot) -> None:
        super().__init__(bot, Guild.community)

    # channels #########################################################################################################
    @property
    def role_selection(self) -> discord.TextChannel:
        """Colour and other roles selection channel."""
        return self.get_channel(Channel.role_selection, discord.TextChannel)

    @property
    def welcome(self) -> discord.TextChannel:
        """Channel to welcome community new-comers."""
        return self.get_channel(Channel.welcome, discord.TextChannel)

    @property
    def bday_notifs(self) -> discord.TextChannel:
        """Channel for birthday notifications."""
        return self.get_channel(Channel.bday_notifs, discord.TextChannel)

    @property
    def stream_notifs(self) -> discord.TextChannel:
        """My own stream notifications channel."""
        return self.get_channel(Channel.stream_notifs, discord.TextChannel)

    @property
    def general(self) -> discord.TextChannel:
        """General channel."""
        return self.get_channel(Channel.general, discord.TextChannel)

    @property
    def comfy_spam(self) -> discord.TextChannel:
        """Channel for peepoComfy emote spam."""
        return self.get_channel(Channel.comfy_spam, discord.TextChannel)

    @property
    def emote_spam(self) -> discord.TextChannel:
        """Channel for emote spam."""
        return self.get_channel(Channel.emote_spam, discord.TextChannel)

    @property
    def logs(self) -> discord.TextChannel:
        """Private channel to log stuff for moderation purposes."""
        return self.get_channel(Channel.logs, discord.TextChannel)

    @property
    def bot_spam(self) -> discord.TextChannel:
        """Channel for bot spam."""
        return self.get_channel(Channel.bot_spam, discord.TextChannel)

    @property
    def nsfw_bot_spam(self) -> discord.TextChannel:
        """Channel for NSFW bot spam."""
        return self.get_channel(Channel.nsfw_bot_spam, discord.TextChannel)

    @property
    def stream_room(self) -> discord.VoiceChannel:
        """Voice Channel to stream in."""
        return self.get_channel(Channel.stream_room, discord.VoiceChannel)

    @property
    def patch_notes(self) -> discord.TextChannel:
        """Community server news. Called Patch Notes for fun."""
        return self.get_channel(Channel.patch_notes, discord.TextChannel)

    @property
    def suggestions(self) -> discord.ForumChannel:
        """Forum channel where each thread is a server related suggestion."""
        return self.get_channel(Channel.suggestions, discord.ForumChannel)

    @property
    def dota_news(self) -> discord.TextChannel:
        """Channel where dota news/announcements are posted."""
        return self.get_channel(Channel.dota_news, discord.TextChannel)

    @property
    def bugtracker_news(self) -> discord.TextChannel:
        """Channel where my bot tracks Valve activity in the bugtracker."""
        return self.get_channel(Channel.bugtracker_news, discord.TextChannel)

    @property
    def my_time(self) -> discord.VoiceChannel:
        """Channel which name somewhat reflects my local time."""
        return self.get_channel(Channel.my_time, discord.VoiceChannel)

    @property
    def total_people(self) -> discord.VoiceChannel:
        """Channel which name somewhat reflects amount of people in the server."""
        return self.get_channel(Channel.total_people, discord.VoiceChannel)

    @property
    def total_bots(self) -> discord.VoiceChannel:
        """Channel which name somewhat reflects amount of people in the server."""
        return self.get_channel(Channel.total_bots, discord.VoiceChannel)

    # roles ############################################################################################################
    @property
    def sister_of_the_veil(self) -> discord.Role:
        """Role with all permissions in community server."""
        return self.get_role(Role.sister_of_the_veil)

    @property
    def voice_role(self) -> discord.Role:
        """Role given to voice chat users."""
        return self.get_role(Role.voice)

    @property
    def bots_role(self) -> discord.Role:
        """Role for bots."""
        return self.get_role(Role.bots)

    @property
    def nsfw_bots_role(self) -> discord.Role:
        """Role for NSFW bots."""
        return self.get_role(Role.nsfw_bots)

    @property
    def live_stream_role(self) -> discord.Role:
        """Role for twitch.tv live streamers."""
        return self.get_role(Role.live_stream)

    @property
    def birthday_role(self) -> discord.Role:
        """Role to mark people whose birthday is today."""
        return self.get_role(Role.birthday)

    @property
    def rolling_stone_role(self) -> discord.Role:
        """Rolling stones flavour role."""
        return self.get_role(Role.rolling_stone)

    @property
    def stream_lover_role(self) -> discord.Role:
        """Role for ping notifications about my stream."""
        return self.get_role(Role.stream_lover)

    @property
    def blacklisted(self) -> discord.Role:
        """Blacklisted Role."""
        return self.get_role(Role.blacklisted)


class HideoutGuild(SavedGuild):
    """Hideout Server.

    A private server of mine with all the notifications, project management, bot logs, reposts, sandbox, etc.
    """

    def __init__(self, bot: AluBot) -> None:
        super().__init__(bot, Guild.hideout)

    # channels
    @property
    def global_logs(self) -> discord.TextChannel:
        """Channel for AluBot global logs."""
        return self.get_channel(Channel.global_logs, discord.TextChannel)

    @property
    def spam_channel_id(self) -> int:
        """Spam channel ID. Note that test version of the bot has different spam channel compared to main one."""
        return Channel.yen_spam if self.bot.test else Channel.alu_spam

    @property
    def spam(self) -> discord.TextChannel:
        """Spam channel. Note that test version of the bot has different spam channel compared to main one."""
        return self.get_channel(self.spam_channel_id, discord.TextChannel)

    @property
    def alubot_logs(self) -> discord.TextChannel:
        """Channel where AluBot posts its own logs from logging library."""
        return self.get_channel(Channel.alu_logs, discord.TextChannel)

    @property
    def repost(self) -> discord.TextChannel:
        """Channel where all news/announcements/notifications get posted/reposted."""
        return self.get_channel(Channel.repost, discord.TextChannel)

    # roles ############################################################################################################
    @property
    def jailed_bots_role(self) -> discord.Role:
        """Role for jailed bots."""
        return self.get_role(Role.jailed_bots)

    @property
    def error_role(self) -> discord.Role:
        """Role to ping developers about bot errors."""
        return self.get_role(Role.error)
