import discord

from utils.const import Emote

from .feedback import FeedbackCog
from .help import AluHelpCog
from .other import OtherCog
from .prefix import PrefixSetupCog
from .setup_cog import SetupCommandCog


class Meta(AluHelpCog, SetupCommandCog, OtherCog, FeedbackCog, PrefixSetupCog):
    """Commands-utilities related to Discord or the Bot itself."""

    @property
    def help_emote(self) -> discord.PartialEmoji:
        return discord.PartialEmoji.from_str(Emote.FeelsDankManLostHisHat)


async def setup(bot):
    await bot.add_cog(Meta(bot))