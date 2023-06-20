from __future__ import annotations

from io import BytesIO
from typing import TYPE_CHECKING
from urllib import parse as urlparse

import discord
from discord import app_commands
from discord.ext import commands

from config import WOLFRAM_TOKEN
from utils import AluCog, const

if TYPE_CHECKING:
    from utils import AluBot, AluContext


class WolframAlpha(AluCog, emote=const.Emote.bedNerdge):
    """Query Wolfram Alpha within the bot.

    Probably the best computational intelligence service ever.
    [wolframalpha.com](https://www.wolframalpha.com/)
    """

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        base = 'https://api.wolframalpha.com/v1'
        self.simple_url = f'{base}/simple?appid={WOLFRAM_TOKEN}&background=black&foreground=white&layout=labelbar&i='
        self.short_url = f"{base}/result?appid={WOLFRAM_TOKEN}&i="

    @commands.hybrid_command(
        name="wolfram_long",
        description="Get long answer from WolframAlpha.com",
        aliases=["wolfram", "wolf"],
    )
    @commands.cooldown(2, 10, commands.BucketType.user)
    @app_commands.describe(query='Query for WolframAlpha')
    async def wolf(self, ctx: AluContext, *, query: str):
        """Get answer from WolframAlpha"""
        await ctx.typing()
        question_url = f'{self.simple_url}{urlparse.quote(query)}'
        async with self.bot.session.get(question_url) as resp:
            await ctx.reply(
                content=f"```py\n{query}```",
                file=discord.File(fp=BytesIO(await resp.read()), filename="WolframAlpha.png"),
            )

    @commands.hybrid_command(name="wolfram_short", description="Get short answer from WolframAlpha.com", aliases=['wa'])
    @commands.cooldown(2, 10, commands.BucketType.user)
    @app_commands.describe(query='Query for WolframAlpha')
    async def wolfram_shorter(self, ctx: AluContext, *, query: str):
        """Get shorter answer from WolframAlpha"""
        await ctx.typing()
        question_url = f'{self.short_url}{urlparse.quote(query)}'
        async with self.bot.session.get(question_url) as resp:
            await ctx.reply(f"```py\n{query}```{await resp.text()}")


async def setup(bot: AluBot):
    await bot.add_cog(WolframAlpha(bot))
