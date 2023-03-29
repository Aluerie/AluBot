from __future__ import annotations

import re
from typing import TYPE_CHECKING

import discord
from discord import app_commands
from discord.ext import commands

if TYPE_CHECKING:
    from utils.bot import AluBot
    from utils.context import Context

from ._base import PersonalBase

JAILED_BOTS_ID = 1090428532162822234


class PersonalCommands(PersonalBase):
    @commands.hybrid_command()
    @app_commands.describe(tweet_ids='Number(-s) in the end of tweet link')
    async def twitter_image(self, ctx: Context, *, tweet_ids: str):
        """Download image from tweets. \
        Useful for Aluerie because Twitter is banned in Russia.
        • `<tweet_ids>` are tweet ids - it's just numbers in the end of tweet links.
        """

        await ctx.typing()

        if not ctx.interaction:
            await ctx.message.edit(suppress=True)

        ids = re.split('; |, |,| ', tweet_ids)
        ids = [t.split('/')[-1].split('?')[0] for t in ids]

        response = await ctx.bot.twitter.get_tweets(
            tweet_ids, media_fields=["url", "preview_image_url"], expansions="attachments.media_keys"
        )
        img_urls = [m.url for m in response.includes['media']]
        # print(img_urls)
        files = await ctx.bot.imgtools.url_to_file(img_urls, return_list=True)
        split_size = 10
        files_10 = [files[x : x + split_size] for x in range(0, len(files), split_size)]
        for fls in files_10:
            await ctx.reply(files=fls)

    @property
    def jailed_bots(self) -> discord.Role:
        return self.hideout.get_role(JAILED_BOTS_ID)  # type: ignore

    @commands.Cog.listener()
    async def on_member_join(self, member: discord.Member):
        if member.guild == self.hideout and member.bot:
            await member.add_roles(self.jailed_bots)
            await member.edit(nick=f"{member.display_name} | ")


async def setup(bot: AluBot):
    await bot.add_cog(PersonalCommands(bot))
