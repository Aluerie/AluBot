from __future__ import annotations
from typing import TYPE_CHECKING

from discord import Embed, app_commands, SelectOption
from discord.ext import commands
from discord.ui import View, Select

from utils.var import *
from utils.format import display_hmstime
from utils import pages

if TYPE_CHECKING:
    from discord import Interaction


help_cat_dict = {
    'Tools': {
        'title': 'Tools',
        'emote': Ems.DankFix,
        'drop': 'Commands providing useful tools',
        'desc': 'Commands providing useful tools'
    },
    'Info': {
        'title': 'Info',
        'emote': Ems.PepoG,
        'drop': 'Commands to get some useful info',
        'desc': 'Commands to get some useful info',
    },
    'Stats': {
        'title': 'Stats',
        'emote': Ems.Smartge,
        'drop': 'Commands to get some stats/infographics',
        'desc': 'Commands to get some stats/infographics',
    },
    'Profile': {
        'title': 'Profile',
        'emote': Ems.bubuAyaya,
        'drop': 'Commands about member profiles',
        'desc': f'There is a profile system in Irene\'s server: levelling experience, '
                f'currency, reputation, custom profile and many other things. ',
    },
    'Aluerie': {
        'title': 'Aluerie',
        'emote': Ems.TwoBButt,
        'drop': 'Commands to stalk Irene\'s progress in some things',
        'desc': f'There are some commands to see Aluerie\'s info such as dota 2 match history'
    },
    'Mute': {
        'title': 'Mute',
        'emote': Ems.peepoPolice,
        'drop': 'Commands to moderate server with',
        'desc': 'Commands to moderate server with'
    },
    'Rules': {
        'title': 'Rules',
        'emote': Ems.peepoWTF,
        'drop': 'Commands to edit rules with',
        'desc': 'Commands to edit rules with'
    },
    'AdminInfo': {
        'title': 'AdminInfo',
        'emote': Ems.peepoComfy,
        'drop': 'Commands for admin info',
        'desc': 'Commands for admin info'
    },
    'AdminTools': {
        'title': 'AdminTools',
        'emote': Ems.MadgeThreat,
        'drop': 'Commands for admin tools',
        'desc': 'Commands for admin tools'
    },
}


class DropdownHelp(Select):
    def __init__(self, paginator):
        options = [
            SelectOption(
                label=v['title'],
                description=v['drop'],
                emoji=v['emote'],
                value=str(i)
            ) for i, (k, v) in enumerate(help_cat_dict.items())
        ]
        super().__init__(placeholder='Choose help category', min_values=1, max_values=1, options=options)
        self.paginator = paginator

    async def callback(self, ntr: Interaction):
        await self.paginator.goto_page(page_number=int(self.values[0]), ntr=ntr)


class ViewHelp(View):
    def __init__(self, paginator):
        super().__init__()
        self.paginator = paginator
        self.add_item(DropdownHelp(paginator))


def get_starting_embed(ctx):
    embed_dict = {
        k: v.get(
            'embed',
            Embed(
                colour=Clr.prpl,
                title=v['title'],
                description=f"{v['emote']} {v['desc']}"
            )
        ).set_footer(
            text=ctx.bot
        ).set_thumbnail(

        ) for k, v in help_cat_dict.items()
    }
    return embed_dict


class HelpCommand(commands.HelpCommand):
    def __init__(self, start_embed, view_class, **kwargs) -> None:
        super().__init__(**kwargs)
        self.start_embed_dict = start_embed
        self.view_class = view_class



    async def send_bot_help(self, mapping):
        temp_dict = dict()
        embed_dict = self.start_embed_dict(self.context)
        for cog, commands in mapping.items():
            if (cog_category := getattr(cog, "help_category", None)) not in list(embed_dict.keys()):
                continue
            filtered = await self.filter_commands(commands, sort=True)

            def add_c_to_embed(c):
                slash = ''
                if c.brief == Ems.slash:
                    slash = Ems.slash
                aliases = ''
                if len(c.aliases):
                    aliases = ' | aliases: ' + '; '.join([f'`{ali}`' for ali in c.aliases])
                cd_str = ''
                if c.cooldown is not None:
                    cd_str = f' | cd: rate {c.cooldown.rate} per {display_hmstime(c.cooldown.per)}'

                if cog_category in temp_dict:
                    temp_dict[cog_category][f'• {slash}`{self.get_command_signature(c)}`{aliases}{cd_str}'] = c.help
                else:
                    temp_dict[cog_category] = {f'• {slash}`{self.get_command_signature(c)}`{aliases}{cd_str}': c.help}

            for c in filtered:
                if getattr(c, 'commands', None) is not None:
                    if c.brief == Ems.slash:
                        add_c_to_embed(c)
                    for x in await self.filter_commands(c.commands, sort=True):
                        if getattr(x, 'commands', None) is not None:
                            for y in await self.filter_commands(x.commands, sort=True):
                                add_c_to_embed(y)
                        else:
                            add_c_to_embed(x)
                else:
                    add_c_to_embed(c)

        for category in temp_dict:
            temp_dict[category] = dict(sorted(temp_dict[category].items()))
            for cmd_name in temp_dict[category]:
                embed_dict[category].add_field(
                    name=cmd_name,
                    inline=False,
                    value=temp_dict[category][cmd_name]
                )

        paginator = pages.Paginator(
            pages=list(embed_dict.values())
        )
        view = self.view_class(paginator)
        paginator.custom_view = view
        await paginator.send(self.context)  # TODO: interaction ?

    async def send_command_help(self, command):
        embed = Embed(title=self.get_command_signature(command), color=Clr.prpl)
        if command.help:
            embed.description = command.help
        if alias := command.aliases:
            embed.add_field(name="Aliases", value=", ".join(alias), inline=False)

        channel = self.get_destination()
        await channel.send(embed=embed)

    async def send_help_embed(self, title, description, commands):  # a helper function to add commands to an embed
        embed = Embed(title=title, colour=Clr.prpl, description=description or "No help found...")

        if filtered_commands := await self.filter_commands(commands):
            for command in filtered_commands:
                embed.add_field(name=self.get_command_signature(command), value=command.help or "No help found...")

        await self.get_destination().send(embed=embed)

    async def send_group_help(self, group):
        title = self.get_command_signature(group)
        await self.send_help_embed(title, group.help, group.commands)

    async def send_cog_help(self, cog):
        title = cog.qualified_name or "No"
        await self.send_help_embed(f'{title} Category', cog.description, cog.get_commands())

    async def send_error_message(self, error):
        embed = Embed(title="Error", description=error, color=Clr.error)
        channel = self.get_destination()

        await channel.send(embed=embed)


class HelpCog(commands.Cog):
    def __init__(self, bot):
        self._original_help_command = bot.help_command
        self.help_category = 'Info'
        self.bot = bot
        bot.help_command = HelpCommand(
            get_starting_embed,
            ViewHelp,
            command_attrs={
                'help':
                    'Show `help` menu for common bot commands. '
                    'Note that you can use `$help [command/group/cog]` to get a help on specific things',
                'brief':
                    f'{Ems.slash}'
            },
            verify_checks=False
        )
        bot.help_command.cog = self

    @app_commands.command(
        name='help',
        description='Show help menu for the bot',
    )
    async def help_slash(self, ntr: Interaction):
        myhelp = HelpCommand(
            get_starting_embed,
            ViewHelp,
            verify_checks=False
        )
        myhelp.context = await commands.Context.from_interaction(ntr)
        await myhelp.command_callback(myhelp.context)


async def setup(bot):
    await bot.add_cog(HelpCog(bot))
