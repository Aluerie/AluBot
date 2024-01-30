from __future__ import annotations

from typing import TYPE_CHECKING, Literal, NamedTuple

import discord
from discord import app_commands
from discord.ext import commands
from gtts import gTTS

from utils import const, errors

from ._base import VoiceChatCog

if TYPE_CHECKING:
    from bot import AluBot
    from utils import AluGuildContext


class LanguageData(NamedTuple):
    code: str
    locale: str
    lang: str
    tld: str


class LanguageCollection:
    fr = LanguageData(code="fr-FR", locale="French (France)", lang="fr", tld="fr")
    en = LanguageData(code="en-IE", locale="English (Ireland)", lang="en", tld="ie")
    ru = LanguageData(code="ru-Ru", locale="Russian (Russia)", lang="ru", tld="com")
    es = LanguageData(code="es-ES", locale="Spanish (Spain)", lang="es", tld="es")
    pt = LanguageData(code="pt-PT", locale="Portuguese (Portugal)", lang="pt", tld="pt")
    cn = LanguageData(code="zh-CN", locale="Mandarin (China Mainland)", lang="zh-CN", tld="com")
    uk = LanguageData(code="uk-UA", locale="Ukrainian (Ukraine)", lang="uk", tld="com.ua")

    Literal = Literal["fr", "en", "ru", "es", "pt", "cn", "uk"]


class TextToSpeech(VoiceChatCog, name="Text To Speech", emote=const.Emote.Ree):
    """Text To Speech commands.

    Make the bot talk in voice chat.
    """

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.connections: dict[int, discord.VoiceClient] = {}  # guild.id to Voice we are connected to

    @app_commands.guild_only()
    @commands.hybrid_group(name="text-to-speech", aliases=["tts", "voice"])
    async def tts_group(self, ctx: AluGuildContext):
        """Text-To-Speech commands."""
        await ctx.send_help(ctx.command)

    async def speak_worker(
        self,
        ctx: AluGuildContext,
        lang: LanguageData,
        *,
        text: str = "Allo",
    ):
        voice_state = ctx.author.voice
        if not voice_state:
            raise errors.ErroneousUsage("You aren't in a voice channel!")

        voice_client = ctx.guild.voice_client
        if voice_client is not None:
            vc = self.connections[ctx.guild.id]
            assert isinstance(voice_client, discord.VoiceClient)
            await voice_client.move_to(voice_state.channel)
        else:
            if not voice_state.channel:
                raise errors.ErroneousUsage("You aren't connected to a voice channel!")
            vc = await voice_state.channel.connect()  # Connect to the voice channel the author is in.
            self.connections.update({ctx.guild.id: vc})  # Updating the cache with the guild and channel.

        assert isinstance(vc, discord.VoiceClient)

        tts = gTTS(text, lang=lang.lang, tld=lang.tld)
        audio_name = ".alubot/audio.mp3"
        tts.save(audio_name)
        vc.play(discord.FFmpegPCMAudio(audio_name))

    @tts_group.command()
    @app_commands.describe(text="Enter text to speak", language="Choose language/accent")
    async def speak(self, ctx: AluGuildContext, language: LanguageCollection.Literal = "fr", *, text: str = "Allo"):
        """Make Text-To-Speech request into voice-chat."""
        lang: LanguageData = getattr(LanguageCollection, language)
        await self.speak_worker(ctx, lang, text=text)
        e = discord.Embed(title="Text-To-Speech request", description=text, colour=ctx.user.colour)
        e.set_author(name=ctx.user.display_name, icon_url=ctx.user.display_avatar.url)
        e.set_footer(text=f"{lang.code} Language: {lang.locale}")
        await ctx.reply(embed=e)

    @tts_group.command()
    async def stop(self, ctx: AluGuildContext):
        """Stop playing current audio. Useful if somebody is abusing TTS system with annoying requests."""
        try:
            vc = self.connections[ctx.guild.id]
        except KeyError:
            raise errors.ErroneousUsage("I'm not in voice channel")

        if vc.is_playing():
            vc.stop()
            e = discord.Embed(description="Stopped", colour=ctx.user.colour)
            await ctx.reply(embed=e)
        else:
            e = discord.Embed(description="I don't think I was talking", colour=const.Colour.maroon)
            await ctx.reply(embed=e, ephemeral=True)

    @tts_group.command()
    async def leave(self, ctx: AluGuildContext):
        """Make bot leave voice channel."""
        try:
            vc = self.connections[ctx.guild.id]
        except KeyError:
            raise errors.ErroneousUsage("I'm not in a voice channel.")

        await vc.disconnect()
        e = discord.Embed(description=f"I left {vc.channel.mention}", colour=ctx.user.colour)
        await ctx.reply(embed=e)

    @app_commands.guild_only()
    @commands.hybrid_command(name="bonjour")
    async def bonjour(self, ctx: AluGuildContext):
        """`Bonjour !` into both text/voice chats."""
        try:
            await self.speak_worker(ctx, LanguageCollection.fr, text="Bonjour !")
        except errors.ErroneousUsage:
            pass
        await ctx.reply(content=f"Bonjour {const.Emote.bubuAYAYA}")

    @commands.Cog.listener(name="on_voice_state_update")
    async def leave_when_everybody_else_disconnects(
        self,
        member: discord.Member,
        before: discord.VoiceState,
        _after: discord.VoiceState,
    ):
        if before.channel is not None and len([m for m in before.channel.members if not m.bot]) == 0:
            vc = self.connections.get(member.guild.id, None)
            if vc is not None:
                await vc.disconnect()


async def setup(bot: AluBot):
    await bot.add_cog(TextToSpeech(bot))
