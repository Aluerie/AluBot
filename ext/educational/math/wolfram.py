from __future__ import annotations

from typing import TYPE_CHECKING, Any
from urllib import parse as urlparse

from discord import app_commands

from config import WOLFRAM_TOKEN
from utils import const, errors

from .._base import EducationalCog

if TYPE_CHECKING:
    import discord

    from bot import AluBot


class WolframAlphaCog(EducationalCog, emote=const.Emote.bedNerdge):
    """Query Wolfram Alpha within the bot.

    Probably the best computational intelligence service ever.
    [wolframalpha.com](https://www.wolframalpha.com/)
    """

    def __init__(self, *args: Any, **kwargs: Any) -> None:
        super().__init__(*args, **kwargs)
        base = "https://api.wolframalpha.com/v1"
        self.simple_url = f"{base}/simple?appid={WOLFRAM_TOKEN}&background=black&foreground=white&layout=labelbar&i="
        self.short_url = f"{base}/result?appid={WOLFRAM_TOKEN}&i="

    wolfram_group = app_commands.Group(
        name="wolfram",
        description="WolframAlpha queries.",
    )

    @wolfram_group.command(name="long")
    @app_commands.checks.cooldown(1, 60.0, key=lambda i: (i.guild_id, i.user.id))
    async def wolfram_long(self, interaction: discord.Interaction[AluBot], query: str) -> None:
        """Get a long, detailed image-answer from WolframAlpha.

        Parameters
        ----------
        query
            Query for WolframAlpha.
        """
        await interaction.response.defer()
        question_url = f"{self.simple_url}{urlparse.quote(query)}"
        file = await self.bot.transposer.url_to_file(question_url, filename="WolframAlpha.png")
        await interaction.followup.send(content=f"```py\n{query}```", file=file)

    @wolfram_group.command(name="short")
    @app_commands.checks.cooldown(1, 60.0, key=lambda i: (i.guild_id, i.user.id))
    async def wolfram_short(self, interaction: discord.Interaction[AluBot], query: str) -> None:
        """Get a quick, short answer from WolframAlpha.

        Parameters
        ----------
        query
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
    await bot.add_cog(WolframAlphaCog(bot))
