from discord import File, option
from discord.ext import commands, bridge

from utils.var import *

from io import BytesIO
from urllib import parse as urlparse
from os import getenv
WOLFRAM_TOKEN = getenv("WOLFRAM_TOKEN")
print(WOLFRAM_TOKEN)


class WolframAlpha(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.WABASICURL = str(
            "http://api.wolframalpha.com/v1/simple?appid=" + WOLFRAM_TOKEN +
            "&background=black&foreground=white&layout=labelbar" + "&i=")
        self.WASHORTURL = str("http://api.wolframalpha.com/v1/result?appid=" + WOLFRAM_TOKEN + "&i=")
        self.help_category = 'Tools'

    @bridge.bridge_command(
        name="wolf",
        brief=Ems.slash,
        aliases=["wolfram"],
        description="Get long answer from WolframAlpha"
    )
    @option('query', description='Query for WolframAlpha')
    @commands.cooldown(2, 10, commands.BucketType.user)
    async def wolf(self, ctx, *, query: str):
        """Get answer from WolframAlpha ;"""
        questionurl = str(self.WABASICURL + str(urlparse.quote(query)))
        async with self.bot.ses.get(questionurl) as resp:
            if (content := await resp.read()) == "Error 1: Invalid appid":
                result = "Sorry! The bot has wrong appid"
                file = None
            else:
                result = f"```python\n{query}```"
                file = File(fp=BytesIO(content), filename="WolframAlpha.png")
            await ctx.respond(content=result, file=file)

    @bridge.bridge_command(
        name="wa",
        brief=Ems.slash,
        description="Get short answer from WolframAlpha"
    )
    @option('query', description='Query for WolframAlpha')
    @commands.cooldown(2, 10, commands.BucketType.user)
    async def wolfram_shorter(self, ctx, *, query: str):
        """Get shorter answer from WolframAlpha ;"""
        questionurl = str(self.WASHORTURL + str(urlparse.quote(query)))
        async with self.bot.ses.get(questionurl) as resp:
            if await resp.read() == "Error 1: Invalid appid":
                result = "Sorry! The bot has wrong appid"
            else:
                result = f"```python\n{query}```"
                result += await resp.text()
            await ctx.respond(content=result)


def setup(bot):
    bot.add_cog(WolframAlpha(bot))
