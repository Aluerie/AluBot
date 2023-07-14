from __future__ import annotations

from enum import IntEnum
from typing import TYPE_CHECKING, TypeVar

import discord

if TYPE_CHECKING:
    from utils import AluBot

T = TypeVar("T")


class SnowflakeEnum(IntEnum):
    def __str__(self) -> str:
        return self.mention

    @property
    def mention(self) -> str:
        raise NotImplemented


class ChannelEnum(SnowflakeEnum):
    @property
    def mention(self) -> str:
        return f'<#{self.value}>'


class RoleEnum(SnowflakeEnum):
    @property
    def mention(self) -> str:
        return f'<@&{self.value}>'


class UserEnum(SnowflakeEnum):
    @property
    def mention(self) -> str:
        return f'<@{self.value}>'


class Guild:
    community = 702561315478044804
    hideout = 759916212842659850

    # friends
    stone = 773607529879699497

    # emotes

    emote1 = 1123901376435589173

    brand1 = 1125050799572131982
    brand2 = 1125050890777268355


MY_GUILDS = [Guild.hideout, Guild.community]
TRUSTED_GUILDS = [Guild.hideout, Guild.stone]


class Channel(ChannelEnum):
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
    dota2tweets = 1124123142068109392

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

    dota_info = 873430376033452053
    github_webhook = 1107050162628595742

    event_pass = 966316773869772860


class Role(RoleEnum):
    # COMMUNITY
    sister_of_the_veil = 821051642443071498
    bots = 724981475099017276
    nsfw_bots = 959955573405777981
    voice = 761475276361826315
    rolling_stone = 819096910848851988
    live_stream = 760082390059581471
    birthday = 748586533627363469
    stream_lover = 760082003495223298
    discord_mods = 855839522620047420
    level_zero = 852663921085251585
    birthday_lover = 1106342236100243499

    colour_category = 851786344354938880
    activity_category = 852199351808032788

    # HIDEOUT
    event = 1090274008680902667
    jailed_bots = 1090428532162822234
    error_ping = 1116171071528374394


CATEGORY_ROLES = [
    856589983707693087,  # moderation
    852199351808032788,  # activity
    852193537067843634,  # subscription
    852199851840372847,  # special
    851786344354938880,  # games
    852192240306618419,  # notification
    727492782196916275,  # plebs
]

IGNORED_FOR_LOGS = [Role.voice, Role.live_stream] + CATEGORY_ROLES


class User(UserEnum):
    aluerie = 312204139751014400
    alubot = 713124699663499274
    yenbot = 1001856865631748159
    lala = 812763204010246174
    mango = 213476188037971968
    nqn = 559426966151757824


MY_BOTS = [User.alubot, User.yenbot]


class SavedGuild:
    """Represents a Discord Saved guild.

    This class is supposed to be subclassed in order
    to mirror structure of known Discord Guild with correct typing, i.e.
    >>> self.bot.community.spam # typechecker knows it's discord.TextChannel

    For more look info look into subclasses below.
    - :class:`~CommunityGuild`
    - :class:`~HideoutGuild`

    Attributes
    ------------
    bot: :class:`AluBot`
        The bot instance to initiate all snowflakes into discord Objects
    id: :class:`int`
        Snowflake ID for the guild itself.
    """

    def __init__(self, bot: AluBot, guild_id: int):
        self.bot: AluBot = bot
        self.id: int = guild_id

    def __repr__(self) -> str:
        return f'<{self.__class__.__name__} id={self.id}>'

    @property
    def guild(self) -> discord.Guild:
        guild = self.bot.get_guild(self.id)
        if guild is None:
            raise RuntimeError(f"{self} not in cache.")
        return guild

    def get_channel(self, channel_id: int, typ: type[T]) -> T:
        channel = self.guild.get_channel(channel_id)
        if channel:
            if isinstance(channel, typ):
                return channel
            raise TypeError(f"Channel id={channel_id} was type: {type(channel)} expected: {typ}")

            # the other way for this is
            #   >>> # this line omitted from runtime when python is run with - O
            #   >>> assert isinstance(channel, typ)
            #   >>> return channel
        else:
            raise RuntimeError(f"Channel id={channel_id} from {self} not in cache")

    def get_role(self, role_id: int) -> discord.Role:
        role = self.guild.get_role(role_id)
        if role is None:
            raise RuntimeError(f"Role id={role_id} from {self} not in cache")
        return role

    def get_member(self, user_id: int) -> discord.Member:
        member = self.guild.get_member(user_id)
        if member is None:
            raise RuntimeError(f"Member id={user_id} from {self} not in cache")
        return member

    @property
    def aluerie(self) -> discord.Member:
        return self.get_member(User.aluerie)


