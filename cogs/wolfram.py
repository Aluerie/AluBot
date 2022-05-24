from __future__ import annotations
from typing import TYPE_CHECKING

from io import BytesIO
from urllib import parse as urlparse
from os import getenv

from discord import app_commands, File
from discord.ext import commands

from utils.var import Ems


if TYPE_CHECKING:
    from utils.context import Context


WOLFRAM_TOKEN = getenv("WOLFRAM_TOKEN")


class WolframAlpha(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.wa_basic_url = \
            f'https://api.wolframalpha.com/v1/simple?appid={WOLFRAM_TOKEN}' \
            f'&background=black&foreground=white&layout=labelbar&i='
        self.wa_short_url = f"https://api.wolframalpha.com/v1/result?appid={WOLFRAM_TOKEN}&i="
        self.help_category = 'Tools'

    @commands.hybrid_command(
        name="wolfram_long",
        brief=Ems.slash,
        description="Get long answer from WolframAlpha.com",
        aliases=["wolfram", "wolf"],
    )
    @commands.cooldown(2, 10, commands.BucketType.user)
    @app_commands.describe(query='Query for WolframAlpha')
    async def wolf(self, ctx: Context, *, query: str):
        """Get answer from WolframAlpha ;"""
        await ctx.typing()
        questionurl = str(self.wa_basic_url + str(urlparse.quote(query)))
        async with self.bot.ses.get(questionurl) as resp:
            if (content := await resp.read()) == "Error 1: Invalid appid":
                result = "Sorry! The bot has wrong appid"
                file = None
            else:
                result = f"```py\n{query}```"
                file = File(fp=BytesIO(content), filename="WolframAlpha.png")
            await ctx.reply(content=result, file=file)

    @commands.hybrid_command(
        name="wolfram_short",
        brief=Ems.slash,
        description="Get short answer from WolframAlpha.com",
        aliases=['wa']
    )
    @commands.cooldown(2, 10, commands.BucketType.user)
    @app_commands.describe(query='Query for WolframAlpha')
    async def wolfram_shorter(self, ctx: Context, *, query: str):
        """Get shorter answer from WolframAlpha ;"""
        await ctx.typing()
        questionurl = str(self.wa_short_url + str(urlparse.quote(query)))
        async with self.bot.ses.get(questionurl) as resp:
            if await resp.read() == "Error 1: Invalid appid":
                result = "Sorry! The bot has wrong appid"
            else:
                result = f"```py\n{query}```"
                result += await resp.text()
            await ctx.reply(content=result)


async def setup(bot):
    await bot.add_cog(WolframAlpha(bot))
