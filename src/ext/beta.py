# pyright: reportImplicitOverride=false
from __future__ import annotations

from beta_base import *


class BetaTest(BetaCog):
    async def beta_test_task_count_1(self) -> None:  # ty: ignore[missing-override-decorator]
        await asyncio.sleep(10)
        channel = self.bot.hideout.spam

        with measure_time("My long operation"):
            print(await channel.webhooks())

        with measure_time("My long operation"):
            query = "SELECT url FROM webhooks WHERE channel_id = $1"
            webhook_url: str | None = await self.bot.pool.fetchval(query, channel.id)
            wh = (
                discord.Webhook.from_url(webhook_url, client=self.bot, bot_token=self.bot.http.token)
                if webhook_url is not None
                else None
            )
            print(wh)

    @commands.command(name="test", aliases=["beta"])
    async def test(self, ctx: AluContext) -> None:
        await ctx.send("test")


async def setup(bot: AluBot) -> None:
    """Load AluBot extension. Framework of discord.py."""
    await bot.add_cog(BetaTest(bot))
