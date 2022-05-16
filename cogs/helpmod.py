from discord import ButtonStyle, Embed, app_commands, ui
from discord.ext import commands
from utils.var import Clr, Ems, Rid
from utils.elpcmd import HelpCommand


def first_page(ctx):
    embed = Embed(color=Clr.prpl)
    embed.title = f'{ctx.bot.user.display_name} | $helpmod Menu'
    embed.description = f'🏠 {ctx.bot.user.display_name} is an ultimate multi-purpose bot !'
    embed.set_thumbnail(url=ctx.bot.user.display_avatar.url)
    embed.set_footer(text=f'With love, {ctx.bot.user.display_name}')
    embed.add_field(name=f'{Ems.peepoPolice} `Mute`', inline=False,
                    value='Commands to moderate server with')
    embed.add_field(name=f'{Ems.peepoWTF} `Rules`', inline=False,
                    value='Commands to edit rules with')
    return embed


class ViewHelpMod(ui.View):
    def __init__(self, paginator):
        super().__init__()
        self.paginator = paginator

    @ui.button(label="", style=ButtonStyle.primary, emoji='🏠')
    async def button0(self, ntr, btn):
        await self.paginator.goto_page(page_number=0, ntr=ntr)

    @ui.button(label="Mute", style=ButtonStyle.primary, emoji=Ems.peepoPolice)
    async def button1(self, ntr, btn):
        await self.paginator.goto_page(page_number=1, ntr=ntr)

    @ui.button(label="Rules", style=ButtonStyle.primary, emoji=Ems.peepoWTF)
    async def button2(self, ntr, btn):
        await self.paginator.goto_page(page_number=2, ntr=ntr)


def get_starting_embed(ctx):
    footer_text = f'With love, {ctx.bot.user.display_name}'
    thumb_url = ctx.bot.user.display_avatar.url
    embed_dict = {
        '🏠': first_page(ctx),
        'Mute':
            Embed(
                title="Mute commands",
                color=Clr.prpl,
                description=f'{Ems.peepoPolice} Commands to punish people with',
            ).set_footer(text=footer_text).set_thumbnail(url=thumb_url),
        'Rules':
            Embed(
                title="Rules commands",
                color=Clr.prpl,
                description=f'{Ems.peepoWTF} Commands to edit rules with',
            ).set_footer(text=footer_text).set_thumbnail(url=thumb_url)
    }
    return embed_dict


class ModHelpCog(commands.Cog):
    def __init__(self, bot):
        self.help_category = 'Info'
        command_attrs = {
            'name': 'helpmod',
            'checks': [commands.has_role(Rid.discord_mods).predicate],
            'help': 'Show special help menu for mods',
            'brief': Ems.slash
        }
        bot.help2_command = HelpCommand(
            get_starting_embed,
            ViewHelpMod,
            command_attrs=command_attrs,
            verify_checks=False
        )
        bot.help2_command.cog = self

    @app_commands.default_permissions(manage_messages=True)
    @app_commands.command(
        name='helpmod',
        description='Show special help menu for mods',
    )
    async def help_slash(self, ctx):
        myhelp = HelpCommand(
            get_starting_embed,
            ViewHelpMod,
            verify_checks=False
        )
        myhelp.context = ctx
        await myhelp.command_callback(myhelp.context)


async def setup(bot):
    await bot.add_cog(ModHelpCog(bot))
