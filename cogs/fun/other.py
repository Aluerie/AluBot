from __future__ import annotations

import re
from typing import TYPE_CHECKING, Optional

import discord
from discord import app_commands
from discord.ext import commands
from numpy.random import choice, randint

from utils import AluCog
from utils.const import Channel, Colour, Emote, Guild, Rgx, User, DIGITS
from utils.webhook import check_msg_react, user_webhook

if TYPE_CHECKING:
    from utils import AluContext


class Other(AluCog):
    @app_commands.command()
    async def coinflip(self, ntr: discord.Interaction):
        """Flip a coin: Heads or Tails?"""
        word = 'Heads' if randint(2) == 0 else 'Tails'
        return await ntr.response.send_message(content=word, file=discord.File(f'assets/images/coinflip/{word}.png'))

    @commands.Cog.listener()
    async def on_message(self, message: discord.Message):
        if message.author.id in [User.bot, User.yen]:
            return

        async def work_non_command_mentions(msg: discord.Message):
            """for now there is only blush and question marks"""
            if msg.guild and msg.guild.me in msg.mentions:
                if any([item in msg.content.lower() for item in ['😊', "blush"]]):
                    await msg.channel.send(f'{msg.author.mention} {Emote.peepoBlushDank}')
                else:
                    ctx = await self.bot.get_context(msg)
                    if ctx.command:
                        return
                    else:
                        for r in ['❔', '❕', '🤔']:
                            await msg.add_reaction(r)

        await work_non_command_mentions(message)

        async def bots_in_lobby(msg: discord.Message):
            if msg.channel.id == Channel.general:
                text = None
                if msg.interaction is not None and msg.interaction.type == discord.InteractionType.application_command:
                    text = 'Slash-commands'
                if msg.author.bot and not msg.webhook_id:
                    text = 'Bots'
                if text is not None:
                    await msg.channel.send('{0} in {1} ! {2} {2} {2}'.format(text, Channel.general.mention, Emote.Ree))

        await bots_in_lobby(message)

        async def weebs_out(msg: discord.Message):
            if msg.channel.id == Channel.weebs and randint(1, 100 + 1) < 7:
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
            if not msg.guild or msg.guild.id != Guild.community:
                return
            if "Oof" in msg.content:
                try:
                    await msg.add_reaction(Emote.Ree)
                except discord.errors.Forbidden:
                    await msg.delete()

        await ree_the_oof(message)

        async def random_comfy_react(msg: discord.Message):
            if not msg.guild or msg.guild.id != Guild.community:
                return
            roll = randint(1, 300 + 1)
            if roll < 2:
                try:
                    await msg.add_reaction(Emote.peepoComfy)
                except Exception:
                    return

        await random_comfy_react(message)

        async def your_life(msg):
            if not msg.guild or msg.guild.id != Guild.community or randint(1, 170 + 1) >= 2:
                return
            try:
                sliced_text = msg.content.split()
                if len(sliced_text) > 2:
                    answer_text = f"Your life {' '.join(sliced_text[2:])}"
                    await msg.channel.send(answer_text)
            except Exception:
                return

        await your_life(message)

    @app_commands.command()
    async def do_emote_spam(self, ntr: discord.Interaction):
        """Send 3x random emote into emote spam channel"""
        rand_guild = choice(self.bot.guilds)  # type: ignore #TODO:FIX
        rand_emoji = choice(rand_guild.emojis)
        answer_text = f'{str(rand_emoji)} ' * 3
        channel = self.community.emote_spam
        await channel.send(answer_text)
        e = discord.Embed(colour=Colour.prpl(), description=f'I sent {answer_text} into {channel.mention}')
        await ntr.response.send_message(embed=e, ephemeral=True, delete_after=10)

    @commands.hybrid_command(description='Send apuband emote combo')
    async def apuband(self, ctx: AluContext):
        """Send apuband emote combo"""
        guild = self.community.guild
        emote_names = ['peepo1Maracas', 'peepo2Drums', 'peepo3Piano', 'peepo4Guitar', 'peepo5Singer', 'peepo6Sax']
        content = ' '.join([str(discord.utils.get(guild.emojis, name=e)) for e in emote_names])
        await ctx.channel.send(content=content)
        if ctx.interaction:
            await ctx.reply(content=f'Nice {Emote.DankApprove}', ephemeral=True)
        else:
            await ctx.message.delete()

    @commands.hybrid_command(description='Roll an integer from 1 to `max_roll_number`')
    @app_commands.describe(max_roll_number="Max limit to roll")
    async def roll(self, ctx, max_roll_number: commands.Range[int, 1, None]):
        """Roll an integer from 1 to `max_roll_number` ;"""
        await ctx.reply(randint(1, max_roll_number + 1))

    @commands.hybrid_command(usage='[channel=curr] [text=Allo]', description='Echo something somewhere')
    @app_commands.describe(channel="Channel to send to")
    @app_commands.describe(text="Enter text to speak")
    async def echo(self, ctx: AluContext, channel: Optional[discord.TextChannel] = None, *, text: str = 'Allo'):
        """Send `text` to `#channel` and delete your invoking message,
        so it looks like the bot is speaking on its own.
        """
        ch = channel or ctx.channel
        if ch.id in [Channel.emote_spam, Channel.comfy_spam]:
            raise commands.MissingPermissions(
                [f'Sorry, these channels are special so you can\'t use this command in {ch.mention}']
            )
        elif not ch.permissions_for(ctx.author).send_messages:
            raise commands.MissingPermissions([f'Sorry, you don\'t have permissions to speak in {ch.mention}'])
        else:
            url_array = re.findall(Rgx.url_link, str(text))
            for url in url_array:  # forbid embeds
                text = text.replace(url, f'<{url}>')
            await ch.send(text)
            if ctx.interaction:
                await ctx.reply(content=f'I did it {Emote.DankApprove}', ephemeral=True)
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
            } | {str(i): n for i, n in enumerate(DIGITS)}
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
            await ctx.reply(content=Emote.DankApprove, ephemeral=True)
        else:
            await ctx.message.delete()

    @commands.Cog.listener()
    async def on_reaction_add(self, reaction, user):
        if str(reaction) == '\N{CROSS MARK}':
            if check_msg_react(user.id, reaction.message.id):
                await reaction.message.delete()
