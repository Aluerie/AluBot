from __future__ import annotations
from typing import TYPE_CHECKING

from discord import ButtonStyle, Embed, app_commands
from discord.ext import commands
from discord.ui import View, button

from utils.var import *
from utils.elpcmd import HelpCommand

if TYPE_CHECKING:
    from discord import Interaction


def first_page(ctx):
    em = Embed(color=Clr.prpl, title=f'{ctx.bot.user.display_name} | $helpmod Menu')
    em.description = f'🏠 {ctx.bot.user.display_name} is an ultimate multi-purpose bot !'
    em.set_thumbnail(url=ctx.bot.user.display_avatar.url)
    em.set_footer(text=f'With love, {ctx.bot.user.display_name}')
    em.add_field(inline=False, name=f'{Ems.peepoPolice} `Mute`', value='Commands to moderate server with')
    em.add_field(inline=False, name=f'{Ems.peepoWTF} `Rules`', value='Commands to edit rules with')
    return em


class ViewHelpMod(View):
    def __init__(self, paginator):
        super().__init__()
        self.paginator = paginator

    @button(label="", style=ButtonStyle.primary, emoji='🏠')
    async def button0(self, ntr, btn):
        await self.paginator.goto_page(page_number=0, ntr=ntr)

    @button(label="Mute", style=ButtonStyle.primary, emoji=Ems.peepoPolice)
    async def button1(self, ntr, btn):
        await self.paginator.goto_page(page_number=1, ntr=ntr)

    @button(label="Rules", style=ButtonStyle.primary, emoji=Ems.peepoWTF)
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
    async def help_slash(self, ntr: Interaction):
        myhelp = HelpCommand(
            get_starting_embed,
            ViewHelpMod,
            verify_checks=False
        )
        myhelp.context = await commands.Context.from_interaction(ntr)
        await myhelp.command_callback(myhelp.context)


async def setup(bot):
    await bot.add_cog(ModHelpCog(bot))
