import discord

from utils.var import Ems

from .other import OtherCog
from .help import HelpCommandCog
from .setup import SetupCommandCog
from .prefix import PrefixSetupCog


class Meta(HelpCommandCog, SetupCommandCog, OtherCog, PrefixSetupCog):
    """Commands-utilities related to Discord or the Bot itself."""

    @property
    def help_emote(self) -> discord.PartialEmoji:
        return discord.PartialEmoji.from_str(Ems.FeelsDankManLostHisHat)


async def setup(bot):
    await bot.add_cog(Meta(bot))
