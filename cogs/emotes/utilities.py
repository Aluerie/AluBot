from __future__ import annotations

import re
from typing import TYPE_CHECKING

import discord
from discord import app_commands
from discord.ext import commands

from utils import AluCog, const
from utils.checks import is_owner

if TYPE_CHECKING:
    from utils import AluBot, AluContext


class EmoteUtilitiesCog(AluCog):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

    # idk doesn't seem like a good idea

    #     self.emote_context_menu = app_commands.ContextMenu(
    #         name="Get emote files to steal", callback=self.get_emote_files_to_steal
    #     )

    # def cog_load(self) -> None:
    #     # self.bot.tree.add_command(self.emote_context_menu)
    #     pass

    # async def get_emote_files_to_steal(self, ntr: discord.Interaction, message: discord.Message):
    #     # await ntr.response.defer()
    #     emote_regex = r"(<a?:[a-zA-Z0-9_]{2,32}:[0-9]{18,22}>)"
    #     emojis = re.findall(emote_regex, message.content)
    #     emojis = list(dict.fromkeys(emojis))
    #     partial_emojis = [discord.PartialEmoji.from_str(x) for x in emojis[:10]]
    #     emoji_urls = [x.url for x in partial_emojis]
    #     emoji_names = [f"{x.name}.{'.gif' if x.animated else 'png'}" for x in partial_emojis]

    #     files = await self.bot.imgtools.url_to_file(url=emoji_urls, filename=emoji_names, return_list=True)
    #     # TODO: same name problem ?
    #     embeds = [
    #         discord.Embed(colour=const.MaterialPalette.amber(shade=400), description=f'`:{pe.name}:`').set_thumbnail(
    #             url=f'attachment://{f.filename}'
    #         )
    #         for f, pe in zip(files, partial_emojis)
    #     ]

    #     await ntr.response.send_message(embeds=embeds, files=files, ephemeral=True)
    #     # await ntr.followup.send(embed=e, files=files)

    @commands.command(name='steal', hidden=True)
    async def steal(self, ctx: AluContext, emotes: commands.Greedy[discord.PartialEmoji]):
        """Add the emote to Hideout Server."""
        es = [await self.hideout.guild.create_custom_emoji(name=e.name, image=await e.read()) for e in emotes]
        code = '\n'.join([f'{emote.name} = \'<{"a" if emote.animated else ""}:_:{emote.id}:>\'' for emote in es])
        await ctx.reply(f'```\n{code}```')


async def setup(bot: AluBot):
    await bot.add_cog(EmoteUtilitiesCog(bot))
