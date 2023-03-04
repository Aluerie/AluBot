import imp
import discord

from .dev_utils import DevUtilities

from utils.var import Ems

class Utilities(
    DevUtilities,
):
    """
    Utilities
    """

    @property
    def help_emote(self) -> discord.PartialEmoji:
        # todo: different emote - this one is taken
        return discord.PartialEmoji.from_str(Ems.FeelsDankManLostHisHat)