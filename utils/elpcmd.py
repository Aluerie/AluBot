from discord import Embed, Color
from discord.ext import commands
from utils.format import display_hmstime
from utils.var import *
from utils import pages


class HelpCommand(commands.HelpCommand):
    def __init__(self, start_embed, view_class, **kwargs) -> None:
        super().__init__(**kwargs)
        self.start_embed_dict = start_embed
        self.view_class = view_class

    def get_command_signature(self, command):
        extra_space = '' if command.signature == '' else ' '
        prefix = getattr(self.context, 'clean_prefix', '$')
        return f'{prefix}{command.qualified_name}{extra_space}{command.signature}'

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
            pages=list(embed_dict.values()),
            # custom_buttons=page_buttons,
            # use_default_buttons=False,
            # show_action_row=True,
            # goto_select=True,
            # bot=self.context.bot
        )
        view = self.view_class(paginator)
        paginator.custom_view = view
        await paginator.send(self.context)  # TODO: interaction ?

    async def send_command_help(self, command):
        embed = Embed(title=self.get_command_signature(command), color=Color.blurple())
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
        embed = Embed(title="Error", description=error, color=Color.red())
        channel = self.get_destination()

        await channel.send(embed=embed)
