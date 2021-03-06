from discord import Embed
from discord.ext import commands, tasks
from utils.var import Cid, Clr, Ems, Rgx, Sid, Uid

import regex
from numpy.random import randint, choice
import asyncio
from emoji import get_emoji_regexp


class EmoteSpam(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.emote_spam.start()
        self.offline_criminal_check.start()

    async def emote_spam_control(self, msg):
        if msg.channel.id == Cid.emote_spam:
            if len(msg.embeds):
                return await msg.delete()
            emoji_regex = get_emoji_regexp()
            text = emoji_regex.sub('', msg.content)  # standard emotes
            filters = [Rgx.whitespaces, Rgx.emote, Rgx.nqn, Rgx.invis_symb]
            for item in filters:
                text = regex.sub(item, '', text)
            whitelisted = ['$doemotespam', '$apuband']
            for item in whitelisted:
                if text == item:
                    return
            if text:
                answer_text = "{0}, you are NOT allowed to use non-emotes in {1}. Emote-only channel ! {2} {2} {2}"\
                    .format(msg.author.mention, msg.channel.mention, Ems.Ree)
                embed = Embed(title="Deleted message", description=msg.content, color=Clr.prpl)
                embed.set_author(name=msg.author.display_name, icon_url=msg.author.display_avatar.url)
                await self.bot.get_channel(Cid.bot_spam).send(answer_text, embed=embed)
                await msg.delete()
                return 1
            else:
                return 0

    async def bug_abuse_check(self, msg):
        if msg.channel.id == Cid.emote_spam:
            emoji_regex = get_emoji_regexp()
            text = emoji_regex.sub('', msg.content)  # standard emotes
            text = regex.sub(Rgx.whitespaces, '', text)
            if not text:
                return

            text = regex.sub(Rgx.bug_check, '', text)
            if not text:
                answer_text = "{0}, it seems like you were trying to abuse the bug in {1}. Reee ! {2} {2} {2}".format(
                    msg.author.mention, msg.channel.mention, Ems.Ree)
                embed = Embed(title="Deleted message", description=msg.content, color=Clr.prpl)
                embed.set_author(name=msg.author.display_name, icon_url=msg.author.display_avatar.url)
                try:
                    await msg.delete()
                    await self.bot.get_channel(Cid.bot_spam).send(answer_text, embed=embed)
                    return 1
                except:
                    return
            else:
                return 0

    @commands.Cog.listener()
    async def on_message(self, message):
        await self.emote_spam_control(message)
        await asyncio.sleep(10)
        await self.bug_abuse_check(message)

    @commands.Cog.listener()
    async def on_message_edit(self, before, after):
        await self.emote_spam_control(after)
        await asyncio.sleep(10)
        await self.bug_abuse_check(after)

    @tasks.loop(minutes=63)
    async def emote_spam(self):
        if randint(1, 100 + 1) < 2:
            while True:
                guild_list = self.bot.guilds
                rand_guild = choice(guild_list)
                rand_emoji = choice(rand_guild.emojis)
                if rand_emoji.is_usable():
                    break
            await self.bot.get_channel(Cid.emote_spam).send('{0} {0} {0}'.format(str(rand_emoji)))

    @emote_spam.before_loop
    async def before(self):
        await self.bot.wait_until_ready()

    @tasks.loop(count=1)
    async def offline_criminal_check(self):
        channel = self.bot.get_channel(Cid.emote_spam)
        async for message in channel.history(limit=2000):
            if message.author.id == Uid.bot:
                return
            if await self.emote_spam_control(message) or await self.bug_abuse_check(message):
                text = f'Offline criminal found {Ems.peepoPolice}'
                await self.bot.get_channel(Cid.bot_spam).send(content=text)

    @offline_criminal_check.before_loop
    async def before(self):
        await self.bot.wait_until_ready()


class ComfySpam(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.comfy_spam.start()
        self.offline_criminal_check.start()

    async def comfy_chat_control(self, msg):
        if msg.channel.id == Cid.comfy_spam:
            if len(msg.embeds):
                return await msg.delete()
            text = str(msg.content)
            text = regex.sub(Rgx.whitespaces, '', text)
            for item in Ems.comfy_emotes:
                text = text.replace(item, "")
            if text:
                answer_text = "{0}, you are NOT allowed to use anything but truly the only one comfy-emote in {1} ! " \
                              "{2} {2} {2}".format(msg.author.mention, msg.channel.mention, Ems.Ree)
                embed = Embed(title="Deleted message", description=msg.content, color=Clr.prpl)
                embed.set_author(name=msg.author.display_name, icon_url=msg.author.display_avatar.url)
                await self.bot.get_channel(Cid.bot_spam).send(answer_text, embed=embed)
                await msg.delete()
                return 1
            else:
                return 0

    @commands.Cog.listener()
    async def on_message(self, message):
        await self.comfy_chat_control(message)

    @commands.Cog.listener()
    async def on_message_edit(self, before, after):
        await self.comfy_chat_control(after)

    @tasks.loop(minutes=60)
    async def comfy_spam(self):
        if randint(1, 100 + 1) < 2:
            await self.bot.get_channel(Cid.comfy_spam).send('{0} {0} {0}'.format(Ems.peepoComfy))

    @comfy_spam.before_loop
    async def before(self):
        await self.bot.wait_until_ready()

    @tasks.loop(count=1)
    async def offline_criminal_check(self):
        channel = self.bot.get_channel(Cid.comfy_spam)
        async for message in channel.history(limit=2000):
            if message.author.id == Uid.bot:
                return
            if await self.comfy_chat_control(message):
                text = f'Offline criminal found {Ems.peepoPolice}'
                await self.bot.get_channel(Cid.bot_spam).send(content=text)

    @offline_criminal_check.before_loop
    async def before(self):
        await self.bot.wait_until_ready()


async def setup(bot):
    await bot.add_cog(EmoteSpam(bot))
    await bot.add_cog(ComfySpam(bot))
