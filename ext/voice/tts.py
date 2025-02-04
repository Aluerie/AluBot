from __future__ import annotations

from typing import TYPE_CHECKING, Any, Literal, NamedTuple

import discord
from discord import app_commands
from discord.ext import commands
from gtts import gTTS

from utils import const, errors

from ._base import VoiceChatCog

if TYPE_CHECKING:
    from bot import AluBot


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

    def __init__(self, *args: Any, **kwargs: Any) -> None:
        super().__init__(*args, **kwargs)
        self.connections: dict[int, discord.VoiceClient] = {}  # guild.id to Voice we are connected to

    tts_group = app_commands.Group(
        name="text-to-speech",
        description="\N{STUDIO MICROPHONE} Make the bot join voice channels and do some talking.",
        guild_only=True,
    )

    async def speak_worker(
        self,
        interaction: discord.Interaction[AluBot],
        lang: LanguageData,
        *,
        text: str = "Allo",
    ) -> None:
        assert isinstance(interaction.user, discord.Member)
        voice_state = interaction.user.voice
        if not voice_state:
            msg = "You aren't in a voice channel!"
            raise errors.ErroneousUsage(msg)

        assert interaction.guild
        voice_client = interaction.guild.voice_client
        if voice_client is not None:
            vc = self.connections[interaction.guild.id]
            assert isinstance(voice_client, discord.VoiceClient)
            await voice_client.move_to(voice_state.channel)
        else:
            if not voice_state.channel:
                msg = "You aren't connected to a voice channel!"
                raise errors.ErroneousUsage(msg)
            vc = await voice_state.channel.connect()  # Connect to the voice channel the author is in.
            self.connections.update({interaction.guild.id: vc})  # Updating the cache with the guild and channel.

        assert isinstance(vc, discord.VoiceClient)

        tts = gTTS(text, lang=lang.lang, tld=lang.tld)
        audio_name = ".alubot/audio.mp3"
        tts.save(audio_name)
        vc.play(discord.FFmpegPCMAudio(audio_name))

    @tts_group.command(name="speak")
    @app_commands.describe()
    async def tts_speak(
        self,
        interaction: discord.Interaction[AluBot],
        language: LanguageCollection.Literal = "fr",
        text: str = "Allo",
    ) -> None:
        """\N{STUDIO MICROPHONE} Make Text-To-Speech request for the voice-chat.

        Parameters
        ----------
        text
            Enter text for the bot to speak.
        language
            Choose language/accent.
        """
        lang: LanguageData = getattr(LanguageCollection, language)
        await self.speak_worker(interaction, lang, text=text)
        embed = (
            discord.Embed(
                colour=interaction.user.colour,
                title="Text-To-Speech request",
                description=text,
            )
            .set_author(name=interaction.user.display_name, icon_url=interaction.user.display_avatar.url)
            .set_footer(text=f"{lang.code} Language: {lang.locale}")
        )
        await interaction.response.send_message(embed=embed)

    @tts_group.command()
    async def stop(self, interaction: discord.Interaction[AluBot]) -> None:
        """\N{STUDIO MICROPHONE} Stop playing current audio. Useful if somebody is abusing TTS system."""
        assert interaction.guild
        try:
            vc = self.connections[interaction.guild.id]
        except KeyError:
            msg = "I'm not in voice channel"
            raise errors.ErroneousUsage(msg) from None

        if vc.is_playing():
            vc.stop()
            embed = discord.Embed(description="Stopped", colour=interaction.user.colour)
            await interaction.response.send_message(embed=embed)
        else:
            embed = discord.Embed(description="I don't think I was talking", colour=const.Colour.maroon)
            await interaction.response.send_message(embed=embed, ephemeral=True)

    @tts_group.command()
    async def leave(self, interaction: discord.Interaction[AluBot]) -> None:
        """\N{STUDIO MICROPHONE} Make the bot leave the voice channel."""
        assert interaction.guild
        try:
            vc = self.connections[interaction.guild.id]
        except KeyError:
            msg = "I'm not in a voice channel."
            raise errors.ErroneousUsage(msg) from None

        await vc.disconnect()
        embed = discord.Embed(description=f"I left {vc.channel.mention}", colour=interaction.user.colour)
        await interaction.response.send_message(embed=embed)

    @tts_group.command(name="bonjour")
    async def tts_bonjour(self, interaction: discord.Interaction[AluBot]) -> None:
        """\N{STUDIO MICROPHONE} Make the bot say "Bonjour !" into both text/voice chats (that you're connected to)."""
        await self.speak_worker(interaction, LanguageCollection.fr, text="Bonjour !")
        await interaction.response.send_message(content=f"Bonjour {const.Emote.bubuAYAYA}")

    @commands.Cog.listener(name="on_voice_state_update")
    async def leave_when_everybody_else_disconnects(
        self,
        member: discord.Member,
        before: discord.VoiceState,
        _after: discord.VoiceState,
    ) -> None:
        if before.channel is not None and len([m for m in before.channel.members if not m.bot]) == 0:
            vc = self.connections.get(member.guild.id, None)
            if vc is not None:
                await vc.disconnect()


async def setup(bot: AluBot) -> None:
    """Load AluBot extension. Framework of discord.py."""
    await bot.add_cog(TextToSpeech(bot))
