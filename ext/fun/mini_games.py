from __future__ import annotations

import random
from enum import Enum
from typing import TYPE_CHECKING, NamedTuple, Self, override

import discord
from discord import app_commands
from discord.ext import commands

from bot import AluCog, AluView
from utils import const

if TYPE_CHECKING:
    from bot import AluBot, AluInteraction


class RPSElement(NamedTuple):
    """Player Move Attributes."""

    number: int  # used for RPS math
    emote: str
    word: str


class RPSChoice(Enum):
    """Enum to describe all three moves of the game."""

    Rock = RPSElement(number=0, emote="\N{ROCK}", word="smashes")
    Paper = RPSElement(number=1, emote="\N{ROLLED-UP NEWSPAPER}", word="covers")
    Scissors = RPSElement(number=2, emote="\N{BLACK SCISSORS}", word="cut")

    @property
    def emote_name(self) -> str:
        """Somewhat display name for the class. I like emote+word formatting a lot."""
        return f"{self.value.emote} {self.name}"


class RPSView(AluView):
    """Rock Paper Scissors View."""

    def __init__(
        self,
        *,
        player1: discord.User | discord.Member,
        player2: discord.User | discord.Member,
        message: discord.Message = None,  # type: ignore[reportArgumentType] # secured to be discord.Message
    ) -> None:
        super().__init__(author_id=None)
        self.player1: discord.User | discord.Member = player1
        self.player2: discord.User | discord.Member = player2
        self.message: discord.Message = message

        self.players = (player1, player2)

        self.choices: dict[discord.User | discord.Member, RPSChoice] = {}

    @override
    async def on_timeout(self) -> None:
        e = self.message.embeds[0]
        e.add_field(name="Timeout", value="Sorry, it is been too long, game is over in Draw due to timeout.")
        await self.message.edit(embed=e, view=None)

    async def bot_choice_edit(self) -> None:
        """Edit the embed with bot's play move."""
        self.choices[self.player2] = random.choice(list(RPSChoice))
        await self.edit_embed_player_choice(self.player2)

    async def edit_embed_player_choice(self, player: discord.User | discord.Member) -> None:
        """Edit the embed with player choice."""
        e = self.message.embeds[0].copy()
        e.set_field_at(
            2,
            name=e.fields[2].name,
            value=((e.fields[2].value or "") + f"\n\N{BLACK CIRCLE} Player {player.mention} has made their choice"),
            inline=False,
        )
        await self.message.edit(embed=e)

    @override
    async def interaction_check(self, interaction: AluInteraction) -> bool:
        if interaction.user and interaction.user in self.players:
            if interaction.user in self.choices:
                embed = discord.Embed(
                    color=const.Color.error,
                    description=f"You've already chosen **{self.choices[interaction.user]}**",
                )
                await interaction.response.send_message(embed=embed, ephemeral=True)
                return False
            return True
        embed = discord.Embed(
            color=const.Color.error,
            description="Sorry! This game dialog is not for you.",
        )
        await interaction.response.send_message(embed=embed, ephemeral=True)
        return False

    def result_str(self) -> tuple[str, discord.User | discord.Member | None]:
        """Calculate and announce the result of the game."""
        choices_string = "\n".join([f"{n.mention}: {c.emote_name}" for n, c in self.choices.items()])

        c1 = self.choices[self.player1]  # choice 1
        c2 = self.choices[self.player2]  # choice 2

        def winning_choice(c1: RPSChoice, c2: RPSChoice) -> tuple[str, str, discord.User | discord.Member | None]:
            if (c1.value.number + 1) % 3 == c2.value.number:  # Player2 won bcs their move is +1 bigger than ~player1
                return f"{c2.emote_name} {c2.value.word} {c1.emote_name}", f"{self.player2.mention} wins", self.player2
            if c1.value.number == c2.value.number:  # It's a draw bcs both players played the same move
                return "Both players chose the same.", "Draw", None
            # Player1 wins bcs we know that it's not a draw and that player2 didn't win
            return f"{c1.emote_name} {c1.value.word} {c2.emote_name}", f"{self.player1.mention} wins", self.player1

        winning_strings = winning_choice(c1, c2)
        ggwp = f"\n\n**Good Game, Well Played {const.Emote.DankL} {const.Emote.DankL} {const.Emote.DankL}**"
        return f"{choices_string}\n{winning_strings[0]}{ggwp}\n{winning_strings[1]}", winning_strings[2]

    async def rps_button_callback(self, interaction: AluInteraction, choice: RPSChoice) -> None:
        """Boiler-plate function for Rock/Scissor/Paper buttons as player move choices."""
        self.choices[interaction.user] = choice

        embed = discord.Embed(color=const.Color.prpl, description=f"You've chosen **{choice.emote_name}**")
        await interaction.response.send_message(embed=embed, ephemeral=True)
        await self.edit_embed_player_choice(interaction.user)

        if len(self.choices) == 2:
            em_game = self.message.embeds[0].copy()
            string, player = self.result_str()
            em_game.add_field(name="Result", value=string, inline=False)
            if player:
                em_game.set_thumbnail(url=player.display_avatar.url)
            await self.message.edit(embed=em_game, view=None)
            self.stop()

    @discord.ui.button(label=RPSChoice.Rock.name, emoji=RPSChoice.Rock.value.emote, style=discord.ButtonStyle.red)
    async def rock_button(self, interaction: AluInteraction, _: discord.ui.Button[Self]) -> None:
        """Button to play rock in a Rock Paper Scissors game."""
        await self.rps_button_callback(interaction, RPSChoice.Rock)

    @discord.ui.button(label=RPSChoice.Paper.name, emoji=RPSChoice.Paper.value.emote, style=discord.ButtonStyle.green)
    async def paper_button(self, interaction: AluInteraction, _: discord.ui.Button[Self]) -> None:
        """Button to play paper in a Rock Paper Scissors game."""
        await self.rps_button_callback(interaction, RPSChoice.Paper)

    @discord.ui.button(
        label=RPSChoice.Scissors.name,
        emoji=RPSChoice.Scissors.value.emote,
        style=discord.ButtonStyle.blurple,
    )
    async def scissors_button(self, interaction: AluInteraction, _: discord.ui.Button[Self]) -> None:
        """Button to play scissors in a Rock Paper SCissors game."""
        await self.rps_button_callback(interaction, RPSChoice.Scissors)


