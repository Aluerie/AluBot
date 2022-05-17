from __future__ import annotations
from typing import TYPE_CHECKING, Optional

from discord import Embed, File, TextChannel, app_commands, errors, utils
from discord.ext import commands

from utils.var import *
from utils.webhook import user_webhook, check_msg_react

from numpy.random import randint, choice
import re

if TYPE_CHECKING:
    from discord import Message


class FunThings(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.help_category = 'Fun'

    @commands.hybrid_command(
        aliases=['cf'],
        brief=Ems.slash,
        description='Flip a coin: Heads or Tails?'
    )
    async def coinflip(self, ctx):
        """Flip a coin ;"""
        word = 'Heads' if randint(2) == 0 else 'Tails'
        return await ctx.reply(content=word, file=File(f'media/{word}.png'))

    @commands.Cog.listener()
    async def on_message(self, message: Message):
        if message.author.id in [Uid.bot, Uid.yen]:
            return

        async def peepoblush(msg):
            if msg.guild.me in msg.mentions:
                if any([item in msg.content.lower() for item in ['😊', "blush"]]):
                    await msg.channel.send(f'{msg.author.mention} {Ems.peepoBlushDank}')
        await peepoblush(message)

        async def bots_in_lobby(msg):
            # https://docs.pycord.dev/en/master/api.html?highlight=interaction#discord.InteractionType
            # i dont like == 2 usage bcs it should be something like == discord.InteractionType.application_command
            if msg.channel.id == Cid.general:
                text = None
                if msg.interaction is not None and msg.interaction.type == 2:
                    text = 'Slash-commands'
                if msg.author.bot and not msg.webhook_id:
                    text = 'Bots'
                if text is not None:
                    await msg.channel.send('{0} in {1} ! {2} {2} {2}'.format(text, msg.channel.mention, Ems.Ree))
        await bots_in_lobby(message)

        async def weebs_out(msg):
            if msg.channel.id == Cid.weebs and randint(1, 100 + 1) < 7:
                await self.bot.get_channel(Cid.weebs).send(
                    '{0} {0} {0} {1} {1} {1} {2} {2} {2} {3} {3} {3}'.format(
                        '<a:WeebsOutOut:730882034167185448>', '<:WeebsOut:856985447985315860>',
                        '<a:peepoWeebSmash:728671752414167080>', '<:peepoRiot:730883102678974491>'))
        await weebs_out(message)

        async def ree_the_oof(msg):
            if "Oof" in msg.content:
                try:
                    await msg.add_reaction(Ems.Ree)
                except errors.Forbidden:
                    await msg.delete()
        await ree_the_oof(message)

        async def random_comfy_react(msg):
            roll = randint(1, 300 + 1)
            if roll < 2:
                try:
                    await msg.add_reaction(Ems.peepoComfy)
                except Exception:
                    return
        await random_comfy_react(message)

        async def yourlife(msg):
            if msg.guild.id != Sid.irene or randint(1, 200 + 1) >= 2:
                return
            try:
                sliced_text = msg.content.split()
                if len(sliced_text) > 2:
                    answer_text = f"Your life {' '.join(sliced_text[2:])}"
                    await msg.channel.send(answer_text)
            except Exception:
                return
        await yourlife(message)

    @commands.hybrid_command(
        brief=Ems.slash,
        description='Send 3x random emote into #emote_spam channel',
        help=f'Send 3x random emote into {cmntn(Cid.emote_spam)} ;'
    )
    async def doemotespam(self, ctx):
        """ Read above ;"""
        rand_guild = choice(self.bot.guilds)
        rand_emoji = choice(rand_guild.emojis)
        answer_text = f'{str(rand_emoji)} ' * 3
        emot_ch = self.bot.get_channel(Cid.emote_spam)
        await emot_ch.send(answer_text)
        em = Embed(colour=Clr.prpl, description=f'I sent {answer_text} into {emot_ch.mention}')
        await ctx.reply(embed=em, ephemeral=True, delete_after=10)
        if not ctx.interaction:
            await ctx.message.delete()

    @commands.hybrid_command(
        brief=Ems.slash,
        description='Send apuband emote combo'
    )
    async def apuband(self, ctx):
        """Send apuband emote combo ;"""
        irene_server = self.bot.get_guild(Sid.irene)
        emote_names = ['peepo1Maracas', 'peepo2Drums', 'peepo3Piano', 'peepo4Guitar', 'peepo5Singer', 'peepo6Sax']
        content = ' '.join([str(utils.get(irene_server.emojis, name=e)) for e in emote_names])
        await ctx.channel.send(content=content)
        if ctx.interaction:
            await ctx.reply(content=f'Nice {Ems.DankApprove}', ephemeral=True)
        else:
            await ctx.message.delete()

    @commands.hybrid_command(
        brief=Ems.slash,
        description='Roll an integer from 1 to `max_roll_number`'
    )
    @app_commands.describe(max_roll_number="Max limit to roll")
    async def roll(self, ctx, max_roll_number: int = 100):
        """Roll an integer from 1 to `max_roll_number` ;"""
        await ctx.reply(randint(1, int(max_roll_number) + 1))

    @commands.hybrid_command(
        brief=Ems.slash,
        usage='[channel=curr] [text=Allo]',
        description='Echo something somewhere'
    )
    @app_commands.describe(channel="Channel to send to")
    @app_commands.describe(text="Enter text to speak")
    async def echo(self, ctx, channel: Optional[TextChannel] = None, *, text: str = f'Allo'):
        """Send `text` to `#channel` and delete your invoking message, so it looks like \
        the bot is speaking on its own ;"""
        channel = channel or ctx.message.channel
        if channel.permissions_for(ctx.author).send_messages:
            url_array = re.findall(Rgx.url_danny, str(text))
            for url in url_array:  # forbid embeds
                text = text.replace(url, f'<{url}>')
            await channel.send(text)
            if ctx.interaction:
                await ctx.reply(content=Ems.DankApprove, ephemeral=True)
        else:
            embed = Embed(colour=Clr.rspbrry).set_author(name='PermissionError')
            embed.description = f'Sorry, you don\'t have permissions to speak in {channel.mention}'
            embed.set_footer(text='Probably that channel is read-only mode for you')
            return await ctx.reply(embed=embed)
        try:
            await ctx.message.delete()
        except:
            pass

    @commands.hybrid_command(
        name='emoteit',
        brief=Ems.slash,
        aliases=['emotialize'],
        description="Emotializes your text into standard emotes"
    )
    @app_commands.describe(text="Text that will be converted into emotes")
    async def emoteit(self, ctx, *, text: str):
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

            emotialize_dict = {  # [f'{chr(0x30 + i)}{chr(0x20E3)}' for i in range(10)] < also numbers but from chars
                ' ': ' ', '!': ':grey_exclamation:', '?': ':grey_question:', '0': '0️⃣', '1': '1️⃣',
                '2': '2️⃣', '3': '3️⃣', '4': '4️⃣', '5': '5️⃣', '6': '6️⃣', '7': '7️⃣', '8': '8️⃣', '9': '9️⃣'
            }
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
        if str(reaction) == '❌':
            if check_msg_react(user.id, reaction.message.id):
                await reaction.message.delete()


async def setup(bot):
    await bot.add_cog(FunThings(bot))
