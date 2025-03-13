from __future__ import annotations

import contextlib
import random
import re
from typing import TYPE_CHECKING

import discord
from discord import app_commands
from discord.ext import commands

from bot import AluCog
from utils import const, mimics

if TYPE_CHECKING:
    from bot import AluBot, AluInteraction


class FunOther(AluCog):
    @app_commands.command()
    async def coinflip(self, interaction: AluInteraction) -> None:
        """Flip a coin: Heads or Tails?."""
        word = "Heads" if random.randint(0, 1) == 0 else "Tails"
        await interaction.response.send_message(content=word, file=discord.File(f"assets/images/coinflip/{word}.png"))

    # todo: this should be sonehere else
    @commands.Cog.listener("on_message")
    async def reply_non_command_mentions(self, message: discord.Message) -> None:
        """For now there is only blush and question marks."""
        if message.guild and message.guild.me in message.mentions:
            if any(item in message.content.lower() for item in ["😊", "blush"]):
                await message.channel.send(f"{message.author.mention} {const.Emote.peepoBlushDank}")
            else:
                ctx = await self.bot.get_context(message)
                if ctx.command:
                    return
                for r in ["❔", "❕", "🤔"]:
                    with contextlib.suppress(discord.HTTPException):
                        await message.add_reaction(r)

    @app_commands.command()
    async def roll(self, interaction: AluInteraction, max_roll_number: app_commands.Range[int, 1]) -> None:
        """Roll an integer from 1 to `max_roll_number`.

        Parameters
        ----------
        max_roll_number
            Max limit to roll.

        """
        await interaction.response.send_message(content=str(random.randint(1, max_roll_number + 1)))

    @staticmethod
    def fancify_text(text: str, *, style: dict[str, str]) -> str:
        patterns = [
            const.Regex.USER_MENTION,
            const.Regex.ROLE_MENTION,
            const.Regex.CHANNEL_MENTION,
            const.Regex.SLASH_MENTION,
            const.Regex.EMOTE,
        ]
        combined_pattern = r"|".join(patterns)
        mentions_or_emotes = re.findall(combined_pattern, text)

        style |= {k: k for k in mentions_or_emotes}
        pattern = "|".join(re.escape(k) for k in style)

        def match_repl(c: re.Match[str]) -> str | re.Match[str]:
            return style.get(c.group(0)) or style.get(c.group(0).lower()) or c

        return re.sub(pattern, match_repl, text)  # type: ignore # i dont understand regex types x_x

    async def send_mimic_text(self, interaction: AluInteraction, content: str) -> None:
        if not interaction.guild:
            # outside of guilds - probably DM
            await interaction.response.send_message(content)
        else:
            # in guild - hopefully we can make a webhook
            mirror = mimics.Mirror.from_interaction(interaction)
            await mirror.send(member=interaction.user, content=content)
            await interaction.response.send_message(content=f"We did it {const.Emote.DankApprove}", ephemeral=True)

    text_group = app_commands.Group(
        name="text",
        description="Commands to transform text into something nice.",
    )

    @text_group.command()
    async def emotify(self, interaction: AluInteraction, text: str) -> None:
        """Makes your text consist only of emotes.

        Parameters
        ----------
            Text to convert into emotes.
        """
        style = (
            {
                "!": "\N{WHITE EXCLAMATION MARK ORNAMENT}",
                "?": "\N{WHITE QUESTION MARK ORNAMENT}",
            }  # Turn ?! into emotes
            | {str(i): n for i, n in enumerate(const.DIGITS)}  # digits into emotes :zero:, :one:, :two:, ...
            | {
                chr(0x00000041 + x): f"{chr(0x0001F1E6 + x)} " for x in range(26)
            }  # A-Z into :regional_identifier_a:-:regional_identifier_z:
            | {
                chr(0x00000061 + x): f"{chr(0x0001F1E6 + x)} " for x in range(26)
            }  # a-z into :regional_identifier_a:-:regional_identifier_z:
        )
        answer = self.fancify_text(text, style=style)
        await self.send_mimic_text(interaction, answer)

    @text_group.command()
    async def fancify(
        self, interaction: AluInteraction, text: str
    ) -> None:  # cSpell:disable #fmt:off # black meeses it up x_x
        """𝓜𝓪𝓴𝓮𝓼 𝔂𝓸𝓾𝓻 𝓽𝓮𝔁𝓽 𝓵𝓸𝓸𝓴 𝓵𝓲𝓴𝓮 𝓽𝓱𝓲𝓼.

        Parameters
        ----------
            Text to convert into fancy text.
        """  # noqa: RUF002
        # cSpell:enable #fmt:on  # noqa: ERA001

        style = {chr(0x00000041 + x): chr(0x0001D4D0 + x) for x in range(26)} | {  # A-Z into fancy font
            chr(0x00000061 + x): chr(0x0001D4EA + x)
            for x in range(26)  # a-z into fancy a-z (Black messes it up)
        }
        answer = self.fancify_text(text, style=style)
        await self.send_mimic_text(interaction, answer)

    @app_commands.command()
    async def apuband(self, interaction: AluInteraction) -> None:
        """Send apuband emote combo."""
        emote_names = ["peepo1Maracas", "peepo2Drums", "peepo3Piano", "peepo4Guitar", "peepo5Singer", "peepo6Sax"]
        content = " ".join([str(discord.utils.get(self.community.guild.emojis, name=e)) for e in emote_names])
        await self.send_mimic_text(interaction, content)


async def setup(bot: AluBot) -> None:
    """Load AluBot extension. Framework of discord.py."""
    await bot.add_cog(FunOther(bot))
