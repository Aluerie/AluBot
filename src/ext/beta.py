# ruff: noqa: D100, D101, D102, D103, T200, T201, F841
# pyright: reportImplicitOverride=false
from __future__ import annotations

from examples.beta.base import *


class BetaTest(BetaCog):
    @aluloop(count=1)
    async def beta_task(self) -> None:
        url = "https://na1.api.riotgames.com/riot/account/v1/accounts/by-puuid/8201ytXCZ3e2n8PmrFoFa2_zdnxZW1OuQtCEDnhvF5tpbnLokVGVAz6Hq9TLWBODX-FQBUB1CNiGVA"
        headers = {"X-Riot-Token": config['TOKENS']['RIOT']}
        async with self.bot.session.get(
            url,
            headers=headers,
        ) as resp:
            return await resp.json()



async def setup(bot: AluBot) -> None:
    """Load AluBot extension. Framework of discord.py."""
    await bot.add_cog(BetaTest(bot))
