from enum import StrEnum
from typing import override

from .abc import ASSETS_IMAGES, CONSTANTS, RAW_GITHUB_IMAGES

__all__ = (
    "Emoticon",
    "Limit",
    "Logo",
    "LogoAsset",
    "Picture",
    "Regex",
    "Slash",
    "Twitch",
    "TwitchID",
)


class LogoAsset(StrEnum):
    """Logo images saved as .png file in the repository assets folder."""

    DotaWhite = "dota_white.png"
    """ ^ image above is made by removing (R) from:
    https://cdn.cloudflare.steamstatic.com/apps/dota2/images/dota_react/global/dota2_logo_symbol.png
    """
    TwitchIO = "twitchio.png"
    SteamPy = "steampy.png"
    EditFPC = "edit_fpc.png"
    """Used as an avatar for Edit FPC log messages via webhook."""
    SendFPC = "send_fpc.png"
    """Used as an avatar for Send FPC log messages via webhook."""

    @override
    def __str__(self) -> str:
        """Relative location compared to the workplace directory, i.e. `./assets/images/logo/dota_white.png`."""
        return ASSETS_IMAGES + "logo/" + self.value

    @property
    def url(self) -> str:
        """Link to the image hosted on raw.githubusercontent.com."""
        return RAW_GITHUB_IMAGES + "logo/" + self.value


class Slash(StrEnum):
    """Slash mentions strings.

    These are to be used when we can't easily access `bot.tree` for its `find_mention` method.
    """

    feedback = "</feedback:1060350834367549541>"
    help = "</help:971447382787108919>"


class Emoticon(StrEnum):
    """CDN links for source images for emojis from emojipedia.

    Notes
    -----
    Maybe a bad name, considering everything is taken from emojipedia,
    but I didn't want to sound similar to Emote/Emoji classes.
    """

    Swan = "407/swan_1f9a2.png"

    @override
    def __str__(self) -> str:
        return f"https://em-content.zobj.net/source/microsoft/{self.value}"


class Regex(CONSTANTS):
    # these match/capture whole mentions/emote as in <a:bla:123>
    USER_MENTION = r"<@!?\d+>"
    ROLE_MENTION = r"<@&\d+>"
    CHANNEL_MENTION = r"<#\d+>"
    SLASH_MENTION = r"</[a-zA-Z0-9_]{2,32}:[0-9]{18,22}>"
    EMOTE = r"<a?:[a-zA-Z0-9_]{2,32}:[0-9]{18,22}>"

    # matches the whole links in the string
    URL = r"http[s]?://(?:[a-zA-Z]|[0-9]|[$-_@.&+]|[!*(),]|(?:%[0-9a-fA-F][0-9a-fA-F]))+"

    # old stuff
    WHITESPACE = r"\s"  # whitespaces
    EMOTE_OLD = r"<(?P<animated>a?):(?P<name>[a-zA-Z0-9_]{2,32}):(?P<id>[0-9]{18,22})>"  # emotes
    NQN = r":(?P<name>[a-zA-Z0-9_]{2,32}):"  # standard emotes
    # emoji = get_emoji_regexp() # use from emoji import get_emoji_regexp for this
    IS_DELETED_BY_NQN = r":.*:"
    EMOTE_STATS = r"<a?:[a-zA-Z0-9_]{2,32}:[0-9]{18,22}>"
    EMOTE_STATS_IDS = r"<a?:[a-zA-Z0-9_]{2,32}:([0-9]{18,22})>"
    INVIS = "[^!-~]+"  # IDK might be huge question mark


class Picture(StrEnum):
    Github = "https://pics.freeicons.io/uploads/icons/png/4381378511600029534-512.png"
    Heart = "https://emojipedia-us.s3.dualstack.us-west-1.amazonaws.com/thumbs/120/google/263/purple-heart_1f49c.png"
    DankFix = "https://i.imgur.com/gzrPVLs.png"
    Frog = "https://em-content.zobj.net/thumbs/120/microsoft/319/frog_1f438.png"


class Logo(StrEnum):
    Python = "https://i.imgur.com/5BFecvA.png"

    Dota = "https://i.imgur.com/F8uMnWr.png"
    LeagueOfLegends = "https://i.imgur.com/1DJa07b.png"
    Twitch = "https://cdn3.iconfinder.com/data/icons/social-messaging-ui-color-shapes-2-free/128/social-twitch-circle-512.png"


class Limit:
    class Embed:
        sum_all = 6000
        footer_text = 2048
        title = 256
        description = 4096
        field_amount = 25
        field_name = 256
        field_value = 1024


class TwitchID(StrEnum):
    Me = "180499648"
    Bot = "1158666176"  # @Aluerie account


class Twitch(CONSTANTS):
    MY_USERNAME = "Irene_Adler__"
    LOL_GAME_CATEGORY_ID = "21779"
    DOTA_GAME_CATEGORY_ID = "29595"
    MY_OFFLINE_SCREEN = "https://static-cdn.jtvnw.net/jtv_user_pictures/ed948895-c574-4325-9c0c-d7639a45df64-channel_offline_image-1920x1080.png"
