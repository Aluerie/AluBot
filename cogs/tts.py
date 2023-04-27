from __future__ import annotations

import typing
from typing import TYPE_CHECKING, Dict, Literal, NamedTuple, Optional

import discord
from discord import app_commands
from discord.ext import commands
from gtts import gTTS

from utils import AluCog, Clr, Ems

if TYPE_CHECKING:
    from utils import AluBot, AluContext


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


class TextToSpeech(AluCog, name='TTS', emote=Ems.Ree):
    """Text To Speech commands.

    Make the bot talk in voice chat.
    """

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.connections: Dict[int, discord.VoiceProtocol] = {}  # guild.id to Voice we are connected to

    @commands.hybrid_group(name='voice')
    async def voice(self, ctx: AluContext):
        """Group command about Voice commands, for actual commands use it together with subcommands"""
        await ctx.scnf()

    @voice.command(
        name='speak',
        description='Make Text-To-Speech request into voice-chat',
        usage="[language keyword=fr-FR] <text='Allo'>",
    )
    @app_commands.describe(text="Enter text to speak", language="Choose language/accent")
    async def speak(
        self, ctx: AluContext, language: Optional[LanguageCollection.Literal] = 'fr', *, text: str = 'Allo'
    ):
        """
        Bot will connect to voice-chat you're in and speak `text` using Google Text-To-Speech module. \
        For available language keywords check `(/ or $)voice languages`
        """

        # honourable mention of exec to avoid the warning
        # tuple(list(lang_dict.keys()))
        # exec('xd = typing.Literal["{0}"]'.format('","'.join(list(lang_dict.keys()))))
        lang: LanguageData = getattr(LanguageCollection, language)
        voice = ctx.author.voice
        if not voice:
            e = discord.Embed(description="You aren't in a voice channel!", colour=Clr.error)
            return await ctx.reply(embed=e, ephemeral=True)
        if ctx.voice_client is not None:
            vc = self.connections[ctx.guild.id]
            await ctx.voice_client.move_to(voice.channel)
        else:
            vc = await voice.channel.connect()  # Connect to the voice channel the author is in.
            self.connections.update({ctx.guild.id: vc})  # Updating the cache with the guild and channel.

        tts = gTTS(text, lang=lang.lang, tld=lang.tld)
        audio_name = "./.temp/audio.mp3"
        tts.save(audio_name)
        vc.play(discord.FFmpegPCMAudio(audio_name))
        e = discord.Embed(title='Text-To-Speech request', description=text, colour=ctx.author.colour)
        e.set_author(name=ctx.author.display_name, icon_url=ctx.author.display_avatar.url)
        e.set_footer(text=f"{lang.code} Language: {lang.locale}")
        await ctx.reply(embed=e)

    @voice.command(
        name='languages', description='Show list of languages supported by `/voice speak` command', aliases=['langs']
    )
    async def languages(self, ctx: AluContext):
        """Show list of languages supported by `(/ or $)voice speak` command"""
        language_keys = typing.get_args(LanguageCollection.Literal)
        our_list = [f"{key}: {getattr(LanguageCollection, key).locale}" for key in language_keys]
        e = discord.Embed(title='List of languages supported by the bot', colour=Clr.prpl)
        e.description = (
            f'Commands `$voice` and `/voice` support following languages.\n '
            f'Example of usage for text-command: `$voice en-UK allo chat AYAYA`.\n '
            f'When using slash-command choose language from available list in its options.'
            f'\n```\n'
            '\n'.join(our_list) + '```'
        )
        await ctx.reply(embed=e)

    @voice.command(
        name='stop',
        description='Stop playing current audio. Useful if somebody is abusing TTS system with annoying requests',
    )
    async def stop(self, ctx: AluContext):
        """Stop playing current audio. Useful if somebody is abusing TTS system with annoying requests."""
        try:
            vc = self.connections[ctx.guild.id]
            if vc.is_playing():
                vc.stop()
                e = discord.Embed(description='Stopped', colour=ctx.author.colour)
                await ctx.reply(embed=e)
            else:
                e = discord.Embed(description="I don't think I was talking", colour=Clr.error)
                await ctx.reply(embed=e, ephemeral=True)
        except KeyError:
            e = discord.Embed(description="I'm not in voice channel", colour=Clr.error)
            await ctx.reply(embed=e, ephemeral=True)

    @voice.command(name='leave', description='Leave voice channel')
    async def leave(self, ctx: AluContext):
        """Make bot leave voice channel. Bot autoleaves voicechannels but you can make it leave too"""
        try:
            vc = self.connections[ctx.guild.id]
            await vc.disconnect()
            e = discord.Embed(description=f'I left {vc.channel.mention}', colour=ctx.author.colour)
            await ctx.reply(embed=e)
        except KeyError:
            e = discord.Embed(description="I'm not in voice channel", colour=Clr.error)
            await ctx.reply(embed=e, ephemeral=True)

    @commands.hybrid_command(
        name='bonjour',
        description=f'`Bonjour !` into both text/voice chats',
    )
    async def bonjour(self, ctx):
        """`Bonjour !` into both text/voice chats"""
        voice = ctx.author.voice
        if not voice:
            return await ctx.reply(content=f'Bonjour {Ems.bubuAyaya}')
        if ctx.voice_client is not None:
            vc = self.connections[ctx.guild.id]
            await ctx.voice_client.move_to(voice.channel)
        else:
            vc = await voice.channel.connect()  # Connect to the voice channel the author is in.
            self.connections.update({ctx.guild.id: vc})  # Updating the cache with the guild and channel.

        tts = gTTS('Bonjour !', lang='fr', tld='fr')
        audio_name = "audio.mp3"
        tts.save(audio_name)
        vc.play(discord.FFmpegPCMAudio(audio_name))
        content = f'Bonjour {Ems.bubuAyaya}'
        await ctx.reply(content=content)

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
