from __future__ import annotations

import asyncio
from typing import TYPE_CHECKING

import discord
import emoji
import regex
from discord.ext import commands, tasks
from numpy.random import choice, randint

from utils.var import Cid, Clr, Ems, Rgx, Uid

from ._base import HideoutBase
from ._const import COMFY_SPAM, EMOTE_SPAM

if TYPE_CHECKING:
    from utils.bot import AluBot


class EmoteSpam(HideoutBase):
    async def cog_load(self) -> None:
        self.emote_spam.start()
        self.offline_criminal_check.start()

    async def cog_unload(self) -> None:
        self.emote_spam.cancel()
        self.offline_criminal_check.cancel()

    async def emote_spam_control(self, message: discord.Message, nqn_check: int = 1):
        if message.channel.id == EMOTE_SPAM:
            if len(message.embeds):
                return await message.delete()
            # emoji_regex = get_emoji_regexp()
            # text = emoji_regex.sub('', msg.content)  # standard emotes

            text = emoji.replace_emoji(message.content, replace='')  # type: ignore # ???
            filters = [Rgx.whitespaces, Rgx.emote, Rgx.nqn, Rgx.invis_symbol]
            if nqn_check == 0:
                filters.remove(Rgx.nqn)
            for item in filters:
                text = regex.sub(item, '', text)
            whitelisted = ['$doemotespam', '$apuband']
            for item in whitelisted:
                if text == item:
                    return

            if text:
                try:
                    await message.delete()
                except discord.NotFound:
                    return
                answer_text = (
                    "{0}, you are NOT allowed to use non-emotes in {1}. Emote-only channel ! {2} {2} {2}".format(
                        message.author.mention, message.channel.mention, Ems.Ree
                    )
                )
                e = discord.Embed(title="Deleted message", description=message.content, color=Clr.prpl)
                e.set_author(name=message.author.display_name, icon_url=message.author.display_avatar.url)
                await self.bot.get_channel(Cid.bot_spam).send(answer_text, embed=e)
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
                rand_guild = choice(guild_list)
                rand_emoji = choice(rand_guild.emojis)
                if rand_emoji.is_usable():
                    break
            await self.bot.get_channel(EMOTE_SPAM).send('{0} {0} {0}'.format(str(rand_emoji)))

    @emote_spam.before_loop
    async def before(self):
        await self.bot.wait_until_ready()

    @tasks.loop(count=1)
    async def offline_criminal_check(self):
        channel = self.bot.get_channel(EMOTE_SPAM)
        async for message in channel.history(limit=2000):
            if message.author.id == Uid.bot:
                return
            if await self.emote_spam_work(message):
                text = f'Offline criminal found {Ems.peepoPolice}'
                await self.bot.get_channel(Cid.bot_spam).send(content=text)

    @offline_criminal_check.before_loop
    async def before(self):
        await self.bot.wait_until_ready()


class ComfySpam(commands.Cog):
    def __init__(self, bot: AluBot):
        self.bot: AluBot = bot

    async def cog_load(self) -> None:
        self.comfy_spam.start()
        self.offline_criminal_check.start()

    async def cog_unload(self) -> None:
        self.comfy_spam.cancel()
        self.offline_criminal_check.cancel()

    async def comfy_chat_control(self, message: discord.Message):
        if message.channel.id == COMFY_SPAM:
            if len(message.embeds):
                return await message.delete()
            text = str(message.content)
            text = regex.sub(Rgx.whitespaces, '', text)
            for item in Ems.comfy_emotes:
                text = text.replace(item, "")
            if text:
                answer_text = (
                    "{0}, you are NOT allowed to use anything but truly the only one comfy-emote in {1} ! "
                    "{2} {2} {2}".format(message.author.mention, message.channel.mention, Ems.Ree)
                )
                e = discord.Embed(title="Deleted message", description=message.content, color=Clr.prpl)
                e.set_author(name=message.author.display_name, icon_url=message.author.display_avatar.url)
                await self.bot.get_channel(Cid.bot_spam).send(answer_text, embed=e)
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
            await self.bot.get_channel(COMFY_SPAM).send('{0} {0} {0}'.format(Ems.peepoComfy))

    @comfy_spam.before_loop
    async def before(self):
        await self.bot.wait_until_ready()

    @tasks.loop(count=1)
    async def offline_criminal_check(self):
        channel = self.bot.get_channel(COMFY_SPAM)
        async for message in channel.history(limit=2000):
            if message.author.id == Uid.bot:
                return
            if await self.comfy_chat_control(message):
                text = f'Offline criminal found {Ems.peepoPolice}'
                await self.bot.get_channel(Cid.bot_spam).send(content=text)

    @offline_criminal_check.before_loop
    async def before(self):
        await self.bot.wait_until_ready()


async def setup(bot: AluBot):
    await bot.add_cog(EmoteSpam(bot))
    await bot.add_cog(ComfySpam(bot))
