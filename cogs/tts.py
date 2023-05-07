from __future__ import annotations

import typing
from typing import TYPE_CHECKING, Dict, Literal, NamedTuple

import discord
from discord import app_commands
from discord.ext import commands
from gtts import gTTS

from utils import AluCog
from utils.const import Colour, Emote

if TYPE_CHECKING:
    from utils import AluBot


class LanguageData(NamedTuple):
    code: str
    locale: str
    lang: str
    tld: str


class LanguageCollection:
    fr = LanguageData(code='fr-FR', locale='French (France)', lang='fr', tld='fr')
    en = LanguageData(code='en-IE', locale='English (Ireland)', lang='en', tld='ie')
    ru = LanguageData(code='ru-Ru', locale='Russian (Russia)', lang='ru', tld='com')
    es = LanguageData(code='es-ES', locale='Spanish (Spain)', lang='es', tld='es')
    pt = LanguageData(code='pt-PT', locale='Portuguese (Portugal)', lang='pt', tld='pt')
    cn = LanguageData(code='zh-CN', locale='Mandarin (China Mainland)', lang='zh-CN', tld='com')
    uk = LanguageData(code='uk-UA', locale='Ukrainian (Ukraine)', lang='uk', tld='com.ua')

    Literal = Literal['fr', 'en', 'ru', 'es', 'pt', 'cn', 'uk']


class TextToSpeech(AluCog, name='TTS', emote=Emote.Ree):
    """Text To Speech commands.

    Make the bot talk in voice chat.
    """

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.connections: Dict[int, discord.VoiceClient] = {}  # guild.id to Voice we are connected to

    tts_group = app_commands.Group(name="tts", description="Group command about TTS commands", guild_only=True)

    @tts_group.command()
    @app_commands.describe(text="Enter text to speak", language="Choose language/accent")
    async def speak(self, ntr: discord.Interaction, language: LanguageCollection.Literal = 'fr', *, text: str = 'Allo'):
        """Make Text-To-Speech request into voice-chat."""
        assert ntr.guild is not None

        lang: LanguageData = getattr(LanguageCollection, language)

        if not (member := ntr.guild.get_member(ntr.user.id)):
            # TODO: raise better error type
            raise commands.BadArgument('Something went wrong.')

        if not (voice_state := member.voice):
            # TODO: raise better error type
            raise commands.BadArgument("You aren't in a voice channel!")

        if (voice_client := ntr.guild.voice_client) is not None:
            vc = self.connections[ntr.guild.id]
            assert isinstance(voice_client, discord.VoiceClient)
            await voice_client.move_to(voice_state.channel)
        else:
            if not voice_state.channel:
                # TODO: raise better error type
                raise commands.BadArgument("You aren't connected to a voice channel!")
            vc = await voice_state.channel.connect()  # Connect to the voice channel the author is in.
            self.connections.update({ntr.guild.id: vc})  # Updating the cache with the guild and channel.

        assert isinstance(vc, discord.VoiceClient)

        tts = gTTS(text, lang=lang.lang, tld=lang.tld)
        audio_name = "./.temp/audio.mp3"
        tts.save(audio_name)
        vc.play(discord.FFmpegPCMAudio(audio_name))

        e = discord.Embed(title='Text-To-Speech request', description=text, colour=ntr.user.colour)
        e.set_author(name=ntr.user.display_name, icon_url=ntr.user.display_avatar.url)
        e.set_footer(text=f"{lang.code} Language: {lang.locale}")
        await ntr.response.send_message(embed=e)

    @tts_group.command()
    async def stop(self, ntr: discord.Interaction):
        """Stop playing current audio. Useful if somebody is abusing TTS system with annoying requests."""
        try:
            assert isinstance(ntr.guild, discord.Guild)
            vc = self.connections[ntr.guild.id]
        except KeyError:
            # TODO: raise better error type
            raise commands.BadArgument("I'm not in voice channel")

        if vc.is_playing():
            vc.stop()
            e = discord.Embed(description='Stopped', colour=ntr.user.colour)
            await ntr.response.send_message(embed=e)
        else:
            e = discord.Embed(description="I don't think I was talking", colour=Colour.error())
            await ntr.response.send_message(embed=e, ephemeral=True)

    @tts_group.command()
    async def leave(self, ntr: discord.Interaction):
        """Make bot leave voice channel."""
        try:
            assert isinstance(ntr.guild, discord.Guild)
            vc = self.connections[ntr.guild.id]
        except KeyError:
            # TODO: raise better error type
            raise commands.BadArgument("I'm not in a voice channel.")

        await vc.disconnect()
        e = discord.Embed(description=f'I left {vc.channel.mention}', colour=ntr.user.colour)
        await ntr.response.send_message(embed=e)

    @app_commands.guild_only()
    @app_commands.command(name='bonjour')
    async def bonjour(self, ntr: discord.Interaction):
        """`Bonjour !` into both text/voice chats"""
        content = f'Bonjour {Emote.bubuAyaya}'

        assert ntr.guild is not None

        if not (member := ntr.guild.get_member(ntr.user.id)):
            # TODO: raise better error type
            raise commands.BadArgument('Something went wrong.')

        if not (voice_state := member.voice):
            return await ntr.response.send_message(content=content)
            
        if ntr.guild.voice_client is not None:
            vc = self.connections[ntr.guild.id]
            await vc.move_to(voice_state.channel)
        else:
            if not voice_state.channel:
                # TODO: raise better error type
                raise commands.BadArgument("You aren't connected to a voice channel!")
            vc = await voice_state.channel.connect()  # Connect to the voice channel the author is in.
            self.connections.update({ntr.guild.id: vc})  # Updating the cache with the guild and channel.

        tts = gTTS('Bonjour !', lang='fr', tld='fr')
        audio_name = "audio.mp3"
        tts.save(audio_name)
        vc.play(discord.FFmpegPCMAudio(audio_name))
        await ntr.response.send_message(content=content)

    @commands.Cog.listener()
    async def on_voice_state_update(
        self, member: discord.Member, before: discord.VoiceState, _after: discord.VoiceState
    ):
        # disconnect
        if before.channel is not None and len([m for m in before.channel.members if not m.bot]) == 0:
            vc = self.connections.get(member.guild.id, None)
            if vc is not None:
                await vc.disconnect()


async def setup(bot: AluBot):
    await bot.add_cog(TextToSpeech(bot))
