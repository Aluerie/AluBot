class Ems:
    """Emote strings."""

    # alu server non-animated emotes
    bedNerdge = '<:_:855495407110586439>'
    DankApprove = '<:_:853015071042961468>'
    DankHatTooBig = '<:_:855056297098215474>'
    DankFix = '<:_:924285577027784774>'
    Ree = '<:_:735905686910664797>'
    PepoG = '<:_:930335533970911262>'
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
    Jebaited = '<:_:726450170769703015>'
    peepoNiceDay = '<:_:857224123885158400>'
    DankLove = '<:_:773614700700368927>'

    MadgeThreat = '<:_:854318972102770728>'
    peepoWTF = '<:_:730688500680097862>'
    DankZzz = '<:_:732126852251910144>'

    # alu server ani
    FeelsRainMan = '<a:_:902254223851421796>'
    DankL = '<a:_:1014616758470070353>'

    # wink server non-animated

    github_logo = '<:_:1081677464637550662>'

    bubuSip = '<:_:865033396189921290>'
    bubuGun = '<:_:847805078543007755>'
    bubuChrist = '<:_:847805078769631262>'
    bubuAyaya = '<:_:764835239138164756>'
    slash = '<:_:823159274954817566>'
    TwoBButt = '<:_:853729747846168576>'
    Lewd = '<:_:976604430059331684>'
    DankG = '<:_:998012133948276857>'
    peepoBusiness = '<:_:998157352098340934>'
    peepoMovie = '<:_:998163742741246003>'
    # wink server ani
    # nothing for now

    # general emotes
    Offline = '\N{LARGE RED CIRCLE}'
    Online = '\N{LARGE GREEN CIRCLE}'
    # emotes arrays
    comfy_emotes = [
        "<:peepoComfy:726438781208756288>",
        "<:_:726438781208756288>",
        "<:pepoblanket:595156413974577162>",
        "<:_:595156413974577162>",
    ]
    phone_numbers = [
        '\N{DIGIT ZERO}',
        '\N{DIGIT ONE}',
        '\N{DIGIT TWO}',
        '\N{DIGIT THREE}',
        '\N{DIGIT FOUR}',
        '\N{DIGIT FIVE}',
        '\N{DIGIT SIX}',
        '\N{DIGIT SEVEN}',
        '\N{DIGIT EIGHT}',
        '\N{DIGIT NINE}',
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

    url_link = r"http[s]?://(?:[a-zA-Z]|[0-9]|[$-_@.&+]|[!*(),]|(?:%[0-9a-fA-F][0-9a-fA-F]))+"
    # url_simple = r"(https?://\S+)"


class Img:
    github = 'https://pics.freeicons.io/uploads/icons/png/4381378511600029534-512.png'
    heart = "https://emojipedia-us.s3.dualstack.us-west-1.amazonaws.com/thumbs/120/google/263/purple-heart_1f49c.png"
    twitchtv = (
        "https://cdn3.iconfinder.com/data/icons/"
        "social-messaging-ui-color-shapes-2-free/128/social-twitch-circle-512.png"
    )


class Lmt:
    class Embed:
        sum_all = 6000
        footer_text = 2048
        title = 256
        description = 4096
        field_amount = 25
        field_name = 256
        field_value = 1024
