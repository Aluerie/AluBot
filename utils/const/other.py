from enum import StrEnum


class Slash(StrEnum):
    """Slash mentions strings."""

    feedback = '</feedback:1060350834367549541>'
    help = '</help:971447382787108919>'


class Emote(StrEnum):
    """Emote strings."""

    # comments mean that this emote is used in help command for something so i don't reuse it by accident

    # COMMUNITY SERVER, NON-ANIMATED EMOTES ############################################################################
    peepoComfy = '<:_:726438781208756288>' # Category: Community

    # HIDEOUT SERVER, NON-ANIMATED EMOTES ##############################################################################

    bedNerdge = '<:_:1106748389565153300>'
    bubuAyaya = '<:_:764835239138164756>'
    bubuChrist = '<:_:847805078769631262>'
    bubuGun = '<:_:847805078543007755>'
    bubuSip = '<:_:865033396189921290>'
    DankApprove = '<:_:1107470723448057886>'
    DankFix = '<:_:1107470989895417897>'
    DankG = '<:_:998012133948276857>'
    DankHey = '<:_:1107475426076532828>'
    DankHatTooBig = '<:_:1106645924974972978>'
    DankLove = '<:_:1107467504290385950>'
    DankMadgeThreat = '<:_:1107475989312835614>'
    DankZzz = '<:_:1107467287398723656>'
    FeelsDankMan = '<:_:1107471658861735958>'
    FeelsDankManLostHisHat = '<:_:1107471692013502504>'
    Jebaited = '<:_:1107467775749914644>'
    Lewd = '<:_:976604430059331684>'
    peepoBlushDank = '<:_:1107471683448754287>'
    peepoBusiness = '<:_:998157352098340934>'
    # peepoComfy = '<:_:1107471654944260096>' # let's use from community
    peepoHappyDank = '<:_:1107471671520133202>'
    peepoMovie = '<:_:998163742741246003>'
    peepoNiceDay = '<:_:1107477683568382076>'
    peepoPolice = '<:_:1107475416559661126>'
    peepoRoseDank = '<:_:1107475422276497508>'
    peepoStepOnMePls = '<:_:1107471687466889267>'
    peepoWTF = '<:_:1106723199128965140>'
    PepoBeliever = '<:_:1107471650678657064>'
    PepoDetective = '<:_:1107471667711709184>'
    PepoG = '<:_:1106749219181699082>'
    PepoRules = '<:_:1107471675538284585>'
    PogChampPepe = '<:_:1107471663169290260>'
    bedWTF = '<:_:999813662036459610>'
    Ree = '<:_:1107471646115254292>'
    slash = '<:_:823159274954817566>'
    Smartge = '<:_:1107471679644512396>'
    TwoBButt = '<:_:853729747846168576>'

    # logo emotes 
    github_logo = '<:_:1081677464637550662>'
    AluerieServer = '<:_:1121891520048533535>'

    # HIDEOUT SERVER, ANIMATED EMOTES ##################################################################################
    DankL = '<a:_:1107481467912736859>'
    SmogeInTheRain = '<a:_:1107481464024608859>'
    KURU = '<a:_:1119329607754203327>'

    # COMMON EMOTES ####################################################################################################
    Offline = '\N{LARGE RED CIRCLE}'
    Online = '\N{LARGE GREEN CIRCLE}'


class Tick(StrEnum):
    yes = '\N{WHITE HEAVY CHECK MARK}'
    no = '\N{CROSS MARK}'
    black = '\N{BLACK LARGE SQUARE}'


# EMOTE LISTS ######################################################################################################
DIGITS = [
    '\N{DIGIT ZERO}\N{COMBINING ENCLOSING KEYCAP}',
    '\N{DIGIT ONE}\N{COMBINING ENCLOSING KEYCAP}',
    '\N{DIGIT TWO}\N{COMBINING ENCLOSING KEYCAP}',
    '\N{DIGIT THREE}\N{COMBINING ENCLOSING KEYCAP}',
    '\N{DIGIT FOUR}\N{COMBINING ENCLOSING KEYCAP}',
    '\N{DIGIT FIVE}\N{COMBINING ENCLOSING KEYCAP}',
    '\N{DIGIT SIX}\N{COMBINING ENCLOSING KEYCAP}',
    '\N{DIGIT SEVEN}\N{COMBINING ENCLOSING KEYCAP}',
    '\N{DIGIT EIGHT}\N{COMBINING ENCLOSING KEYCAP}',
    '\N{DIGIT NINE}\N{COMBINING ENCLOSING KEYCAP}',
]


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
