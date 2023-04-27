import discord

from utils import Ems

from .help import HelpCommandCog
from .other import OtherCog
from .prefix import PrefixSetupCog
from .setup import SetupCommandCog


class Meta(HelpCommandCog, SetupCommandCog, OtherCog, PrefixSetupCog):
    """Commands-utilities related to Discord or the Bot itself."""

    @property
    def help_emote(self) -> discord.PartialEmoji:
        return discord.PartialEmoji.from_str(Ems.FeelsDankManLostHisHat)


async def setup(bot):
    await bot.add_cog(Meta(bot))
