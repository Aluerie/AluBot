from __future__ import annotations

from typing import TYPE_CHECKING, Any
from urllib import parse as urlparse

from discord import app_commands

from bot import AluCog
from config import config
from utils import errors

if TYPE_CHECKING:
    from bot import AluBot, AluInteraction

__all__ = ("WolframAlpha",)


class WolframAlpha(AluCog):
    """Query Wolfram Alpha within the bot.

    Probably the best computational intelligence service ever.
    [wolframalpha.com](https://www.wolframalpha.com/)
    """

    def __init__(self, *args: Any, **kwargs: Any) -> None:
        super().__init__(*args, **kwargs)
        base = "https://api.wolframalpha.com/v1"
        wolfram_token = config["TOKENS"]["WOLFRAM"]
        self.simple_url = f"{base}/simple?appid={wolfram_token}&background=black&foreground=white&layout=labelbar&i="
        self.short_url = f"{base}/result?appid={wolfram_token}&i="

    wolfram_group = app_commands.Group(
        name="wolfram",
        description="WolframAlpha queries.",
    )

    @wolfram_group.command(name="long")
    @app_commands.checks.cooldown(1, 60.0, key=lambda i: (i.guild_id, i.user.id))
    async def wolfram_long(self, interaction: AluInteraction, query: str) -> None:
        """Get a long, detailed image-answer from WolframAlpha.

        Parameters
        ----------
        query : str
            Query for WolframAlpha.
        """
        await interaction.response.defer()
        question_url = f"{self.simple_url}{urlparse.quote(query)}"
        file = await self.bot.transposer.url_to_file(question_url, filename="WolframAlpha.png")
        await interaction.followup.send(content=f"```py\n{query}```", file=file)

    @wolfram_group.command(name="short")
    @app_commands.checks.cooldown(1, 60.0, key=lambda i: (i.guild_id, i.user.id))
    async def wolfram_short(self, interaction: AluInteraction, query: str) -> None:
        """Get a quick, short answer from WolframAlpha.

        Parameters
        ----------
        query: str
            Query for WolframAlpha.
        """
        await interaction.response.defer()
        question_url = f"{self.short_url}{urlparse.quote(query)}"
        async with self.bot.session.get(question_url) as response:
            if response.ok:
                await interaction.followup.send(f"```py\n{query}```{await response.text()}")
            else:
                msg = f"Wolfram Response was not ok, Status {response.status},"
                raise errors.ResponseNotOK(msg)


async def setup(bot: AluBot) -> None:
    """Load AluBot extension. Framework of discord.py."""
    await bot.add_cog(WolframAlpha(bot))
