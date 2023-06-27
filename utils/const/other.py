from enum import StrEnum


class Slash(StrEnum):
    """Slash mentions strings."""

    feedback = '</feedback:1060350834367549541>'
    help = '</help:971447382787108919>'


class Rgx:
    # these match/capture whole mentions/emote as in <a:blabla:123>
    user_mention = r'<@!?\d+>'
    role_mention = r'<@&\d+>'
    channel_mention = r'<#\d+>'
    slash_mention = r'</[a-zA-Z0-9_]{2,32}:[0-9]{18,22}>'
    emote = r'<a?:[a-zA-Z0-9_]{2,32}:[0-9]{18,22}>'

    # old stuff
    whitespace = r"\s"  # whitespaces
    emote_old = r"<(?P<animated>a?):(?P<name>[a-zA-Z0-9_]{2,32}):(?P<id>[0-9]{18,22})>"  # emotes
    nqn = r":(?P<name>[a-zA-Z0-9_]{2,32}):"  # standard emotes
    # emoji = get_emoji_regexp() # use from emoji import get_emoji_regexp for this
    bug_check = r":.*:"
    emote_stats = r"<a?:[a-zA-Z0-9_]{2,32}:[0-9]{18,22}>"
    emote_stats_ids = r"<a?:[a-zA-Z0-9_]{2,32}:([0-9]{18,22})>"
    invis = "[^!-~]+"  # IDK might be huge question mark


# TODO: include above^
REGEX_URL_LINK = r"http[s]?://(?:[a-zA-Z]|[0-9]|[$-_@.&+]|[!*(),]|(?:%[0-9a-fA-F][0-9a-fA-F]))+"


class Picture(StrEnum):
    github = 'https://pics.freeicons.io/uploads/icons/png/4381378511600029534-512.png'
    heart = "https://emojipedia-us.s3.dualstack.us-west-1.amazonaws.com/thumbs/120/google/263/purple-heart_1f49c.png"
    twitch = (
        "https://cdn3.iconfinder.com/data/icons/"
        "social-messaging-ui-color-shapes-2-free/128/social-twitch-circle-512.png"
    )


class Logo(StrEnum):
    python = "https://i.imgur.com/5BFecvA.png"

    # this image is made by removing (R) from
    # https://cdn.cloudflare.steamstatic.com/apps/dota2/images/dota_react/global/dota2_logo_symbol.png
    dota = 'https://i.imgur.com/F8uMnWr.png'


class Limit:
    class Embed:
        sum_all = 6000
        footer_text = 2048
        title = 256
        description = 4096
        field_amount = 25
        field_name = 256
        field_value = 1024
