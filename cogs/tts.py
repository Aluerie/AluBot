from discord import FFmpegPCMAudio, Embed, option, OptionChoice
from discord.commands import SlashCommandGroup
from discord.ext import bridge, commands

from utils.var import *
from utils.dcordtools import scnf

from gtts import gTTS
from typing import Literal, Optional


lang_dict = {
    'fr-FR': {'locale': 'French (France)', 'lang': 'fr', 'tld': 'fr'},
    'en-IE': {'locale': 'English (Ireland)', 'lang': 'en', 'tld': 'ie'},
    'ru-RU': {'locale': 'Russian (Russia)', 'lang': 'ru', 'tld': 'com'},
    'es-ES': {'locale': 'Spanish (Spain)', 'lang': 'es', 'tld': 'es'},
    'pt-PT': {'locale': 'Portuguese (Portugal)', 'lang': 'pt', 'tld': 'pt'},
    'zh-CN': {'locale': 'Mandarin (China Mainland)', 'lang': 'zh-CN', 'tld': 'com'},
    # 'uk-UA': {'locale': 'Ukrainian (Ukrain)', 'lang': 'uk', 'tld': 'com.ua'},
}


class TextToSpeech(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.connections = {}
        self.help_category = 'Tools'

    async def voice_work(self, ctx, dict_key, text):
        voice = ctx.author.voice
        if not voice:
            embed = Embed(colour=Clr.error)
            embed.description = "You aren't in a voice channel!"
            return await ctx.respond(embed=embed)
        if ctx.voice_client is not None:
            vc = self.connections[ctx.guild.id]
            await ctx.voice_client.move_to(voice.channel)
        else:
            vc = await voice.channel.connect()  # Connect to the voice channel the author is in.
            self.connections.update({ctx.guild.id: vc})  # Updating the cache with the guild and channel.

        tts = gTTS(text, lang=lang_dict[dict_key]['lang'], tld=lang_dict[dict_key]['tld'])
        audio_name = "audio.mp3"
        tts.save(audio_name)
        vc.play(FFmpegPCMAudio(audio_name))
        embed = Embed(colour=ctx.author.colour, title='Text-To-Speech request')
        embed.set_author(name=ctx.author.display_name, icon_url=ctx.author.display_avatar.url)
        embed.set_footer(text=f"{dict_key} Language: {lang_dict[dict_key]['locale']}")
        embed.description = text
        await ctx.respond(embed=embed)

    vcslash_gr = SlashCommandGroup('voice', 'Text-To-Speech commands')

    @vcslash_gr.command(
        name='speak',
        description='Make Text-To-Speech request into voice-chat'
    )
    @option('text', description="Enter text to speak")
    @option('lang',
            choices=[OptionChoice(lang_dict[key]['locale'], value=key) for key in lang_dict],
            default='fr-FR',
            description="Choose language/accent")
    async def speak_slash(self, ctx, text: str, lang: str):
        await self.voice_work(ctx, lang, text)

    @commands.group(name='voice')
    async def vctext_gr(self, ctx):
        """Group command about Voice commands, for actual commands use it together with subcommands"""
        await scnf(ctx)

    @vctext_gr.command(
        name='speak',
        brief=Ems.slash,
        usage="[language keyword=fr-FR] <text='Allo'>"
    )
    async def speak_text(
            self,
            ctx,
            lang: Optional[Literal[tuple(list(lang_dict.keys()))]] = 'fr-FR',
            # honourable mention of exec to avoid the warning
            # exec('xd = typing.Literal["{0}"]'.format('","'.join(list(lang_dict.keys()))))
            *,
            text: str = 'Allo'
    ):
        """Bot will connect to voice-chat you're in and speak `text` using Google Text-To-Speech module. \
        For available language keywords check `(/ or $)voice languages` ;"""
        await self.voice_work(ctx, lang, text)

    async def langs_work(self, ctx):
        embed = Embed(colour=Clr.prpl)
        embed.description = 'List of languages'
        our_list = [f"{key}: {lang_dict[key]['locale']}" for key in lang_dict]
        embed.description = \
            f'Commands `$voice` and `/voice` support following languages.\n ' \
            f'Example of usage for text-command: `$voice en-UK allo chat AYAYA`.\n ' \
            f'When using slash-command choose language from available list in its options.' \
            f'\n```\n' + \
            '\n'.join(our_list) + '```'
        await ctx.respond(embed=embed)

    @vcslash_gr.command(
        name='languages',
        description='Show list of languages supported by `/voice speak` command'
    )
    async def langs_slash(self, ctx):
        await self.langs_work(ctx)

    @vctext_gr.command(
        name='languages',
        brief=Ems.slash,
        aliases=['langs']
    )
    async def langs_text(self, ctx):
        """Show list of languages supported by `(/ or $)voice speak` command"""
        await self.langs_work(ctx)

    async def stop_work(self, ctx):
        try:
            vc = self.connections[ctx.guild.id]
            if vc.is_playing():
                vc.stop()
                embed = Embed(colour=ctx.author.colour)
                embed.description = 'Stopped'
                await ctx.respond(embed=embed)
            else:
                embed = Embed(colour=Clr.error)
                embed.description = "I don't think I was talking"
                await ctx.respond(embed=embed)
        except KeyError:
            embed = Embed(colour=Clr.error)
            embed.description = "I'm not in voice channel"
            await ctx.respond(embed=embed)

    @vcslash_gr.command(
        name='stop',
        description='Stop playing current audio. Useful if somebody is abusing TTS system with annoying requests'
    )
    async def stop_slash(self, ctx):
        await self.stop_work(ctx)

    @vctext_gr.command(
        name='stop',
        brief=Ems.slash
    )
    async def stop_text(self, ctx):
        """Stop playing current audio. Useful if somebody is abusing TTS system with annoying requests ;"""
        await self.stop_work(ctx)

    @bridge.bridge_command(
        name='bonjour',
        description=f'`Bonjour !` into both text/voice chats',
        brief=Ems.slash,
    )
    async def bonjour(self, ctx):
        """`Bonjour !` into both text/voice chats"""
        voice = ctx.author.voice
        if not voice:
            content = f'Bonjour {Ems.bubuAyaya}'
            return await ctx.respond(content=content)
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
        await ctx.respond(content=content)

    @commands.Cog.listener()
    async def on_voice_state_update(self, member, before, after):
        # disconnect
        if before.channel is not None and len([m for m in before.channel.members if not m.bot]) == 0:
            vc = self.connections[member.guild.id]
            await vc.disconnect()


def setup(bot):
    bot.add_cog(TextToSpeech(bot))

