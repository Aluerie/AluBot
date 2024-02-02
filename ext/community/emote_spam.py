from __future__ import annotations

import asyncio
import itertools
import random
import re
from typing import TYPE_CHECKING, Literal, override

import discord
import emoji
from discord.ext import commands, tasks

from utils import cache, const

from ._base import CommunityCog

if TYPE_CHECKING:
    from bot import AluBot
    from utils import AluContext


class EmoteSpam(CommunityCog):
    @override
    async def cog_load(self) -> None:
        self.emote_spam.start()
        self.offline_criminal_check.start()

    @override
    async def cog_unload(self) -> None:
        self.emote_spam.cancel()
        self.offline_criminal_check.cancel()

    async def is_message_allowed(self, message: discord.Message, nqn_check: int = 1) -> bool:
        if message.channel.id == const.Channel.emote_spam:
            if len(message.embeds) or len(message.stickers) or len(message.attachments):
                return False

            text = emoji.replace_emoji(message.content, replace="")  # standard emojis

            # there is definitely a better way to regex it out
            filters = [const.Regex.WHITESPACE, const.Regex.EMOTE_OLD, const.Regex.NQN, const.Regex.INVIS]
            if nqn_check == 0:
                filters.remove(const.Regex.NQN)
            for item in filters:
                text = re.sub(item, "", text)

            return not bool(text)  # if there is some text left then it's forbidden.
        else:
            return True

    async def delete_the_message(self, message: discord.Message) -> None:
        try:
            await message.delete()
        except discord.NotFound:
            return
        channel: discord.TextChannel = message.channel  # type: ignore # emote_spam channel is secured
        answer_text = "{0}, you are NOT allowed to use non-emotes in {1}. Emote-only channel ! {2} {2} {2}".format(
            message.author.mention, channel.mention, const.Emote.Ree
        )
        e = discord.Embed(title="Deleted message", description=message.content, color=const.Colour.maroon)
        e.set_author(name=message.author.display_name, icon_url=message.author.display_avatar.url)
        if s := message.stickers:
            e.set_thumbnail(url=s[0].url)
        await self.bot.community.bot_spam.send(answer_text, embed=e)

    async def emote_spam_work(self, message: discord.Message) -> None:
        is_allowed = await self.is_message_allowed(message, nqn_check=1)
        if is_allowed:
            await asyncio.sleep(10)
            is_allowed = await self.is_message_allowed(message, nqn_check=0)

        if not is_allowed:
            await self.delete_the_message(message)

    @commands.Cog.listener()
    async def on_message(self, message: discord.Message) -> None:
        await self.emote_spam_work(message)

    @commands.Cog.listener()
    async def on_message_edit(self, before: discord.Message, after: discord.Message) -> None:
        await self.emote_spam_work(after)

    @cache.cache(maxsize=60 * 24, strategy=cache.Strategy.lru)
    async def get_all_emotes(self) -> list[discord.Emoji]:
        """Get all emotes available to the bot."""
        return list(itertools.chain.from_iterable(guild.emojis for guild in self.bot.guilds))

    async def get_random_emote(self) -> discord.Emoji:
        """Get a random discord emote from one of discord servers the bot is in."""

        # Note: hmm, maybe we need to do some privacy check?
        # what if server owner doesn't want me to use their emotes.

        all_emotes: list[discord.Emoji] = await self.get_all_emotes()
        while True:
            random_emote = random.choice(all_emotes)
            if random_emote.is_usable():
                # in theory we are f*ked if there is not a single usable emote,
                # but my server will always have one :D
                return random_emote

    @tasks.loop(minutes=63)
    async def emote_spam(self) -> None:
        if random.randint(1, 100 + 1) < 2:
            emote = await self.get_random_emote()
            await self.bot.community.emote_spam.send(f"{emote!s} {emote!s} {emote!s}")

    @commands.hybrid_command()
    async def do_emote_spam(self, ctx: AluContext) -> None:
        """Send 3x random emote into emote spam channel"""

        emote = await self.get_random_emote()
        channel = self.community.emote_spam
        content = f"{emote!s} {emote!s} {emote!s}"
        await channel.send(content)
        e = discord.Embed(colour=const.Colour.blueviolet, description=f"I sent {content} into {channel.mention}")
        await ctx.reply(embed=e, ephemeral=True, delete_after=10)

    @tasks.loop(count=1)
    async def offline_criminal_check(self) -> None:
        channel = self.bot.community.emote_spam
        async for message in channel.history(limit=2000):
            if message.author.id == self.bot.user.id:
                return
            if await self.emote_spam_work(message):
                text = f"Offline criminal found {const.Emote.peepoPolice}"
                await self.community.bot_spam.send(content=text)

    @emote_spam.before_loop
    @offline_criminal_check.before_loop
    async def emote_spam_before(self) -> None:
        await self.bot.wait_until_ready()


class ComfySpam(CommunityCog):
    @override
    async def cog_load(self) -> None:
        self.comfy_spam.start()
        self.offline_criminal_check.start()

    @override
    async def cog_unload(self) -> None:
        self.comfy_spam.cancel()
        self.offline_criminal_check.cancel()

    comfy_emotes = (
        "<:peepoComfy:726438781208756288>",
        "<:_:726438781208756288>",
        "<:pepoblanket:595156413974577162>",
        "<:_:595156413974577162>",
    )

    async def comfy_chat_control(self, message: discord.Message) -> Literal[0, 1] | None:
        if message.channel.id == const.Channel.comfy_spam:
            channel: discord.TextChannel = message.channel  # type: ignore
            if len(message.embeds):
                await message.delete()
                return
            text = str(message.content)
            text = re.sub(const.Regex.WHITESPACE, "", text)
            for item in self.comfy_emotes:
                text = text.replace(item, "")
            if text:
                answer_text = (
                    "{0}, you are NOT allowed to use anything but truly the only one comfy-emote in {1} ! "
                    "{2} {2} {2}".format(message.author.mention, channel.mention, const.Emote.Ree)
                )
                e = discord.Embed(title="Deleted message", description=message.content, color=const.Colour.blueviolet)
                e.set_author(name=message.author.display_name, icon_url=message.author.display_avatar.url)
                await self.bot.community.bot_spam.send(answer_text, embed=e)
                await message.delete()
                return 1
            else:
                return 0

    @commands.Cog.listener()
    async def on_message(self, message: discord.Message) -> None:
        await self.comfy_chat_control(message)

    @commands.Cog.listener()
    async def on_message_edit(self, before: discord.Message, after: discord.Message) -> None:
        await self.comfy_chat_control(after)

    @tasks.loop(minutes=62)
    async def comfy_spam(self) -> None:
        if random.randint(1, 100 + 1) < 2:
            await self.community.comfy_spam.send("{0} {0} {0}".format(const.Emote.peepoComfy))

    @tasks.loop(count=1)
    async def offline_criminal_check(self) -> None:
        async for message in self.community.comfy_spam.history(limit=2000):
            if message.author.id == self.bot.user.id:
                return
            if await self.comfy_chat_control(message):
                text = f"Offline criminal found {const.Emote.peepoPolice}"
                await self.bot.community.bot_spam.send(content=text)

    @comfy_spam.before_loop
    @offline_criminal_check.before_loop
    async def comfy_spam_before(self) -> None:
        await self.bot.wait_until_ready()


async def setup(bot: AluBot) -> None:
    await bot.add_cog(EmoteSpam(bot))
    await bot.add_cog(ComfySpam(bot))
