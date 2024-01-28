from __future__ import annotations

from typing import TYPE_CHECKING, Union

import discord
from discord import app_commands
from discord.ext import commands

from utils import AluGuildContext, const, errors

from ._base import DevBaseCog

if TYPE_CHECKING:
    from bot import AluBot


class DeveloperUtilities(DevBaseCog):
    @commands.guild_only()
    @commands.command()
    async def yoink(self, ctx: AluGuildContext, emote: Union[discord.PartialEmoji, str]):
        """Yoink emote from current server to one of my emote servers for the bot.

        This is used to reduce annoyance of opening another account, copying files and copying id.
        """

        async def add_new_emote_to_emote_guilds(emote_to_yoink: Union[discord.PartialEmoji, discord.Emoji]):
            for guild_id in const.EMOTE_GUILDS:
                guild = self.bot.get_guild(guild_id)
                if guild is None:
                    raise errors.SomethingWentWrong("One of `EMOTE_GUILDS` is None")
                try:
                    new_emote = await guild.create_custom_emoji(
                        name=emote_to_yoink.name,
                        image=await emote_to_yoink.read(),
                    )
                except Exception:
                    continue
                else:
                    answer = f"```py\n{new_emote.name} = '{new_emote}'```"
                    e = discord.Embed(title="Emote yoinked")
                    e.set_thumbnail(url=new_emote.url)
                    await ctx.reply(answer, embed=e)
                    return
            raise errors.SomethingWentWrong("We failed to add the emote to any of `EMOTE_GUILDS`")

        if isinstance(emote, discord.PartialEmoji):
            await add_new_emote_to_emote_guilds(emote)

        # apparently discord.PartialEmoji.from_str only accepts `name:id` formats
        # which is a problem for us since we can't use animated emojis being a nitro pleb
        # so we have to do the conversion ourselves

        else:  # emote is str then and we need to find it manually
            for emo in ctx.guild.emojis:
                if emo.name == emote:
                    # it's just first occurrence so be mindful about same names
                    await add_new_emote_to_emote_guilds(emo)


async def setup(bot: AluBot):
    await bot.add_cog(DeveloperUtilities(bot))
