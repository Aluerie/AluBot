from __future__ import annotations
from typing import TYPE_CHECKING, Optional

from discord import FFmpegPCMAudio, Embed, app_commands
from discord.ext import commands

from utils.var import *

from gtts import gTTS

if TYPE_CHECKING:
    from utils.context import Context

lang_dict = {
    'fr': {
        'code': 'fr-FR',
        'locale': 'French (France)',
        'lang': 'fr',
        'tld': 'fr'
    },
    'en': {
        'code': 'en-IE',
        'locale': 'English (Ireland)',
        'lang': 'en',
        'tld': 'ie'
    },
    'ru': {
        'code': 'ru-RU',
        'locale': 'Russian (Russia)',
        'lang': 'ru',
        'tld': 'com'
    },
    'es': {
        'code': 'es-ES',
        'locale': 'Spanish (Spain)',
        'lang': 'es',
        'tld': 'es'
    },
    'pt': {
        'code': 'pt-PT',
        'locale': 'Portuguese (Portugal)',
        'lang': 'pt',
        'tld': 'pt'
    },
    'cn': {
        'code': 'zh-CN',
        'locale': 'Mandarin (China Mainland)',
        'lang': 'zh-CN',
        'tld': 'com'
    },
    'uk': {
        'code': 'uk-UA',
        'locale': 'Ukrainian (Ukrain)',
        'lang': 'uk',
        'tld': 'com.ua'
    },
}


class TextToSpeech(commands.Cog, name='TTS'):
    """
    Text To Speech commands.

    Make the bot talk in voice chat.
    """
    def __init__(self, bot):
        self.bot = bot
        self.connections = {}
        self.help_emote = Ems.Ree

    @commands.hybrid_group(name='voice')
    async def voice(self, ctx: Context):
        """Group command about Voice commands, for actual commands use it together with subcommands"""
        await ctx.scnf()

    @voice.command(
        name='speak',
        brief=Ems.slash,
        description='Make Text-To-Speech request into voice-chat',
        usage="[language keyword=fr-FR] <text='Allo'>"
    )
    @app_commands.describe(text="Enter text to speak", lang="Choose language/accent")
    async def speak(
            self,
            ctx,
            lang: Optional[Literal['fr', 'en', 'ru', 'es', 'pt', 'cn', 'uk']] = 'fr',
            *,
            text: str = 'Allo'
            # honourable mention of exec to avoid the warning
            # tuple(list(lang_dict.keys()))
            # exec('xd = typing.Literal["{0}"]'.format('","'.join(list(lang_dict.keys()))))
    ):
        """
        Bot will connect to voice-chat you're in and speak `text` using Google Text-To-Speech module. \
        For available language keywords check `(/ or $)voice languages`
        """
        voice = ctx.author.voice
        if not voice:
            em = Embed(
                colour=Clr.error,
                description="You aren't in a voice channel!"
            )
            return await ctx.reply(embed=em, ephemeral=True)
        if ctx.voice_client is not None:
            vc = self.connections[ctx.guild.id]
            await ctx.voice_client.move_to(voice.channel)
        else:
            vc = await voice.channel.connect()  # Connect to the voice channel the author is in.
            self.connections.update({ctx.guild.id: vc})  # Updating the cache with the guild and channel.

        tts = gTTS(text, lang=lang_dict[lang]['lang'], tld=lang_dict[lang]['tld'])
        audio_name = "audio.mp3"
        tts.save(audio_name)
        vc.play(FFmpegPCMAudio(audio_name))
        em = Embed(
            colour=ctx.author.colour,
            title='Text-To-Speech request',
            description=text
        ).set_author(
            name=ctx.author.display_name,
            icon_url=ctx.author.display_avatar.url
        ).set_footer(
            text=f"{lang_dict[lang]['code']} Language: {lang_dict[lang]['locale']}"
        )
        await ctx.reply(embed=em)

    @voice.command(
        name='languages',
        brief=Ems.slash,
        description='Show list of languages supported by `/voice speak` command',
        aliases=['langs']
    )
    async def languages(self, ctx):
        """
        Show list of languages supported by `(/ or $)voice speak` command.
        """
        our_list = [f"{key}: {lang_dict[key]['locale']}" for key in lang_dict]
        em = Embed(
            colour=Clr.prpl,
            title='List of languages supported by the bot',
            description=
            f'Commands `$voice` and `/voice` support following languages.\n '
            f'Example of usage for text-command: `$voice en-UK allo chat AYAYA`.\n '
            f'When using slash-command choose language from available list in its options.'
            f'\n```\n'
            '\n'.join(our_list) + '```'
        )
        await ctx.reply(embed=em)

    @voice.command(
        name='stop',
        brief=Ems.slash,
        description='Stop playing current audio. Useful if somebody is abusing TTS system with annoying requests'
    )
    async def stop(self, ctx: Context):
        """
        Stop playing current audio. Useful if somebody is abusing TTS system with annoying requests.
        """
        try:
            vc = self.connections[ctx.guild.id]
            if vc.is_playing():
                vc.stop()
                em = Embed(
                    colour=ctx.author.colour,
                    description='Stopped'
                )
                await ctx.reply(embed=em)
            else:
                em = Embed(
                    colour=Clr.error,
                    description="I don't think I was talking"
                )
                await ctx.reply(embed=em, ephemeral=True)
        except KeyError:
            em = Embed(
                colour=Clr.error,
                description="I'm not in voice channel"
            )
            await ctx.reply(embed=em, ephemeral=True)

    @voice.command(
        name='leave',
        brief=Ems.slash,
        description='Leave voice channel'
    )
    async def leave(self, ctx):
        """
        Make bot leave voice channel. Bot autoleaves voicechannels but you can make it leave too
        """
        try:
            vc = self.connections[ctx.guild.id]
            await vc.disconnect()
            em = Embed(
                colour=ctx.author.colour,
                description=f'I left {vc.channel.mention}'
            )
            await ctx.reply(embed=em)
        except KeyError:
            em = Embed(
                colour=Clr.error,
                description="I'm not in voice channel"
            )
            await ctx.reply(embed=em, ephemeral=True)

    @commands.hybrid_command(
        name='bonjour',
        brief=Ems.slash,
        description=f'`Bonjour !` into both text/voice chats',
    )
    async def bonjour(self, ctx):
        """
        `Bonjour !` into both text/voice chats
        """
        voice = ctx.author.voice
        if not voice:
            content = f'Bonjour {Ems.bubuAyaya}'
            return await ctx.reply(content=content)
        if ctx.voice_client is not None:
            vc = self.connections[ctx.guild.id]
            await ctx.voice_client.move_to(voice.channel)
        else:
            vc = await voice.channel.connect()  # Connect to the voice channel the author is in.
            self.connections.update({ctx.guild.id: vc})  # Updating the cache with the guild and channel.

        tts = gTTS('Bonjour !', lang='fr', tld='fr')
        audio_name = "audio.mp3"
        tts.save(audio_name)
        vc.play(FFmpegPCMAudio(audio_name))
        content = f'Bonjour {Ems.bubuAyaya}'
        await ctx.reply(content=content)

    @commands.Cog.listener()
    async def on_voice_state_update(self, member, before, after):
        # disconnect
        if before.channel is not None and len([m for m in before.channel.members if not m.bot]) == 0:
            vc = self.connections.get(member.guild.id, None)
            if vc is not None:
                await vc.disconnect()


async def setup(bot):
    await bot.add_cog(TextToSpeech(bot))

