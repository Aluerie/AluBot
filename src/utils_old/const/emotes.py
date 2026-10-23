"""EMOTE CONSTANTS.

This file contains emote constants in Discord string format.

Notes
-----
* Emotes uploaded to Discord Developer Portal (to the bot's application page, under "Emotes" tab) are preferable to use
    compared to shared guild emotes. As the former can be used everywhere by the bot, while the latter will not work in
    User Installs, some webhooks.
* Unfortunately, YenBot and AluBot do not share their application emojis pools on Discord Developer Portal.
    So emotes uploaded to YenBot DevPortal page aren't accessible by AluBot. Therefore we use a `if platform.system()`
    quirk in this file.
* Keep in mind that for webhooks in order to use application emojis from Discord Developer Portal - those webhooks have
    to be created by the bot.
* Emotes from shared guilds are still fine granted they are not to be used in app installs.
"""

import platform
from enum import StrEnum

# emote names should match discord ones and etc thus:
# ruff: file-ignore[mixed-case-variable-in-class-scope]

__all__ = (
    "Emote",
    "Tick",
)


class AluEmote(StrEnum):
    """Application Emojis uploaded to AluBot's Discord Developer Portal.

    Names match double-colon namings in Discord UI.
    """

    Discord = "<:Discord:1562184459531321445>"
    GitHub = "<:GitHub:1562130860256530482>"


class YenEmote(StrEnum):
    """Application Emojis uploaded to YenBot's Discord Developer Portal.

    Names match double-colon namings in Discord UI.
    """

    Discord = "<:Discord:1562184586333519932>"
    GitHub = "<:GitHub:1562130775501971536>"


Emote = AluEmote if platform.system() != "Windows" else YenEmote


# class Emote(StrEnum):
#     """Common Discord Emotes used by the bot.

#     These emotes are uploaded to discord servers where the bots are members.
#     Names should match double-colon namings in Discord.
#     """

#     # comments mean that this emote is used in help command for something so i don't reuse it by accident

#     ####################
#     # COMMUNITY SERVER #
#     ####################

#     # non animated

#     peepoComfy = "<:peepoComfy:726438781208756288>"  # Category: Community
#     DankApprove = "<:DankApprove:1125591734332706907>"  # has to be from the community guild itself to work in forums

#     ###################
#     # Emote Server #1 #
#     ###################

#     # non animated
#     DankFix = "<:DankFix:1125591737939791963>"  # Category: Jishaku
#     DankG = "<:DankG:1125591639256211596>"
#     DankHatTooBig = "<:DankHatTooBig:1125591656192806922>"
#     DankHey = "<:DankHey:1125591893871448095>"
#     DankLove = "<:DankLove:1125591725931515976>"
#     DankMadgeThreat = "<:DankMadgeThreat:1125591898241892482>"
#     DankZzz = "<:DankZzz:1125591722487984208>"
#     FeelsDankMan = "<:FeelsDankMan:1125591801785503884>"
#     FeelsDankManLostHisHat = "<:FeelsDankManLostHisHat:1125591840427618384>"
#     Jebaited = "<:Jebaited:1125591730163552328>"  # Category: Jebaited
#     Lewd = "<:Lewd:1125591635296796792>"
#     PepoBeliever = "<:PepoBeliever:1125591746265501716>"
#     PepoDetective = "<:PepoDetective:1125591814188044298>"
#     PepoG = "<:PepoG:1125591718373371914>"
#     PepoRules = "<:PepoRules:1125591823348416542>"
#     PogChampPepe = "<:PogChampPepe:1125591805363236934>"
#     Ree = "<:Ree:1125591742712918146>"
#     Smartge = "<:Smartge:1125591827425263617>"
#     WeebsOut = "<:WeebsOut:1125598043455115264>"
#     bedNerdge = "<:bedNerdge:1125591713386352692>"
#     bedWTF = "<:bedWTF:1125591651495194694>"  # Category: Beta
#     bubuAYAYA = "<:bubuAYAYA:1125591624710357013>"
#     bubuChrist = "<:bubuChrist:1125591632268496979>"
#     bubuGun = "<:bubuGun:1125591628996948048>"
#     peepoBlushDank = "<:peepoBlushDank:1125591832240328786>"
#     peepoBusiness = "<:peepoBusiness:1125591642729091113>"
#     peepoHappyDank = "<:peepoHappyDank:1125591819137335304>"
#     peepoMovie = "<:peepoMovie:1125591645853859901>"
#     peepoNiceDay = "<:peepoNiceDay:1125591903488987236>"
#     peepoPolice = "<:peepoPolice:1125591845540462693>"
#     peepoRiot = "<:peepoRiot:1125597699778035713>"
#     peepoRoseDank = "<:peepoRoseDank:1125591890037854299>"
#     peepoStepOnMePls = "<:peepoStepOnMePls:1125591836057145396>"
#     peepoWater = "<:peepoWater:1125720123722973285>"
#     peepoWTF = "<:peepoWTF:1125591659846058035>"
#     peepoRedCard = "<:peepoRedCard:1139905850077626399>"
#     peepoYellowCard = "<:peepoYellowCard:1139908316508729436>"

#     # animated
#     DankL = "<a:DankL:1125591914524184667>"
#     KURU = "<a:KURU:1125591919574138940>"
#     SmogeInTheRain = "<a:SmogeInTheRain:1125591908656361574>"
#     WeebsOutOut = "<a:WeebsOutOut:1125597169957748826>"
#     peepoWeebSmash = "<a:peepoWeebSmash:1125597172675653662>"


class Tick(StrEnum):
    """Tick StrEnum, used to match True/False with yes/no emotes."""

    Yes = "\N{WHITE HEAVY CHECK MARK}"
    No = "\N{CROSS MARK}"
    Black = "\N{BLACK LARGE SQUARE}"
    Question = "\N{WHITE QUESTION MARK ORNAMENT}"
