from __future__ import annotations

import asyncio
from typing import TYPE_CHECKING

import discord
import emoji
import regex
from discord.ext import commands, tasks
from numpy.random import choice, randint

from utils.const.community import COMFY_SPAM, EMOTE_SPAM
from utils.var import Clr, Ems, Rgx, Uid

from utils import AluCog

if TYPE_CHECKING:
    from utils import AluBot


class EmoteSpam(AluCog):
    async def cog_load(self) -> None:
        self.emote_spam.start()
        self.offline_criminal_check.start()

    async def cog_unload(self) -> None:
        self.emote_spam.cancel()
        self.offline_criminal_check.cancel()

    async def emote_spam_control(self, message: discord.Message, nqn_check: int = 1):
        if message.channel.id == EMOTE_SPAM:
            channel: discord.TextChannel = message.channel  # type: ignore
            if len(message.embeds):
                return await message.delete()
            # emoji_regex = get_emoji_regexp()
            # text = emoji_regex.sub('', msg.content)  # standard emotes

            text = emoji.replace_emoji(message.content, replace='')
            filters = [Rgx.whitespaces, Rgx.emote, Rgx.nqn, Rgx.invis_symbol]
            if nqn_check == 0:
                filters.remove(Rgx.nqn)
            for item in filters:
                text = regex.sub(item, '', text)

            if text:
                try:
                    await message.delete()
                except discord.NotFound:
                    return
                answer_text = (
                    "{0}, you are NOT allowed to use non-emotes in {1}. Emote-only channel ! {2} {2} {2}".format(
                        message.author.mention, channel.mention, Ems.Ree
                    )
                )
                e = discord.Embed(title="Deleted message", description=message.content, color=Clr.prpl)
                e.set_author(name=message.author.display_name, icon_url=message.author.display_avatar.url)
                await self.bot.community.bot_spam.send(answer_text, embed=e)
                return 1
            else:
                return 0

    async def emote_spam_work(self, message):
        await self.emote_spam_control(message, nqn_check=1)
        await asyncio.sleep(10)
        await self.emote_spam_control(message, nqn_check=0)

    @commands.Cog.listener()
    async def on_message(self, message):
        await self.emote_spam_work(message)

    @commands.Cog.listener()
    async def on_message_edit(self, _before, after):
        await self.emote_spam_work(after)

    @tasks.loop(minutes=63)
    async def emote_spam(self):
        if randint(1, 100 + 1) < 2:
            while True:
                guild_list = self.bot.guilds
                rand_guild = choice(guild_list)  # type: ignore # TODO:FIX
                rand_emoji = choice(rand_guild.emojis)
                if rand_emoji.is_usable():
                    break
            await self.bot.community.emote_spam.send('{0} {0} {0}'.format(str(rand_emoji)))

    @emote_spam.before_loop
    async def emote_spam_before(self):
        await self.bot.wait_until_ready()

    @tasks.loop(count=1)
    async def offline_criminal_check(self):
        channel = self.bot.community.emote_spam
        async for message in channel.history(limit=2000):
            if message.author.id == Uid.bot:
                return
            if await self.emote_spam_work(message):
                text = f'Offline criminal found {Ems.peepoPolice}'
                await self.bot.community.bot_spam.send(content=text)

    @offline_criminal_check.before_loop
    async def before(self):
        await self.bot.wait_until_ready()


class ComfySpam(AluCog):

    async def cog_load(self) -> None:
        self.comfy_spam.start()
        self.offline_criminal_check.start()

    async def cog_unload(self) -> None:
        self.comfy_spam.cancel()
        self.offline_criminal_check.cancel()

    async def comfy_chat_control(self, message: discord.Message):
        if message.channel.id == COMFY_SPAM:
            channel: discord.TextChannel = message.channel  # type: ignore
            if len(message.embeds):
                return await message.delete()
            text = str(message.content)
            text = regex.sub(Rgx.whitespaces, '', text)
            for item in Ems.comfy_emotes:
                text = text.replace(item, "")
            if text:
                answer_text = (
                    "{0}, you are NOT allowed to use anything but truly the only one comfy-emote in {1} ! "
                    "{2} {2} {2}".format(message.author.mention, channel.mention, Ems.Ree)
                )
                e = discord.Embed(title="Deleted message", description=message.content, color=Clr.prpl)
                e.set_author(name=message.author.display_name, icon_url=message.author.display_avatar.url)
                await self.bot.community.bot_spam.send(answer_text, embed=e)
                await message.delete()
                return 1
            else:
                return 0

    @commands.Cog.listener()
    async def on_message(self, message: discord.Message):
        await self.comfy_chat_control(message)

    @commands.Cog.listener()
    async def on_message_edit(self, _before: discord.Message, after: discord.Message):
        await self.comfy_chat_control(after)

    @tasks.loop(minutes=60)
    async def comfy_spam(self):
        if randint(1, 100 + 1) < 2:
            await self.bot.community.comfy_spam.send('{0} {0} {0}'.format(Ems.peepoComfy))

    @comfy_spam.before_loop
    async def comfy_spam_before(self):
        await self.bot.wait_until_ready()

    @tasks.loop(count=1)
    async def offline_criminal_check(self):
        async for message in self.bot.community.comfy_spam.history(limit=2000):
            if message.author.id == Uid.bot:
                return
            if await self.comfy_chat_control(message):
                text = f'Offline criminal found {Ems.peepoPolice}'
                await self.bot.community.bot_spam.send(content=text)

    @offline_criminal_check.before_loop
    async def before(self):
        await self.bot.wait_until_ready()


async def setup(bot: AluBot):
    await bot.add_cog(EmoteSpam(bot))
    await bot.add_cog(ComfySpam(bot))
