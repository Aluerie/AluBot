from __future__ import annotations
from typing import TYPE_CHECKING

from io import BytesIO
from urllib import parse as urlparse

import discord
from discord import app_commands
from discord.ext import commands

from config import WOLFRAM_TOKEN
from utils.var import Ems

if TYPE_CHECKING:
    from utils.bot import AluBot
    from utils.context import Context


class WolframAlpha(commands.Cog):
    """Query Wolfram Alpha within the bot.

    Probably the best computational intelligence service ever.
    [wolframalpha.com](https://www.wolframalpha.com/)
    """

    def __init__(self, bot: AluBot):
        self.bot: AluBot = bot
        self.wa_basic_url = (
            f'https://api.wolframalpha.com/v1/simple?appid={WOLFRAM_TOKEN}' 
            f'&background=black&foreground=white&layout=labelbar&i='
        )
        self.wa_short_url = f"https://api.wolframalpha.com/v1/result?appid={WOLFRAM_TOKEN}&i="

    @property
    def help_emote(self) -> discord.PartialEmoji:
        return discord.PartialEmoji.from_str(Ems.bedNerdge)

    @commands.hybrid_command(
        name="wolfram_long",
        description="Get long answer from WolframAlpha.com",
        aliases=["wolfram", "wolf"],
    )
    @commands.cooldown(2, 10, commands.BucketType.user)
    @app_commands.describe(query='Query for WolframAlpha')
    async def wolf(self, ctx: Context, *, query: str):
        """Get answer from WolframAlpha"""
        await ctx.typing()
        question_url = f'{self.wa_basic_url}{urlparse.quote(query)}'
        async with self.bot.session.get(question_url) as resp:
            await ctx.reply(
                content=f"```py\n{query}```",
                file=discord.File(
                    fp=BytesIO(await resp.read()),
                    filename="WolframAlpha.png"
                )
            )

    @commands.hybrid_command(
        name="wolfram_short",
        description="Get short answer from WolframAlpha.com",
        aliases=['wa']
    )
    @commands.cooldown(2, 10, commands.BucketType.user)
    @app_commands.describe(query='Query for WolframAlpha')
    async def wolfram_shorter(self, ctx: Context, *, query: str):
        """Get shorter answer from WolframAlpha"""
        await ctx.typing()
        question_url = f'{self.wa_short_url}{urlparse.quote(query)}'
        async with self.bot.session.get(question_url) as resp:
            await ctx.reply(f"```py\n{query}```{await resp.text()}")


async def setup(bot: AluBot):
    await bot.add_cog(WolframAlpha(bot))
