from __future__ import annotations
from typing import TYPE_CHECKING

import discord
from discord.ext import commands, tasks

from .utils.var import Cid, Clr, Ems

if TYPE_CHECKING:
    from .utils.bot import AluBot
    from .utils.context import Context


class Meta(commands.Cog):
    """Commands for utilities related to Discord or the Bot itself."""

    def __init__(self, bot: AluBot):
        self.bot: AluBot = bot

    @property
    def help_emote(self) -> discord.PartialEmoji:
        return discord.PartialEmoji.from_str(Ems.FeelsDankManLostHisHat)

    async def cog_load(self) -> None:
        self.reload_info.start()

    async def cog_unload(self) -> None:
        self.reload_info.cancel()

    @commands.command(aliases=['join'])
    async def invite(self, ctx: Context):
        """Show my invite link so you can invite me.
        You can also press discord-native button "Add to Server" in my profile.
        """
        perms = discord.Permissions.all()
        # perms.read_messages = True
        url = discord.utils.oauth_url(self.bot.client_id, permissions=perms)
        e = discord.Embed(title='Invite link for the bot', url=url, description=url, color=Clr.prpl)
        e.set_thumbnail(url=self.bot.user.display_avatar.url)
        await ctx.reply(embed=e)

    @tasks.loop(count=1)
    async def reload_info(self):
        e = discord.Embed(colour=Clr.prpl, description=f'Logged in as {self.bot.user}')
        await self.bot.get_channel(Cid.spam_me).send(embed=e)
        self.bot.help_command.cog = self  # show help command in there
        if not self.bot.test:
            # em.set_author(name='Finished updating/rebooting')
            await self.bot.get_channel(Cid.bot_spam).send(embed=e)

    @reload_info.before_loop
    async def before(self):
        await self.bot.wait_until_ready()


async def setup(bot: AluBot):
    await bot.add_cog(Meta(bot))
