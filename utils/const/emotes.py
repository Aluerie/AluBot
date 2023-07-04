from enum import StrEnum


class Emote(StrEnum):
    """Emote strings."""

    # comments mean that this emote is used in help command for something so i don't reuse it by accident

    # COMMUNITY SERVER, NON-ANIMATED EMOTES ############################################################################
    peepoComfy = '<:_:726438781208756288>'  # Category: Community

    # Emote Server 1

    # non animated
    DankApprove = '<:DankApprove:1125591734332706907>'
    DankFix = '<:DankFix:1125591737939791963>'  # Category: Jishaku
    DankG = '<:DankG:1125591639256211596>'
    DankHatTooBig = '<:DankHatTooBig:1125591656192806922>'
    DankHey = '<:DankHey:1125591893871448095>'
    DankLove = '<:DankLove:1125591725931515976>'
    DankMadgeThreat = '<:DankMadgeThreat:1125591898241892482>'
    DankZzz = '<:DankZzz:1125591722487984208>'
    FeelsDankMan = '<:FeelsDankMan:1125591801785503884>'
    FeelsDankManLostHisHat = '<:FeelsDankManLostHisHat:1125591840427618384>'
    Jebaited = '<:Jebaited:1125591730163552328>'  # Category: Jebaited
    Lewd = '<:Lewd:1125591635296796792>'
    PepoBeliever = '<:PepoBeliever:1125591746265501716>'
    PepoDetective = '<:PepoDetective:1125591814188044298>'
    PepoG = '<:PepoG:1125591718373371914>'
    PepoRules = '<:PepoRules:1125591823348416542>'
    PogChampPepe = '<:PogChampPepe:1125591805363236934>'
    Ree = '<:Ree:1125591742712918146>'
    Smartge = '<:Smartge:1125591827425263617>'
    WeebsOut = '<:WeebsOut:1125598043455115264>'
    bedNerdge = '<:bedNerdge:1125591713386352692>'
    bedWTF = '<:bedWTF:1125591651495194694>'  # Category: Beta
    bubuAYAYA = '<:bubuAYAYA:1125591624710357013>'
    bubuChrist = '<:bubuChrist:1125591632268496979>'
    bubuGun = '<:bubuGun:1125591628996948048>'
    peepoBlushDank = '<:peepoBlushDank:1125591832240328786>'
    peepoBusiness = '<:peepoBusiness:1125591642729091113>'
    # peepoComfy = '<:peepoComfy:1125591750665318420>' # we will use the one from community
    peepoHappyDank = '<:peepoHappyDank:1125591819137335304>'
    peepoMovie = '<:peepoMovie:1125591645853859901>'
    peepoNiceDay = '<:peepoNiceDay:1125591903488987236>'
    peepoPolice = '<:peepoPolice:1125591845540462693>'
    peepoRiot = '<:peepoRiot:1125597699778035713>'
    peepoRoseDank = '<:peepoRoseDank:1125591890037854299>'
    peepoStepOnMePls = '<:peepoStepOnMePls:1125591836057145396>'
    peepoWTF = '<:peepoWTF:1125591659846058035>'

    # animated
    DankL = '<a:DankL:1125591914524184667>'
    KURU = '<a:KURU:1125591919574138940>'
    SmogeInTheRain = '<a:SmogeInTheRain:1125591908656361574>'
    WeebsOutOut = '<a:WeebsOutOut:1125597169957748826>'
    peepoWeebSmash = '<a:peepoWeebSmash:1125597172675653662>'

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


class GitIssueEvent(StrEnum):
    # pictures are taken from 16px versions here https://primer.style/octicons/
    # and background circles are added with simple online editor https://iconscout.com/color-editor
    # make pics to be 128x128, so it's consistent for all sizes
    reopened = '<:reopened:1125588760269164587>'
    opened = '<:opened:1125588763087753307>'
    closed = '<:closed:1125588765759508552>'
    assigned = '<:assigned:1125588768070578196>'
    commented = '<:commented:1125588770679431258>'


class EmoteLogo(StrEnum):
    github_logo = '<:github_logo:1125588758197178439>'
    AluerieServer = '<:AluerieServer:1125600089109442661>'