class CommunityGuild(SavedGuild):
    def __init__(self, bot: AluBot):
        super().__init__(bot, Guild.community)

    # channels #########################################################################################################
    @property
    def role_selection(self) -> discord.TextChannel:
        return self.get_channel(Channel.role_selection, discord.TextChannel)

    @property
    def welcome(self) -> discord.TextChannel:
        return self.get_channel(Channel.welcome, discord.TextChannel)

    @property
    def bday_notifs(self) -> discord.TextChannel:
        return self.get_channel(Channel.bday_notifs, discord.TextChannel)

    @property
    def stream_notifs(self) -> discord.TextChannel:
        return self.get_channel(Channel.stream_notifs, discord.TextChannel)

    @property
    def general(self) -> discord.TextChannel:
        return self.get_channel(Channel.general, discord.TextChannel)

    @property
    def comfy_spam(self) -> discord.TextChannel:
        return self.get_channel(Channel.comfy_spam, discord.TextChannel)

    @property
    def emote_spam(self) -> discord.TextChannel:
        return self.get_channel(Channel.emote_spam, discord.TextChannel)

    @property
    def logs(self) -> discord.TextChannel:
        return self.get_channel(Channel.logs, discord.TextChannel)

    @property
    def bot_spam(self) -> discord.TextChannel:
        return self.get_channel(Channel.bot_spam, discord.TextChannel)

    @property
    def nsfw_bot_spam(self) -> discord.TextChannel:
        return self.get_channel(Channel.nsfw_bot_spam, discord.TextChannel)

    @property
    def stream_room(self) -> discord.VoiceChannel:
        return self.get_channel(Channel.stream_room, discord.VoiceChannel)

    @property
    def patch_notes(self) -> discord.TextChannel:
        return self.get_channel(Channel.patch_notes, discord.TextChannel)

    @property
    def suggestions(self) -> discord.TextChannel:
        return self.get_channel(Channel.suggestions, discord.TextChannel)

    @property
    def dota_news(self) -> discord.TextChannel:
        return self.get_channel(Channel.dota_news, discord.TextChannel)

    @property
    def bugtracker_news(self) -> discord.TextChannel:
        return self.get_channel(Channel.bugtracker_news, discord.TextChannel)

    @property
    def dota2tweets(self) -> discord.TextChannel:
        return self.get_channel(Channel.dota2tweets, discord.TextChannel)

    @property
    def my_time(self) -> discord.VoiceChannel:
        return self.get_channel(Channel.my_time, discord.VoiceChannel)

    @property
    def total_people(self) -> discord.VoiceChannel:
        return self.get_channel(Channel.total_people, discord.VoiceChannel)

    @property
    def total_bots(self) -> discord.VoiceChannel:
        return self.get_channel(Channel.total_bots, discord.VoiceChannel)

    # roles ############################################################################################################
    @property
    def sister_of_the_veil(self) -> discord.Role:
        return self.get_role(Role.sister_of_the_veil)

    @property
    def voice_role(self) -> discord.Role:
        return self.get_role(Role.voice)

    @property
    def bots_role(self) -> discord.Role:
        return self.get_role(Role.bots)

    @property
    def nsfw_bots_role(self) -> discord.Role:
        return self.get_role(Role.nsfw_bots)

    @property
    def live_stream_role(self) -> discord.Role:
        return self.get_role(Role.live_stream)

    @property
    def birthday_role(self) -> discord.Role:
        return self.get_role(Role.birthday)

    @property
    def rolling_stone_role(self) -> discord.Role:
        return self.get_role(Role.rolling_stone)

    @property
    def stream_lover_role(self) -> discord.Role:
        return self.get_role(Role.stream_lover)


class HideoutGuild(SavedGuild):
    def __init__(self, bot: AluBot):
        super().__init__(bot, Guild.hideout)

    # channels
    @property
    def global_logs(self) -> discord.TextChannel:
        return self.get_channel(Channel.global_logs, discord.TextChannel)

    @property
    def daily_report(self) -> discord.TextChannel:
        return self.get_channel(Channel.daily_report, discord.TextChannel)

    @property
    def spam_channel_id(self) -> int:
        return Channel.test_spam if self.bot.test else Channel.spam_me

    @property
    def spam(self) -> discord.TextChannel:
        return self.get_channel(self.spam_channel_id, discord.TextChannel)

    @property
    def repost(self) -> discord.TextChannel:
        return self.get_channel(Channel.repost, discord.TextChannel)

    # roles ############################################################################################################
    @property
    def jailed_bots(self) -> discord.Role:
        return self.get_role(Role.jailed_bots)

    @property
    def error_ping(self) -> discord.Role:
        return self.get_role(Role.error_ping)
