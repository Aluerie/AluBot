from __future__ import annotations

import random
import re
from typing import TYPE_CHECKING, Optional

import discord
from discord import app_commands
from discord.ext import commands

from utils import checks, const, mimicry

from .._category import FunCog

if TYPE_CHECKING:
    from utils import AluContext, AluGuildContext


class Other(FunCog):
    @commands.hybrid_command()
    async def coinflip(self, ctx: AluContext):
        """Flip a coin: Heads or Tails?"""
        
        word = 'Heads' if random.randint(0, 1) == 0 else 'Tails'
        return await ctx.reply(content=word, file=discord.File(f'assets/images/coinflip/{word}.png'))

    @commands.Cog.listener('on_message')
    async def reply_non_command_mentions(self, message: discord.Message):
        """for now there is only blush and question marks"""
        if message.guild and message.guild.me in message.mentions:
            if any([item in message.content.lower() for item in ['😊', "blush"]]):
                await message.channel.send(f'{message.author.mention} {const.Emote.peepoBlushDank}')
            else:
                ctx = await self.bot.get_context(message)
                if ctx.command:
                    return
                else:
                    for r in ['❔', '❕', '🤔']:
                        await message.add_reaction(r)

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

        For text command you can also reply to a message without specifying text for bot to copy it.

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

    @staticmethod
    def fancify_text(text: str, *, style: dict[str, str]):
        patterns = [
            const.Rgx.user_mention,
            const.Rgx.role_mention,
            const.Rgx.channel_mention,
            const.Rgx.slash_mention,
            const.Rgx.emote,
        ]
        combined_pattern = r'|'.join(patterns)
        mentions_or_emotes = re.findall(combined_pattern, text)

        style = style | {k: k for k in mentions_or_emotes}
        pattern = '|'.join(re.escape(k) for k in style)
        match_repl = lambda c: (style.get(c.group(0)) or style.get(c.group(0).lower()) or c)
        return re.sub(pattern, match_repl, text)  # type: ignore # i dont understand regex types x_x

    async def send_fancy_text(self, ctx: AluContext, answer: str):
        if ctx.guild:
            # TODO: I'm not sure what to do when permissions won't go our way
            mimic = mimicry.MimicUserWebhook.from_context(ctx)

            await mimic.send_user_message(ctx.author, content=answer)

            if ctx.interaction:
                await ctx.reply(content=f'I did it {const.Emote.DankApprove}', ephemeral=True)
            else:
                await ctx.message.delete()
        else:
            await ctx.reply(answer)

    @commands.hybrid_command()
    @app_commands.describe(text="Text to convert into emotes.")
    async def emotify(self, ctx: AluContext, *, text: str):
        """Makes your text consist only of emotes."""

        style = (
            {
                '!': '\N{WHITE EXCLAMATION MARK ORNAMENT}',
                '?': '\N{WHITE QUESTION MARK ORNAMENT}',
            }  # ?! into emotes
            | {str(i): n for i, n in enumerate(const.DIGITS)}  # digits into emotes :zero:, :one:, :two:, ...
            | {
                chr(0x00000041 + x): f'{chr(0x0001F1E6 + x)} ' for x in range(26)
            }  # A-Z into :regional_identifier_a:-:regional_identifier_z:
            | {
                chr(0x00000061 + x): f'{chr(0x0001F1E6 + x)} ' for x in range(26)
            }  # a-z into :regional_identifier_a:-:regional_identifier_z:
        )
        answer = self.fancify_text(text, style=style)
        await self.send_fancy_text(ctx, answer)

    @commands.hybrid_command()
    @app_commands.describe(text="Text to convert into fancy text")
    async def fancify(self, ctx: AluContext, *, text: str): # cSpell:disable #fmt:off # black meeses it up x_x
        """𝓜𝓪𝓴𝓮𝓼 𝔂𝓸𝓾𝓻 𝓽𝓮𝔁𝓽 𝓵𝓸𝓸𝓴 𝓵𝓲𝓴𝓮 𝓽𝓱𝓲𝓼.""" 
        # cSpell:enable #fmt:on

        style = {chr(0x00000041 + x): chr(0x0001D4D0 + x) for x in range(26)} | {  # A-Z into fancy 𝓐-𝓩
            chr(0x00000061 + x): chr(0x0001D4EA + x) for x in range(26)  # a-z into fancy a-z (Black messes it up)
        }
        answer = self.fancify_text(text, style=style)
        await self.send_fancy_text(ctx, answer)
