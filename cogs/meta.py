from __future__ import annotations

from typing import TYPE_CHECKING

from discord import Embed, Permissions
from discord.ext import commands
from discord.utils import oauth_url

from .utils.var import Clr, Ems

if TYPE_CHECKING:
    from .utils.bot import AluBot
    from .utils.context import Context


class Meta(commands.Cog):
    """Commands for utilities related to Discord or the Bot itself."""

    def __init__(self, bot: AluBot):
        self.bot: AluBot = bot
        self.help_emote = Ems.FeelsDankManLostHisHat

    @commands.command(aliases=['join'])
    async def invite(self, ctx: Context):
        """
        Show my invite link so you can invite me.
        You can also press discord-native button "Add to Server" in my profile.
        """
        perms = Permissions.all()
        # perms.read_messages = True
        # todo: add all ours properly
        url = oauth_url(self.bot.client_id, permissions=perms)
        em = Embed(title='Invite link for the bot', url=url, description=url, color=Clr.prpl)
        em.set_thumbnail(url=self.bot.user.display_avatar.url)
        await ctx.send(embed=em)


async def setup(bot: AluBot):
    await bot.add_cog(Meta(bot))
