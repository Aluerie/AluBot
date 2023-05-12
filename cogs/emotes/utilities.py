from __future__ import annotations

from typing import TYPE_CHECKING

import discord
from discord.ext import commands

from utils import AluCog, const
from utils.checks import is_owner

if TYPE_CHECKING:
    from utils import AluBot, AluContext


class EmoteUtilitiesCog(AluCog):
    @is_owner()
    @commands.command(name='steal', hidden=True)
    @commands.has_permissions(manage_emojis=True)
    async def steal(self, ctx: AluContext, emoji: discord.PartialEmoji):
        """Add the emote to Hideout Server."""
        emote = await self.hideout.guild.create_custom_emoji(name=emoji.name, image=await emoji.read())
        e = discord.Embed(title='Yoink!', colour=const.MaterialPalette.amber(shade=400))
        e.description = f'Added {emote} to the hideout server.\n`\\{emote}`'
        file = await emoji.to_file()
        e.set_thumbnail(url=f'attachment://{file.filename}')
        await ctx.send(embed=e, file=file)


async def setup(bot: AluBot):
    await bot.add_cog(EmoteUtilitiesCog(bot))