class MiniGames(AluCog):
    """Just one command cog.

    Rock Paper Scissors mini-game.
    """

    @app_commands.command(name="rock-paper-scissors")
    async def rps(self, interaction: AluInteraction, user: discord.Member | discord.User) -> None:
        """Rock Paper Scissors game with @member."""
        if user == interaction.user:
            msg = "You cannot challenge yourself in a Rock Paper Scissors game"
            raise commands.BadArgument(msg)
        if user.bot and interaction.guild and user != interaction.guild.me:
            msg = "I'm afraid other bots do not know how to play this game"
            raise commands.BadArgument(msg)

        player1, player2 = (interaction.user, user)
        embed = (
            discord.Embed(
                color=const.Color.prpl,
                title="Rock Paper Scissors Game",
            )
            .add_field(name="Player 1", value=f"{player1.mention}")
            .add_field(name="Player 2", value=f"{player2.mention}")
            .add_field(
                name="Game State Log",
                value="\N{BLACK CIRCLE} Both players need to choose their item",
                inline=False,
            )
        )
        view = RPSView(player1=player1, player2=player2)
        await interaction.response.send_message(embed=embed, view=view)
        view.message = await interaction.original_response()
        if user.bot:
            await view.bot_choice_edit()


async def setup(bot: AluBot) -> None:
    """Load AluBot extension. Framework of discord.py."""
    await bot.add_cog(MiniGames(bot))
