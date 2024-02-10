from enum import StrEnum

from ._meta import CONSTANTS

GITHUB_BOT_IMAGES = "https://raw.githubusercontent.com/Aluerie/AluBot/main/assets/images"


class Slash(StrEnum):
    """Slash mentions strings."""

    feedback = "</feedback:1060350834367549541>"
    help = "</help:971447382787108919>"


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
    Placeholder640X360 = f"{GITHUB_BOT_IMAGES}/hosted/Lavender640x360.png"


class Logo(StrEnum):
    Python = "https://i.imgur.com/5BFecvA.png"

    # the next image is made by removing (R) from
    # https://cdn.cloudflare.steamstatic.com/apps/dota2/images/dota_react/global/dota2_logo_symbol.png
    Dota = "https://i.imgur.com/F8uMnWr.png"
    Lol = "https://i.imgur.com/1DJa07b.png"
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


class Twitch(CONSTANTS):
    MY_USERNAME = "Irene_Adler__"
    MY_USER_ID = 180499648
    LOL_GAME_CATEGORY_ID = "21779"
    DOTA_GAME_CATEGORY_ID = "29595"


class League(CONSTANTS):
    # https://static.developer.riotgames.com/docs/lol/queues.json
    # says 420 is 5v5 Ranked Solo games
    SOLO_RANKED_5v5_QUEUE_ENUM = 420


class Dota(CONSTANTS):
    # remember the imgur.com 429 catastrophe
    # which means that we shouldn't host images there ever
    # because they rate-limit my bot
    # otherwise `bot.transposer.url_to_image` will fail

    HERO_DISCONNECT = f"{GITHUB_BOT_IMAGES}/hosted/DotaDisconnect.png"
    EMPTY_ITEM_TILE = f"{GITHUB_BOT_IMAGES}/hosted/Black_tile.png"

    PLAYER_COLOUR_MAP = (
        "#3375FF",
        "#66FFBF",
        "#BF00BF",
        "#F3F00B",
        "#FF6B00",
        "#FE86C2",
        "#A1B447",
        "#65D9F7",
        "#008321",
        "#A46900",
    )

    TALENT_TREE_ICON = "https://liquipedia.net/commons/images/5/54/Talents.png"
    ATTR_BONUS_ICON = "https://static.wikia.nocookie.net/dota2_gamepedia/images/e/e2/Attribute_Bonus_icon.png"

    AGHANIMS_SCEPTER_ITEM_ID = 108
    AGHANIMS_BLESSING_ITEM_ID = 271
    AGHANIMS_SHARD_ITEM_ID = 609
