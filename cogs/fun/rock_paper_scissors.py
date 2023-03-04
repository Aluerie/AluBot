from __future__ import annotations
from typing import TYPE_CHECKING, Optional, Literal

import discord
from discord.ext import commands
from numpy.random import choice

from utils.var import Clr, Ems

from ._base import FunBase

if TYPE_CHECKING:
    from utils.context import Context


class RPSView(discord.ui.View):
    def __init__(
        self,
        *,
        players: [discord.Member, discord.Member],
        message: Optional[discord.Message] = None,
    ):
        super().__init__()
        self.players: [discord.Member, discord.Member] = players
        self.message: Optional[discord.Message] = message

        self.choices = [None, None]

    async def on_timeout(self) -> None:
        e = self.message.embeds[0]
        e.add_field(name='Timeout', value='Sorry, it is been too long, game is over in Draw due to timeout.')
        await self.message.edit(embed=e, view=None)

    async def bot_choice_edit(self):
        self.choices[1] = choice(self.all_choices)
        await self.edit_embed_player_choice(1)

    @staticmethod
    def choice_name(btn_: discord.ui.Button):
        return f'{btn_.emoji} {btn_.label}'

    @property
    def all_choices(self):
        return [self.choice_name(b) for b in self.children if isinstance(b, discord.ui.Button)]

    async def edit_embed_player_choice(self, player_index: Literal[0, 1]):
        e = self.message.embeds[0]
        e.set_field_at(
            2,
            name=e.fields[2].name,
            value=(
                e.fields[2].value
                + f'\n\N{BLACK CIRCLE} Player {1 + player_index} {self.players[player_index].mention} has made their choice'
            ),
            inline=False,
        )
        await self.message.edit(embed=e)

    async def interaction_check(self, ntr: discord.Interaction) -> bool:
        if ntr.user and ntr.user in self.players:
            return True
        else:
            e = discord.Embed(description='Sorry! This game dialog is not for you.', colour=Clr.error)
            await ntr.response.send_message(embed=e, ephemeral=True)
            return False

    async def rps_button_callback(self, ntr: discord.Interaction, btn: discord.ui.Button):
        outcome_list = ['Draw', f'{self.players[0].mention} wins', f'{self.players[1].mention} wins']

        player_index = self.players.index(ntr.user)

        if self.choices[player_index] is not None:
            e = discord.Embed(colour=Clr.error, description=f'You\'ve already chosen **{self.choices[player_index]}**')
            await ntr.response.send_message(embed=e, ephemeral=True)
        else:
            self.choices[player_index] = self.choice_name(btn)
            e = discord.Embed(colour=Clr.prpl, description=f'You\'ve chosen **{self.choice_name(btn)}**')
            await ntr.response.send_message(embed=e, ephemeral=True)
            await self.edit_embed_player_choice(player_index)

        if self.choices[1 - player_index] is not None:

            def winner_index(p1, p2):
                if (p1 + 1) % 3 == p2:
                    return 2  # Player 2 won because their move is one greater than player 1
                if p1 == p2:
                    return 0  # It's a draw because both players played the same move
                else:
                    return 1  # Player 1 wins because we know that it's not a draw and that player 2 didn't win

            em_game = self.message.embeds[0]
            player_choices = [self.all_choices.index(p) for p in self.choices]  # type: ignore
            win_index = winner_index(*player_choices)

            def winning_sentence():
                verb_dict = {'🪨 Rock': 'smashes', '🗞️ Paper': 'covers', '✂ Scissors': 'cut'}
                if win_index:
                    return (
                        f'{self.choices[win_index-1]} '
                        f'{verb_dict[self.choices[win_index-1]]} '
                        f'{self.choices[1-(win_index-1)]}'
                    )
                else:
                    return 'Both players chose the same !'

            em_game.add_field(
                name='Result',
                value=(
                    f'{chr(10).join([f"{x.mention}: {y}" for x, y in zip(self.players, self.choices)])}'
                    f'\n{winning_sentence()}'
                    f'\n\n**Good Game, Well Played {Ems.DankL} {Ems.DankL} {Ems.DankL}**'
                    f'\n**{outcome_list[win_index]}**'
                ),
                inline=False,
            )
            if win_index:
                em_game.set_thumbnail(url=self.players[win_index - 1].avatar.url)
            await self.message.edit(embed=em_game, view=None)
            self.stop()

    @discord.ui.button(label='Rock', emoji='🪨', style=discord.ButtonStyle.red)
    async def rock_button(self, ntr: discord.Interaction, btn: discord.ui.Button):
        await self.rps_button_callback(ntr, btn)

    @discord.ui.button(label='Paper', emoji='🗞️', style=discord.ButtonStyle.green)
    async def paper_button(self, ntr: discord.Interaction, btn: discord.ui.Button):
        await self.rps_button_callback(ntr, btn)

    @discord.ui.button(label='Scissors', emoji='✂', style=discord.ButtonStyle.blurple)
    async def scissors_button(self, ntr: discord.Interaction, btn: discord.ui.Button):
        await self.rps_button_callback(ntr, btn)


class RockPaperScissorsCommand(FunBase):
    @commands.hybrid_command(name='rock-paper-scissors', aliases=['rps', 'rock_paper_scissors'])
    async def rps(self, ctx: Context, member: discord.Member):
        """Rock Paper Scissors game with @member"""
        if member == ctx.author:
            raise commands.BadArgument('You cannot challenge yourself in a Rock Paper Scissors game')
        if member.bot and member != ctx.guild.me:
            raise commands.BadArgument('I\'m afraid other bots do not know how to play this game')

        players = [ctx.author, member]
        e = discord.Embed(title='Rock Paper Scissors Game', colour=Clr.prpl)
        e.add_field(name='Player 1', value=f'{players[0].mention}')
        e.add_field(name='Player 2', value=f'{players[1].mention}')
        e.add_field(
            name='Game State Log', value='\N{BLACK CIRCLE} Both players need to choose their item', inline=False
        )
        view = RPSView(players=players)
        view.message = await ctx.reply(embed=e, view=view)
        if member.bot:
            await view.bot_choice_edit()
