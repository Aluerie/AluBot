from __future__ import annotations

from typing import TYPE_CHECKING
from urllib import parse as urlparse

from discord import app_commands
from discord.ext import commands

from config import WOLFRAM_TOKEN
from utils import const, errors

from .._base import EducationalCog

if TYPE_CHECKING:
    from bot import AluBot
    from utils import AluContext


class WolframAlphaCog(EducationalCog, emote=const.Emote.bedNerdge):
    """Query Wolfram Alpha within the bot.

    Probably the best computational intelligence service ever.
    [wolframalpha.com](https://www.wolframalpha.com/)
    """

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        base = "https://api.wolframalpha.com/v1"
        self.simple_url = f"{base}/simple?appid={WOLFRAM_TOKEN}&background=black&foreground=white&layout=labelbar&i="
        self.short_url = f"{base}/result?appid={WOLFRAM_TOKEN}&i="

    @commands.hybrid_group(name="wolfram")
    async def wolfram_group(self, ctx: AluContext):
        """WolframAlpha Commands."""
        await ctx.send_help(ctx.command)

    async def wa_long_worker(self, ctx: AluContext, *, query: str):
        await ctx.typing()
        question_url = f"{self.simple_url}{urlparse.quote(query)}"
        file = await self.bot.transposer.url_to_file(question_url, filename="WolframAlpha.png")
        await ctx.reply(content=f"```py\n{query}```", file=file)

    @wolfram_group.command(name="long")
    @commands.cooldown(2, 10, commands.BucketType.user)
    @app_commands.describe(query="Query for WolframAlpha.")
    async def wolfram_long(self, ctx: AluContext, *, query: str):
        """Get a long, detailed image-answer from WolframAlpha."""
        await self.wa_long_worker(ctx, query=query)

    @commands.command(name="wolf")
    @commands.cooldown(2, 10, commands.BucketType.user)
    async def wolfram_long_shortcut(self, ctx: AluContext, *, query: str):
        """Just a txt command shortcut for `wolfram long`."""
        await self.wa_long_worker(ctx, query=query)

    async def wa_short_worker(self, ctx: AluContext, *, query: str):
        await ctx.typing()
        question_url = f"{self.short_url}{urlparse.quote(query)}"
        async with self.bot.session.get(question_url) as response:
            if response.ok:
                await ctx.reply(f"```py\n{query}```{await response.text()}")
            else:
                raise errors.ResponseNotOK(f"Wolfram Response was not ok, Status {response.status},")

    @wolfram_group.command(name="short", aliases=["wa"])
    @commands.cooldown(2, 10, commands.BucketType.user)
    @app_commands.describe(query="Query for WolframAlpha.")
    async def wolfram_short(self, ctx: AluContext, *, query: str):
        """Get a quick, short answer from WolframAlpha."""
        await self.wa_short_worker(ctx, query=query)

    @commands.command(name="wa")
    @commands.cooldown(2, 10, commands.BucketType.user)
    async def wolfram_short_shortcut(self, ctx: AluContext, *, query: str):
        """Just a txt command shortcut for `wolfram short`."""
        await self.wa_short_worker(ctx, query=query)


async def setup(bot: AluBot):
    await bot.add_cog(WolframAlphaCog(bot))
