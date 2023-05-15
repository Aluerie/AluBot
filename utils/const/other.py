from enum import IntEnum, StrEnum


class Emote(StrEnum):
    """Emote strings."""

    # COMMUNITY SERVER, NON-ANIMATED EMOTES ############################################################################
    Ree = '<:_:735905686910664797>'
    PepoBeliever = '<:_:730887642404618314>'
    peepoComfy = '<:_:726438781208756288>'
    FeelsDankMan = '<:_:726441255805911120>'
    PogChampPepe = '<:_:785600902140526642>'
    PepoDetective = '<:_:743988423500628102>'
    peepoHappyDank = '<:_:852928248953831514>'
    peepoRose = '<:_:856262331666923580>'
    PepoRules = '<:_:772399483039907860>'
    Smartge = '<:_:869075184445956156>'
    peepoWave = '<:_:856262331217346571>'
    peepoBlushDank = '<:_:853744336214032384>'
    peepoPlsStepOnMe = '<:_:761174324420935722>'
    FeelsDankManLostHisHat = '<:_:852976573929095198>'

    peepoPolice = '<:_:960004884235690024>'
    
    peepoNiceDay = '<:_:857224123885158400>'

    MadgeThreat = '<:_:854318972102770728>'

    # COMMUNITY SERVER, ANIMATED EMOTES ################################################################################
    FeelsRainMan = '<a:_:902254223851421796>'
    DankL = '<a:_:1014616758470070353>'

    # HIDEOUT SERVER, NON-ANIMATED EMOTES ##############################################################################
    
    bedNerdge = '<:_:1106748389565153300:>'
    bubuAyaya = '<:_:764835239138164756>'
    bubuChrist = '<:_:847805078769631262>'
    bubuGun = '<:_:847805078543007755>'
    bubuSip = '<:_:865033396189921290>'
    DankApprove = '<:_:1107470723448057886:>'
    DankFix = '<:_:1107470989895417897:>'
    DankG = '<:_:998012133948276857>'
    DankHatTooBig = '<:_:1106645924974972978>'
    DankLove = '<:_:1107467504290385950:>'
    DankZzz = '<:_:1107467287398723656:>'
    github_logo = '<:_:1081677464637550662>'
    Jebaited = '<:_:1107467775749914644:>'
    Lewd = '<:_:976604430059331684>'
    peepoBusiness = '<:_:998157352098340934>'
    peepoMovie = '<:_:998163742741246003>'
    peepoWTF = '<:_:1106723199128965140>'
    PepoG = '<:_:1106749219181699082:>'
    bedWTF = '<:_:999813662036459610>'
    slash = '<:_:823159274954817566>'
    TwoBButt = '<:_:853729747846168576>'
    # HIDEOUT SERVER, ANIMATED EMOTES ##################################################################################
    # nothing for now

    # COMMON EMOTES ####################################################################################################
    Offline = '\N{LARGE RED CIRCLE}'
    Online = '\N{LARGE GREEN CIRCLE}'


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
    whitespace = r"\s"  # whitespaces
    emote = r"<(?P<animated>a?):(?P<name>[a-zA-Z0-9_]{2,32}):(?P<id>[0-9]{18,22})>"  # emotes
    nqn = r":(?P<name>[a-zA-Z0-9_]{2,32}):"  # standard emotes
    # emoji = get_emoji_regexp() # use from emoji import get_emoji_regexp for this
    bug_check = r":.*:"
    emote_stats = r"<a?:[a-zA-Z0-9_]{2,32}:[0-9]{18,22}>"
    emote_stats_ids = r"<a?:[a-zA-Z0-9_]{2,32}:([0-9]{18,22})>"
    invis = "[^!-~]+"  # IDK might be huge question mark


REGEX_URL_LINK = r"http[s]?://(?:[a-zA-Z]|[0-9]|[$-_@.&+]|[!*(),]|(?:%[0-9a-fA-F][0-9a-fA-F]))+"


class Picture(StrEnum):
    github = 'https://pics.freeicons.io/uploads/icons/png/4381378511600029534-512.png'
    heart = "https://emojipedia-us.s3.dualstack.us-west-1.amazonaws.com/thumbs/120/google/263/purple-heart_1f49c.png"
    twitch = (
        "https://cdn3.iconfinder.com/data/icons/"
        "social-messaging-ui-color-shapes-2-free/128/social-twitch-circle-512.png"
    )


class Limit:
    class Embed:
        sum_all = 6000
        footer_text = 2048
        title = 256
        description = 4096
        field_amount = 25
        field_name = 256
        field_value = 1024
