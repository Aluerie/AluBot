from __future__ import annotations
from typing import TYPE_CHECKING, Optional, Literal

import re

import discord
from discord import app_commands
from discord.ext import commands
from numpy.random import randint, choice

from .utils.var import Clr, Ems, Uid, Cid, Sid, Rgx
from .utils.webhook import user_webhook, check_msg_react

if TYPE_CHECKING:
    from .utils.bot import AluBot
    from .utils.context import Context


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
        e.add_field(
            name='Timeout',
            value='Sorry, it is been too long, game is over in Draw due to timeout.'
        )
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
                e.fields[2].value +
                f'\n\N{BLACK CIRCLE} Player {1 + player_index} {self.players[player_index].mention} has made their choice'
            ),
            inline=False
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

        if self.choices[1-player_index] is not None:
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
                verb_dict = {
                    '🪨 Rock': 'smashes',
                    '🗞️ Paper': 'covers',
                    '✂ Scissors': 'cut'
                }
                if win_index:
                    return \
                        f'{self.choices[win_index-1]} ' \
                        f'{verb_dict[self.choices[win_index-1]]} ' \
                        f'{self.choices[1-(win_index-1)]}'
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
                inline=False
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


class FunThings(commands.Cog, name='Fun'):
    """Commands to have fun with"""
    def __init__(self, bot: AluBot):
        self.bot: AluBot = bot

    @property
    def help_emote(self) -> discord.PartialEmoji:
        return discord.PartialEmoji.from_str(Ems.FeelsDankMan)

    @commands.hybrid_command(name='rock-paper-scissors', aliases=['rps'])
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
        e.add_field(name='Game State Log', value='\N{BLACK CIRCLE} Both players need to choose their item', inline=False)
        view = RPSView(players=players)
        view.message = await ctx.reply(embed=e, view=view)
        if member.bot:
            await view.bot_choice_edit()

    @commands.hybrid_command(
        aliases=['cf'],
        description='Flip a coin: Heads or Tails?'
    )
    async def coinflip(self, ctx):
        """Flip a coin """
        word = 'Heads' if randint(2) == 0 else 'Tails'
        return await ctx.reply(content=word, file=discord.File(f'media/{word}.png'))

    @commands.Cog.listener()
    async def on_message(self, message: discord.Message):
        if message.author.id in [Uid.bot, Uid.yen]:
            return

        async def work_non_command_mentions(msg: discord.Message):
            """for now there is only blush and question marks"""
            if msg.guild and msg.guild.me in msg.mentions:
                if any([item in msg.content.lower() for item in ['😊', "blush"]]):
                    await msg.channel.send(f'{msg.author.mention} {Ems.peepoBlushDank}')
                else:
                    ctx = await self.bot.get_context(msg)
                    if ctx.command:
                        return
                    else:
                        for r in ['❔', '❕', '🤔']:
                            await msg.add_reaction(r)
        await work_non_command_mentions(message)

        async def bots_in_lobby(msg: discord.Message):
            if msg.channel.id == Cid.general:
                text = None
                if msg.interaction is not None and msg.interaction.type == discord.InteractionType.application_command:
                    text = 'Slash-commands'
                if msg.author.bot and not msg.webhook_id:
                    text = 'Bots'
                if text is not None:
                    await msg.channel.send('{0} in {1} ! {2} {2} {2}'.format(text, msg.channel.mention, Ems.Ree))
        await bots_in_lobby(message)

        async def weebs_out(msg: discord.Message):
            if msg.channel.id == Cid.weebs and randint(1, 100 + 1) < 7:
                await self.bot.get_channel(Cid.weebs).send(
                    '{0} {0} {0} {1} {1} {1} {2} {2} {2} {3} {3} {3}'.format(
                        '<a:WeebsOutOut:730882034167185448>', '<:WeebsOut:856985447985315860>',
                        '<a:peepoWeebSmash:728671752414167080>', '<:peepoRiot:730883102678974491>'
                    )
                )
        await weebs_out(message)

        async def ree_the_oof(msg: discord.Message):
            if not msg.guild or msg.guild.id != Sid.alu:
                return
            if "Oof" in msg.content:
                try:
                    await msg.add_reaction(Ems.Ree)
                except discord.errors.Forbidden:
                    await msg.delete()
        await ree_the_oof(message)

        async def random_comfy_react(msg: discord.Message):
            if not msg.guild or msg.guild.id != Sid.alu:
                return
            roll = randint(1, 300 + 1)
            if roll < 2:
                try:
                    await msg.add_reaction(Ems.peepoComfy)
                except Exception:
                    return
        await random_comfy_react(message)

        async def your_life(msg):
            if not msg.guild or msg.guild.id != Sid.alu or randint(1, 170 + 1) >= 2:
                return
            try:
                sliced_text = msg.content.split()
                if len(sliced_text) > 2:
                    answer_text = f"Your life {' '.join(sliced_text[2:])}"
                    await msg.channel.send(answer_text)
            except Exception:
                return
        await your_life(message)

    @commands.hybrid_command()
    async def doemotespam(self, ctx: Context):
        """Send 3x random emote into emote spam channel"""
        rand_guild = choice(self.bot.guilds)
        rand_emoji = choice(rand_guild.emojis)
        answer_text = f'{str(rand_emoji)} ' * 3
        emot_ch = self.bot.get_channel(Cid.emote_spam)
        await emot_ch.send(answer_text)
        e = discord.Embed(colour=Clr.prpl, description=f'I sent {answer_text} into {emot_ch.mention}')
        await ctx.reply(embed=e, ephemeral=True, delete_after=10)
        if not ctx.interaction:
            await ctx.message.delete()

    @commands.hybrid_command(
        description='Send apuband emote combo'
    )
    async def apuband(self, ctx: Context):
        """Send apuband emote combo"""
        guild = self.bot.get_guild(Sid.alu)
        emote_names = ['peepo1Maracas', 'peepo2Drums', 'peepo3Piano', 'peepo4Guitar', 'peepo5Singer', 'peepo6Sax']
        content = ' '.join([str(discord.utils.get(guild.emojis, name=e)) for e in emote_names])
        await ctx.channel.send(content=content)
        if ctx.interaction:
            await ctx.reply(content=f'Nice {Ems.DankApprove}', ephemeral=True)
        else:
            await ctx.message.delete()

    @commands.hybrid_command(
        description='Roll an integer from 1 to `max_roll_number`'
    )
    @app_commands.describe(max_roll_number="Max limit to roll")
    async def roll(self, ctx, max_roll_number: commands.Range[int, 1, None]):
        """Roll an integer from 1 to `max_roll_number` ;"""
        await ctx.reply(randint(1, max_roll_number + 1))

    @commands.hybrid_command(
        usage='[channel=curr] [text=Allo]',
        description='Echo something somewhere'
    )
    @app_commands.describe(channel="Channel to send to")
    @app_commands.describe(text="Enter text to speak")
    async def echo(
            self,
            ctx: Context,
            channel: Optional[discord.TextChannel] = None,
            *,
            text: str = 'Allo'
    ):
        """Send `text` to `#channel` and delete your invoking message,
        so it looks like the bot is speaking on its own.
        """
        ch = channel or ctx.channel
        if ch.id in [Cid.emote_spam, Cid.comfy_spam]:
            raise commands.MissingPermissions(
                [f'Sorry, these channels are special so you can\'t use this command in {ch.mention}']
            )
        elif not ch.permissions_for(ctx.author).send_messages:
            raise commands.MissingPermissions(
                [f'Sorry, you don\'t have permissions to speak in {ch.mention}']
            )
        else:
            url_array = re.findall(Rgx.url_danny, str(text))
            for url in url_array:  # forbid embeds
                text = text.replace(url, f'<{url}>')
            await ch.send(text)
            if ctx.interaction:
                await ctx.reply(content=f'I did it {Ems.DankApprove}', ephemeral=True)
        try:
            await ctx.message.delete()
        except:
            pass

    @commands.hybrid_command(
        name='emoteit',
        aliases=['emotialize'],
        description="Emotializes your text into standard emotes"
    )
    @app_commands.describe(text="Text that will be converted into emotes")
    async def emoteit(self, ctx: Context, *, text: str):
        """Emotializes your text into standard emotes"""
        answer = ''
        skip_mode = 0
        for letter in text:
            if letter == '<':
                skip_mode = 1
                answer += letter
                continue
            if letter == '>':
                skip_mode = 0
                answer += letter
                continue
            elif skip_mode == 1:
                answer += letter
                continue

            # [f'{chr(0x30 + i)}{chr(0x20E3)}' for i in range(10)] < also numbers but from chars
            emotialize_dict = {
                ' ': ' ', '!': '\N{WHITE EXCLAMATION MARK ORNAMENT}', '?': '\N{WHITE QUESTION MARK ORNAMENT}'
            } | {str(i): n for i, n in enumerate(Ems.phone_numbers)}
            alphabet = [  # maybe make char one as well one day
                'a', 'b', 'c', 'd', 'e', 'f', 'g', 'h', 'i', 'j', 'k', 'l', 'm', 'n', 'o', 'p', 'q', 'r', 's', 't',
                'u', 'v', 'w', 'x', 'y', 'z'
            ]
            for item in alphabet:
                emotialize_dict[item] = f':regional_indicator_{item}: '

            if letter.lower() in emotialize_dict.keys():
                answer += emotialize_dict[letter.lower()]
            else:
                answer += letter
        await user_webhook(ctx, content=answer)
        if ctx.interaction:
            await ctx.reply(content=Ems.DankApprove, ephemeral=True)
        else:
            await ctx.message.delete()

    @commands.Cog.listener()
    async def on_reaction_add(self, reaction, user):
        if str(reaction) == '\N{CROSS MARK}':
            if check_msg_react(user.id, reaction.message.id):
                await reaction.message.delete()


async def setup(bot: AluBot):
    await bot.add_cog(FunThings(bot))
