from __future__ import annotations

import re
from typing import TYPE_CHECKING

import discord
from discord import app_commands
from discord.ext import commands

from utils import AluCog

if TYPE_CHECKING:
    from utils import AluBot, AluContext


class PersonalCommands(AluCog):
    @commands.hybrid_command()
    @app_commands.describe(tweet_ids='Number(-s) in the end of tweet link')
    async def twitter_image(self, ctx: AluContext, *, tweet_ids: str):
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

    @commands.Cog.listener()
    async def on_member_join(self, member: discord.Member):
        if member.guild == self.bot.hideout.guild and member.bot:
            await member.add_roles(self.bot.hideout.jailed_bots)
            await member.edit(nick=f"{member.display_name} | ")


async def setup(bot: AluBot):
    await bot.add_cog(PersonalCommands(bot))
