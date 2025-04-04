"""EMOTE CONSTANTS.

This file contains emote constants in Discord string format.
These emotes are hosted in my emote servers (why not on discord dev portal - explained below).

Notes
-----
* Unfortunately, as of today (13/October/2024) uploading emotes to the bot page on discord developer portal
    has some severe disadvantages compared to having many emote servers:
    1. Webhooks cannot utilize them (even with @everybody having "Use external emojis" permission) - just sends :emote:
    2. Then we have to upload same emote twice - once to AluBot page, once to YenBot page
    3. And we have to list the emotes twice and have some kind of global namespace variable for it - kinda bad.
        (as in emotes = YENBOT_EMOTES if TEST_BOT_TOKEN else ALUBOT_EMOTES) where TEST_BOT_TOKEN is a global var.
    # TODO: after 13/October/2025 - check if now it's possible to use bot emotes from dev portal in webhooks.
"""

from enum import StrEnum

# emote names should match discord ones and etc thus:
# ruff: noqa: N815


class Emote(StrEnum):
    """Emote strings.

    Names should match namings for discord emotes they represent.
    """

    # comments mean that this emote is used in help command for something so i don't reuse it by accident

    #########################################
    # COMMUNITY SERVER, NON-ANIMATED EMOTES #
    #########################################
    peepoComfy = "<:_:726438781208756288>"  # Category: Community
    UpvoteSuggestion = "<:DankApprove:853015071042961468>"  # it has to be from the community guild itself

    ##################
    # Emote Server 1 #
    ##################

    # non animated
    DankApprove = "<:DankApprove:1125591734332706907>"
    DankFix = "<:DankFix:1125591737939791963>"  # Category: Jishaku
    DankG = "<:DankG:1125591639256211596>"
    DankHatTooBig = "<:DankHatTooBig:1125591656192806922>"
    DankHey = "<:DankHey:1125591893871448095>"
    DankLove = "<:DankLove:1125591725931515976>"
    DankMadgeThreat = "<:DankMadgeThreat:1125591898241892482>"
    DankZzz = "<:DankZzz:1125591722487984208>"
    FeelsDankMan = "<:FeelsDankMan:1125591801785503884>"
    FeelsDankManLostHisHat = "<:FeelsDankManLostHisHat:1125591840427618384>"
    Jebaited = "<:Jebaited:1125591730163552328>"  # Category: Jebaited
    Lewd = "<:Lewd:1125591635296796792>"
    PepoBeliever = "<:PepoBeliever:1125591746265501716>"
    PepoDetective = "<:PepoDetective:1125591814188044298>"
    PepoG = "<:PepoG:1125591718373371914>"
    PepoRules = "<:PepoRules:1125591823348416542>"
    PogChampPepe = "<:PogChampPepe:1125591805363236934>"
    Ree = "<:Ree:1125591742712918146>"
    Smartge = "<:Smartge:1125591827425263617>"
    WeebsOut = "<:WeebsOut:1125598043455115264>"
    bedNerdge = "<:bedNerdge:1125591713386352692>"
    bedWTF = "<:bedWTF:1125591651495194694>"  # Category: Beta
    bubuAYAYA = "<:bubuAYAYA:1125591624710357013>"
    bubuChrist = "<:bubuChrist:1125591632268496979>"
    bubuGun = "<:bubuGun:1125591628996948048>"
    peepoBlushDank = "<:peepoBlushDank:1125591832240328786>"
    peepoBusiness = "<:peepoBusiness:1125591642729091113>"
    peepoHappyDank = "<:peepoHappyDank:1125591819137335304>"
    peepoMovie = "<:peepoMovie:1125591645853859901>"
    peepoNiceDay = "<:peepoNiceDay:1125591903488987236>"
    peepoPolice = "<:peepoPolice:1125591845540462693>"
    peepoRiot = "<:peepoRiot:1125597699778035713>"
    peepoRoseDank = "<:peepoRoseDank:1125591890037854299>"
    peepoStepOnMePls = "<:peepoStepOnMePls:1125591836057145396>"
    peepoWater = "<:peepoWater:1125720123722973285>"
    peepoWTF = "<:peepoWTF:1125591659846058035>"
    peepoRedCard = "<:peepoRedCard:1139905850077626399>"
    peepoYellowCard = "<:peepoYellowCard:1139908316508729436>"

    # animated
    DankL = "<a:DankL:1125591914524184667>"
    KURU = "<a:KURU:1125591919574138940>"
    SmogeInTheRain = "<a:SmogeInTheRain:1125591908656361574>"
    WeebsOutOut = "<a:WeebsOutOut:1125597169957748826>"
    peepoWeebSmash = "<a:peepoWeebSmash:1125597172675653662>"

    #################
    # COMMON EMOTES #
    #################

    Offline = "\N{LARGE RED CIRCLE}"
    Online = "\N{LARGE GREEN CIRCLE}"


class Tick(StrEnum):
    """Tick StrEnum, used to match True/False with yes/no emotes."""

    Yes = "\N{WHITE HEAVY CHECK MARK}"
    No = "\N{CROSS MARK}"
    Black = "\N{BLACK LARGE SQUARE}"
    Question = "\N{WHITE QUESTION MARK ORNAMENT}"


DIGITS = [
    "\N{DIGIT ZERO}\N{COMBINING ENCLOSING KEYCAP}",
    "\N{DIGIT ONE}\N{COMBINING ENCLOSING KEYCAP}",
    "\N{DIGIT TWO}\N{COMBINING ENCLOSING KEYCAP}",
    "\N{DIGIT THREE}\N{COMBINING ENCLOSING KEYCAP}",
    "\N{DIGIT FOUR}\N{COMBINING ENCLOSING KEYCAP}",
    "\N{DIGIT FIVE}\N{COMBINING ENCLOSING KEYCAP}",
    "\N{DIGIT SIX}\N{COMBINING ENCLOSING KEYCAP}",
    "\N{DIGIT SEVEN}\N{COMBINING ENCLOSING KEYCAP}",
    "\N{DIGIT EIGHT}\N{COMBINING ENCLOSING KEYCAP}",
    "\N{DIGIT NINE}\N{COMBINING ENCLOSING KEYCAP}",
]


class GitIssueEvent(StrEnum):
    """Emotes to showcase GitHub Issue Events with."""

    # pictures are taken from 16px versions here https://primer.style/octicons/
    # and background circles are added with a simple online editor https://iconscout.com/color-editor
    # make pics to be 128x128, so it's consistent for all sizes
    # =========================================================
    # Emotes from B1-50 extra emote server, names match GitHub event names (and emote names)
    # events
    reopened = "<:reopened:1125588760269164587>"
    opened = "<:opened:1125588763087753307>"
    closed = "<:closed:1125588765759508552>"
    # comments
    assigned = "<:assigned:1125588768070578196>"
    commented = "<:commented:1125588770679431258>"


class EmoteLogo(StrEnum):
    """Emotes to showcase some logos with."""

    # Emotes from BXX extra emote servers, names match emote names in those servers (try to keep them PascalCase)
    GitHub = "<:GitHub:1125588758197178439>"
    AluerieServer = "<:AluerieServer:1125600089109442661>"
