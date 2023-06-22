from __future__ import annotations

from enum import Enum
from typing import TYPE_CHECKING, Dict, NamedTuple, Optional, Tuple

import discord
from discord.ext import commands
from numpy.random import choice

from utils import AluCog, const

from .._category import FunCog

if TYPE_CHECKING:
    from utils import AluGuildContext


class RPSElement(NamedTuple):
    number: int
    emote: str
    word: str


class RPSChoice(Enum):
    Rock = RPSElement(number=0, emote='\N{ROCK}', word='smashes')
    Paper = RPSElement(number=1, emote='\N{ROLLED-UP NEWSPAPER}', word='covers')
    Scissors = RPSElement(number=2, emote='\N{BLACK SCISSORS}', word='cut')

    @property
    def emote_name(self):
        return f'{self.value.emote} {self.name}'


class RPSView(discord.ui.View):
    def __init__(
        self,
        *,
        player1: discord.User | discord.Member,
        player2: discord.User | discord.Member,
        message: discord.Message = None,  # type: ignore
    ):
        super().__init__()
        self.player1: discord.User | discord.Member = player1
        self.player2: discord.User | discord.Member = player2
        self.message: discord.Message = message

        self.players = (player1, player2)

        self.choices: Dict[discord.User | discord.Member, RPSChoice] = {}

    async def on_timeout(self) -> None:
        e = self.message.embeds[0]
        e.add_field(name='Timeout', value='Sorry, it is been too long, game is over in Draw due to timeout.')
        await self.message.edit(embed=e, view=None)

    async def bot_choice_edit(self):
        self.choices[self.player2] = choice(list(RPSChoice))  # type: ignore # TODO: FIX
        await self.edit_embed_player_choice(self.player2)

    @staticmethod
    def choice_name(btn_: discord.ui.Button):
        return f'{btn_.emoji} {btn_.label}'

    async def edit_embed_player_choice(self, player: discord.User | discord.Member):
        e = self.message.embeds[0].copy()
        e.set_field_at(
            2,
            name=e.fields[2].name,
            value=((e.fields[2].value or '') + f'\n\N{BLACK CIRCLE} Player {player.mention} has made their choice'),
            inline=False,
        )
        await self.message.edit(embed=e)

    async def interaction_check(self, ntr: discord.Interaction) -> bool:
        if ntr.user and ntr.user in self.players:
            if ntr.user.id in self.choices:
                e = discord.Embed(colour=const.Colour.error())
                e.description = f'You\'ve already chosen **{self.choices[ntr.user.id]}**'
                await ntr.response.send_message(embed=e, ephemeral=True)
                return False
            else:
                return True
        else:
            e = discord.Embed(colour=const.Colour.error(), description='Sorry! This game dialog is not for you.')
            await ntr.response.send_message(embed=e, ephemeral=True)
            return False

    def result_str(self) -> Tuple[str, Optional[discord.User | discord.Member]]:
        choices_string = '\n'.join([f'{n.mention}: {c.emote_name}' for n, c in self.choices.items()])

        c1 = self.choices[self.player1]
        c2 = self.choices[self.player2]

        def winning_choice(c1: RPSChoice, c2: RPSChoice) -> Tuple[str, str, Optional[discord.User | discord.Member]]:
            if (c1.value.number + 1) % 3 == c2.value.number:  # Player2 won bcs their move is +1 bigger than ~player1
                return f'{c2.emote_name} {c2.value.word} {c1.emote_name}', f'{self.player2.mention} wins', self.player2
            elif c1.value.number == c2.value.number:  # It's a draw bcs both players played the same move
                return 'Both players chose the same.', 'Draw', None
            else:  # Player1 wins bcs we know that it's not a draw and that player2 didn't win
                return f'{c1.emote_name} {c1.value.word} {c2.emote_name}', f'{self.player1.mention} wins', self.player1

        winning_strings = winning_choice(c1, c2)
        ggwp = '\n\n**Good Game, Well Played {0} {0} {0}**'.format(const.Emote.DankL)
        return f'{choices_string}\n{winning_strings[0]}{ggwp}\n{winning_strings[1]}', winning_strings[2]

    async def rps_button_callback(self, ntr: discord.Interaction, choice: RPSChoice):
        self.choices[ntr.user] = choice

        e = discord.Embed(colour=const.Colour.prpl(), description=f'You\'ve chosen **{choice.emote_name}**')
        await ntr.response.send_message(embed=e, ephemeral=True)
        await self.edit_embed_player_choice(ntr.user)

        if len(self.choices) == 2:
            em_game = self.message.embeds[0].copy()
            string, player = self.result_str()
            em_game.add_field(name='Result', value=string, inline=False)
            if player:
                em_game.set_thumbnail(url=player.display_avatar.url)
            await self.message.edit(embed=em_game, view=None)
            self.stop()

    @discord.ui.button(label=RPSChoice.Rock.name, emoji=RPSChoice.Rock.value.emote, style=discord.ButtonStyle.red)
    async def rock_button(self, ntr: discord.Interaction, _btn: discord.ui.Button):
        await self.rps_button_callback(ntr, RPSChoice.Rock)

    @discord.ui.button(label=RPSChoice.Paper.name, emoji=RPSChoice.Paper.value.emote, style=discord.ButtonStyle.green)
    async def paper_button(self, ntr: discord.Interaction, _btn: discord.ui.Button):
        await self.rps_button_callback(ntr, RPSChoice.Paper)

    @discord.ui.button(
        label=RPSChoice.Scissors.name, emoji=RPSChoice.Scissors.value.emote, style=discord.ButtonStyle.blurple
    )
    async def scissors_button(self, ntr: discord.Interaction, _btn: discord.ui.Button):
        await self.rps_button_callback(ntr, RPSChoice.Scissors)


class RockPaperScissorsCommand(FunCog):
    @commands.hybrid_command(name='rock-paper-scissors', aliases=['rps', 'rock_paper_scissors'])
    async def rps(self, ctx: AluGuildContext, user: discord.Member | discord.User):
        """Rock Paper Scissors game with @member"""
        if user == ctx.author:
            raise commands.BadArgument('You cannot challenge yourself in a Rock Paper Scissors game')
        if user.bot and ctx.guild and user != ctx.guild.me:
            raise commands.BadArgument('I\'m afraid other bots do not know how to play this game')

        player1, player2 = (ctx.author, user)
        e = discord.Embed(title='Rock Paper Scissors Game', colour=const.Colour.prpl())
        e.add_field(name='Player 1', value=f'{player1.mention}')
        e.add_field(name='Player 2', value=f'{player2.mention}')
        e.add_field(
            name='Game State Log', value='\N{BLACK CIRCLE} Both players need to choose their item', inline=False
        )
        view = RPSView(player1=player1, player2=player2)
        view.message = await ctx.reply(embed=e, view=view)
        if user.bot:
            await view.bot_choice_edit()
