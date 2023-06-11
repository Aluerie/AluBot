from __future__ import annotations

import random
import re
from typing import TYPE_CHECKING, Optional

import discord
from discord import app_commands
from discord.ext import commands

from utils import AluCog, checks, const
from utils.webhook import check_msg_react, user_webhook

if TYPE_CHECKING:
    from utils import AluContext, AluGuildContext


class Other(AluCog):
    @commands.hybrid_command()
    async def coinflip(self, ctx: AluContext):
        """Flip a coin: Heads or Tails?"""
        word = 'Heads' if random.randint(0, 1) == 0 else 'Tails'
        return await ctx.reply(content=word, file=discord.File(f'assets/images/coinflip/{word}.png'))

    @commands.Cog.listener()
    async def on_message(self, message: discord.Message):
        if message.author.id in [const.User.bot, const.User.yen]:
            return

        async def work_non_command_mentions(msg: discord.Message):
            """for now there is only blush and question marks"""
            if msg.guild and msg.guild.me in msg.mentions:
                if any([item in msg.content.lower() for item in ['😊', "blush"]]):
                    await msg.channel.send(f'{msg.author.mention} {const.Emote.peepoBlushDank}')
                else:
                    ctx = await self.bot.get_context(msg)
                    if ctx.command:
                        return
                    else:
                        for r in ['❔', '❕', '🤔']:
                            await msg.add_reaction(r)

        await work_non_command_mentions(message)

        async def bots_in_lobby(msg: discord.Message):
            if msg.channel.id == const.Channel.general:
                text = None
                if msg.interaction is not None and msg.interaction.type == discord.InteractionType.application_command:
                    text = 'Slash-commands'
                if msg.author.bot and not msg.webhook_id:
                    text = 'Bots'
                if text is not None:
                    await msg.channel.send(
                        '{0} in {1} ! {2} {2} {2}'.format(text, const.Channel.general.mention, const.Emote.Ree)
                    )

        await bots_in_lobby(message)

        async def weebs_out(msg: discord.Message):
            if msg.channel.id == const.Channel.weebs and random.randint(1, 100 + 1) < 7:
                await msg.channel.send(
                    '{0} {0} {0} {1} {1} {1} {2} {2} {2} {3} {3} {3}'.format(
                        '<a:WeebsOutOut:730882034167185448>',
                        '<:WeebsOut:856985447985315860>',
                        '<a:peepoWeebSmash:728671752414167080>',
                        '<:peepoRiot:730883102678974491>',
                    )
                )

        await weebs_out(message)

        async def ree_the_oof(msg: discord.Message):
            if not msg.guild or msg.guild.id != const.Guild.community:
                return
            if "Oof" in msg.content:
                try:
                    await msg.add_reaction(const.Emote.Ree)
                except discord.errors.Forbidden:
                    await msg.delete()

        await ree_the_oof(message)

        async def random_comfy_react(msg: discord.Message):
            if not msg.guild or msg.guild.id != const.Guild.community:
                return
            roll = random.randint(1, 300 + 1)
            if roll < 2:
                try:
                    await msg.add_reaction(const.Emote.peepoComfy)
                except Exception:
                    return

        await random_comfy_react(message)

        async def your_life(msg):
            if not msg.guild or msg.guild.id != const.Guild.community or random.randint(1, 170 + 1) >= 2:
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
    async def do_emote_spam(self, ctx: AluContext):
        """Send 3x random emote into emote spam channel"""
        rand_guild = random.choice(self.bot.guilds)
        rand_emoji = random.choice(rand_guild.emojis)
        answer_text = f'{str(rand_emoji)} ' * 3
        channel = self.community.emote_spam
        await channel.send(answer_text)
        e = discord.Embed(colour=const.Colour.prpl(), description=f'I sent {answer_text} into {channel.mention}')
        await ctx.reply(embed=e, ephemeral=True, delete_after=10)

    @commands.hybrid_command()
    async def apuband(self, ctx: AluContext):
        """Send apuband emote combo."""
        guild = self.community.guild
        emote_names = ['peepo1Maracas', 'peepo2Drums', 'peepo3Piano', 'peepo4Guitar', 'peepo5Singer', 'peepo6Sax']
        content = ' '.join([str(discord.utils.get(guild.emojis, name=e)) for e in emote_names])
        try:
            if ctx.channel and not isinstance(ctx.channel, (discord.ForumChannel, discord.CategoryChannel)):
                await ctx.channel.send(content=content)
                await ctx.reply(content=f'Nice {const.Emote.DankApprove}', ephemeral=True)
            else:
                msg = f'We can\'t send messages in forum channels {const.Emote.FeelsDankManLostHisHat}'
                await ctx.reply(content=msg, ephemeral=True)
        except:
            msg = f'Something went wrong {const.Emote.FeelsDankManLostHisHat} probably permissions'
            await ctx.reply(content=msg, ephemeral=True)

    @commands.hybrid_command()
    @app_commands.describe(max_roll_number="Max limit to roll")
    async def roll(self, ctx: AluContext, max_roll_number: app_commands.Range[int, 1]):
        """Roll an integer from 1 to `max_roll_number`."""
        await ctx.reply(content=str(random.randint(1, max_roll_number + 1)))

    @commands.hybrid_command(usage='[channel=curr] [text=Allo]')
    @commands.check_any(commands.has_permissions(manage_messages=True), commands.check(checks.ext.is_my_guild()))
    @commands.bot_has_permissions(send_messages=True, manage_messages=True)
    async def echo(
        self,
        ctx: AluGuildContext,
        channel: Optional[discord.TextChannel] = None,
        *,
        text: str = 'Allo',
    ):
        """Send `text` to `#channel` from bot's name.

        For text command you can also reply to a message without specifying text`for bot to copy it. 

        Parameters
        ----------
        channel: Optional[discord.TextChannel]
            Channel to send to
        text:
            Enter text to speak
        """

        # Note, that if you want bot to send a fancy message with embeds then there is `/embed make` command.
        # TODO: when embed maker is ready add this^ into the command docstring 
        ch = channel or ctx.channel
        if ch.id in [const.Channel.emote_spam, const.Channel.comfy_spam]:
            msg = f'Sorry, channel {ch.mention} is special emote-only channel. I won\' speak there.'
            raise commands.MissingPermissions([msg])
        elif not ch.permissions_for(ctx.author).send_messages:
            raise commands.MissingPermissions([f'Sorry, you don\'t have permissions to speak in {ch.mention}'])
        else:
            if replied_msg := ctx.replied_message:
                text = replied_msg.content
            await ch.send(text[0:2000])
            if ctx.interaction:
                await ctx.reply(content=f'I did it {const.Emote.DankApprove}', ephemeral=True)
        try:
            await ctx.message.delete()
        except:
            pass

    @commands.hybrid_command(
        name='emoteit', aliases=['emotialize'], description="Emotializes your text into standard emotes"
    )
    @app_commands.describe(text="Text that will be converted into emotes")
    async def emoteit(self, ctx: AluContext, *, text: str):
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
                ' ': ' ',
                '!': '\N{WHITE EXCLAMATION MARK ORNAMENT}',
                '?': '\N{WHITE QUESTION MARK ORNAMENT}',
            } | {str(i): n for i, n in enumerate(const.DIGITS)}
            alphabet = [  # maybe make char one as well one day
                'a',
                'b',
                'c',
                'd',
                'e',
                'f',
                'g',
                'h',
                'i',
                'j',
                'k',
                'l',
                'm',
                'n',
                'o',
                'p',
                'q',
                'r',
                's',
                't',
                'u',
                'v',
                'w',
                'x',
                'y',
                'z',
            ]
            for item in alphabet:
                emotialize_dict[item] = f':regional_indicator_{item}: '

            if letter.lower() in emotialize_dict.keys():
                answer += emotialize_dict[letter.lower()]
            else:
                answer += letter
        await user_webhook(ctx, content=answer)
        if ctx.interaction:
            await ctx.reply(content=const.Emote.DankApprove, ephemeral=True)
        else:
            await ctx.message.delete()

    @commands.Cog.listener()
    async def on_reaction_add(self, reaction, user):
        if str(reaction) == '\N{CROSS MARK}':
            if check_msg_react(user.id, reaction.message.id):
                await reaction.message.delete()
