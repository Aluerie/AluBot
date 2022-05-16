from discord import ButtonStyle, Embed, ui, app_commands, Interaction
from discord.ext import commands
from utils.var import Clr, Ems, Cid, cmntn
from utils.elpcmd import HelpCommand


def first_page(ctx):
    bot_name = ctx.guild.me.display_name
    embed = Embed(color=Clr.prpl, title=f'{bot_name} | $helpadmin Menu')
    embed.description = f'🏠 {bot_name} is everything !'
    embed.set_thumbnail(url=ctx.bot.user.display_avatar.url)
    embed.set_footer(text=f'With love, {bot_name}')
    embed.add_field(name=f'{Ems.phone_numbers[1]} `Page #1`', inline=False,
                    value='Dota 2 related commands ;')
    embed.add_field(name=f'{Ems.phone_numbers[2]} `Page #2`', inline=False,
                    value='LoL related commands ;')
    embed.add_field(name=f'{Ems.phone_numbers[3]} `Page #3`', inline=False,
                    value='Info related commands ;')
    embed.add_field(name=f'{Ems.phone_numbers[4]} `Page #4`', inline=False,
                    value='Tools related commands ;')
    return embed


class ViewHelpAdmin(ui.View):
    def __init__(self, paginator):
        super().__init__()
        self.paginator = paginator

    @ui.button(label="", style=ButtonStyle.primary, emoji='🏠')
    async def button0(self, ntr, btn):
        await self.paginator.goto_page(page_number=0, ntr=ntr)

    @ui.button(label="Dota 2", style=ButtonStyle.primary, emoji=Ems.phone_numbers[1])
    async def button1(self, ntr, btn):
        await self.paginator.goto_page(page_number=1, ntr=ntr)

    @ui.button(label="LoL", style=ButtonStyle.primary, emoji=Ems.phone_numbers[2])
    async def button2(self, ntr, btn):
        await self.paginator.goto_page(page_number=2, ntr=ntr)

    @ui.button(label="Info", style=ButtonStyle.primary, emoji=Ems.phone_numbers[3])
    async def button3(self, ntr, btn):
        await self.paginator.goto_page(page_number=3, ntr=ntr)

    @ui.button(label="Tools", style=ButtonStyle.primary, emoji=Ems.phone_numbers[4])
    async def button4(self, ntr, btn):
        await self.paginator.goto_page(page_number=4, ntr=ntr)


def get_starting_embed(ctx):
    footer_text = f'With love, {ctx.bot.user.display_name}'
    thumb_url = ctx.bot.user.display_avatar.url
    embed_dict = {
        '🏠': first_page(ctx),
        'Dota 2':
            Embed(
                color=Clr.prpl, title="Dota 2 feed related commands",
                description=f'{Ems.phone_numbers[1]} Commands to control Dota 2 feed in {cmntn(Cid.irene_bot)}',
            ).set_footer(text=footer_text).set_thumbnail(url=thumb_url),
        'LoL':
            Embed(
                color=Clr.prpl, title="LoL feed related commands",
                description=f'{Ems.phone_numbers[2]} Commands to control LoL feed in {cmntn(Cid.irene_bot)}',
            ).set_footer(text=footer_text).set_thumbnail(url=thumb_url),
        'AdminInfo':
            Embed(
                color=Clr.prpl, title="AdminInfo commands",
                description=f'{Ems.phone_numbers[3]} Commands AdminInfo',
            ).set_footer(text=footer_text).set_thumbnail(url=thumb_url),
        'AdminTools':
            Embed(
                color=Clr.prpl, title="AdminTools commands",
                description=f'{Ems.phone_numbers[4]} Commands AdminTools',
            ).set_footer(text=footer_text).set_thumbnail(url=thumb_url),
    }
    return embed_dict


class AdminHelpCog(commands.Cog):
    def __init__(self, bot):
        self.help_category = 'Info'
        command_attrs = {
            'name': 'helpadmin',
            'checks': [commands.is_owner().predicate],
            'help': 'Show special help menu for the bot admin',
            'brief': Ems.slash
        }
        bot.help3_command = HelpCommand(
            get_starting_embed,
            ViewHelpAdmin,
            command_attrs=command_attrs,
            verify_checks=False)
        bot.help3_command.cog = self

    @commands.is_owner()
    @app_commands.default_permissions(administrator=True)
    @app_commands.command(
        name='helpadmin',
        description='Show special help menu for the bot admin'
    )
    async def help_slash(self, ntr: Interaction):
        myhelp = HelpCommand(
            get_starting_embed,
            ViewHelpAdmin,
            verify_checks=False
        )
        myhelp.context = await commands.Context.from_interaction(ntr)
        await myhelp.command_callback(myhelp.context)


async def setup(bot):
    await bot.add_cog(AdminHelpCog(bot))
