from __future__ import annotations

import asyncio
import random
from typing import TYPE_CHECKING, Optional

import discord
import emoji
import regex
from discord.ext import commands, tasks

from utils import AluCog, const

from ._category import CommunityCog

if TYPE_CHECKING:
    from utils import AluBot


class EmoteSpam(CommunityCog):
    async def cog_load(self) -> None:
        self.emote_spam.start()
        self.offline_criminal_check.start()

    async def cog_unload(self) -> None:
        self.emote_spam.cancel()
        self.offline_criminal_check.cancel()

    async def is_message_allowed(self, message: discord.Message, nqn_check: int = 1) -> bool:
        if message.channel.id == const.Channel.emote_spam:
            if len(message.embeds) or len(message.stickers) or len(message.attachments):
                return False

            text = emoji.replace_emoji(message.content, replace='')  # standard emojis

            # there is definitely a better way to regex it out
            filters = [const.Rgx.whitespace, const.Rgx.emote_old, const.Rgx.nqn, const.Rgx.invis]
            if nqn_check == 0:
                filters.remove(const.Rgx.nqn)
            for item in filters:
                text = regex.sub(item, '', text)

            return not bool(text)  # if there is some text left then it's forbidden.  
        else:
            return True

    async def delete_the_message(self, message: discord.Message):
        try:
            await message.delete()
        except discord.NotFound:
            return
        channel: discord.TextChannel = message.channel  # type: ignore # channel is secured
        answer_text = "{0}, you are NOT allowed to use non-emotes in {1}. Emote-only channel ! {2} {2} {2}".format(
            message.author.mention, channel.mention, const.Emote.Ree
        )
        e = discord.Embed(title="Deleted message", description=message.content, color=const.Colour.prpl())
        e.set_author(name=message.author.display_name, icon_url=message.author.display_avatar.url)
        if s := message.stickers:
            e.set_thumbnail(url=s[0].url)
        await self.bot.community.bot_spam.send(answer_text, embed=e)

    async def emote_spam_work(self, message: discord.Message):
        is_allowed = await self.is_message_allowed(message, nqn_check=1)
        if is_allowed:
            await asyncio.sleep(10)
            is_allowed = await self.is_message_allowed(message, nqn_check=0)

        if not is_allowed:
            await self.delete_the_message(message)

    @commands.Cog.listener()
    async def on_message(self, message: discord.Message):
        await self.emote_spam_work(message)

    @commands.Cog.listener()
    async def on_message_edit(self, _before: discord.Message, after: discord.Message):
        await self.emote_spam_work(after)

    @tasks.loop(minutes=63)
    async def emote_spam(self):
        if random.randint(1, 100 + 1) < 2:
            while(True):
                rand_guild = random.choice(self.bot.guilds)
                if rand_guild.emojis:
                    # We need to do this loop in case some servers do not upload any emotes.
                    rand_emoji = random.choice(rand_guild.emojis)
                    if rand_emoji.is_usable():
                        break
            await self.bot.community.emote_spam.send('{0} {0} {0}'.format(str(rand_emoji)))

    @tasks.loop(count=1)
    async def offline_criminal_check(self):
        channel = self.bot.community.emote_spam
        async for message in channel.history(limit=2000):
            if message.author.id == self.bot.user.id:
                return
            if await self.emote_spam_work(message):
                text = f'Offline criminal found {const.Emote.peepoPolice}'
                await self.bot.community.bot_spam.send(content=text)

    @emote_spam.before_loop
    @offline_criminal_check.before_loop
    async def emote_spam_before(self):
        await self.bot.wait_until_ready()


class ComfySpam(AluCog):
    async def cog_load(self) -> None:
        self.comfy_spam.start()
        self.offline_criminal_check.start()

    async def cog_unload(self) -> None:
        self.comfy_spam.cancel()
        self.offline_criminal_check.cancel()

    comfy_emotes = [
        "<:peepoComfy:726438781208756288>",
        "<:_:726438781208756288>",
        "<:pepoblanket:595156413974577162>",
        "<:_:595156413974577162>",
    ]

    async def comfy_chat_control(self, message: discord.Message):
        if message.channel.id == const.Channel.comfy_spam:
            channel: discord.TextChannel = message.channel  # type: ignore
            if len(message.embeds):
                return await message.delete()
            text = str(message.content)
            text = regex.sub(const.Rgx.whitespace, '', text)
            for item in self.comfy_emotes:
                text = text.replace(item, "")
            if text:
                answer_text = (
                    "{0}, you are NOT allowed to use anything but truly the only one comfy-emote in {1} ! "
                    "{2} {2} {2}".format(message.author.mention, channel.mention, const.Emote.Ree)
                )
                e = discord.Embed(title="Deleted message", description=message.content, color=const.Colour.prpl())
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
        if random.randint(1, 100 + 1) < 2:
            await self.community.comfy_spam.send('{0} {0} {0}'.format(const.Emote.peepoComfy))

    @tasks.loop(count=1)
    async def offline_criminal_check(self):
        async for message in self.community.comfy_spam.history(limit=2000):
            if message.author.id == self.bot.user.id:
                return
            if await self.comfy_chat_control(message):
                text = f'Offline criminal found {const.Emote.peepoPolice}'
                await self.bot.community.bot_spam.send(content=text)

    @comfy_spam.before_loop
    @offline_criminal_check.before_loop
    async def comfy_spam_before(self):
        await self.bot.wait_until_ready()


async def setup(bot: AluBot):
    await bot.add_cog(EmoteSpam(bot))
    await bot.add_cog(ComfySpam(bot))
