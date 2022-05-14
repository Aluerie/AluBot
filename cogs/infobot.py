from discord import Embed
from discord.ext import commands, bridge

from utils.var import Ems, Clr

import platform, socket, psutil
from os import getenv


class BotInfo(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.help_category = 'Info'

    @bridge.bridge_command(
        name='sysinfo',
        brief=Ems.slash,
        description='Get system info about machine currently hosting the bot',
        aliases=['systeminfo']
    )
    async def sysinfo(self, ctx):
        """Get system info about machine currently hosting the bot. Idk myself what machine it is being hosted on ;"""
        embed = Embed(colour=Clr.prpl, title="Bot Host Machine System Info")
        embed.description = \
            f'Hostname: {socket.gethostname()}\n' \
            f'Machine: {platform.machine()}\n' \
            f'Platform: {platform.platform()}\n' \
            f'System: `{platform.system()}` release: `{platform.release()}`\n' \
            f'Version: `{platform.version()}`\n' \
            f'Processor: {platform.processor()}\n'
        embed.add_field(
            name='Current % | max values',
            value=f'CPU usage: {psutil.cpu_percent()}% | {psutil.cpu_freq().current/1000:.1f}GHz\n'
                  f'RAM usage: {psutil.virtual_memory().percent}% | '
                  f'{str(round(psutil.virtual_memory().total / (1024.0 ** 3))) + " GB"}\n'
                  f'Disk usage: {(du := psutil.disk_usage("/")).percent} % | '
                  f'{du.used / (1024 ** 3):.1f}GB /{du.total / (1024 ** 3):.1f}GB'
        )
        """ # well it didnt work on our host machine
        if platform.system() == 'Linux':
            embed.add_field(
                name='Sensors info',
                value=f'Temperature: {psutil.sensors_temperatures(fahrenheit=False)}\n'
                      f'Fans info: {psutil.sensors_fans()}'
            )
        """
        embed.set_footer(text='This is what they give me for free plan :D')
        await ctx.respond(embed=embed)


class BotAdminInfo(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.help_category = 'AdminInfo'

    @commands.command(aliases=['invitelink'])
    @commands.is_owner()
    @commands.guild_only()
    async def invite_link(self, ctx):
        embed = Embed(color=Clr.prpl)
        embed.description = getenv('DISCORD_BOT_INVLINK')
        await ctx.send(embed=embed)


def setup(bot):
    bot.add_cog(BotInfo(bot))
    bot.add_cog(BotAdminInfo(bot))
