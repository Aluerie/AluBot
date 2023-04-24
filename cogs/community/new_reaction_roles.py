from __future__ import annotations

from typing import TYPE_CHECKING

import discord
from discord.ext import commands

from utils.checks import is_owner
from utils.var import Cid, Clr, Sid

if TYPE_CHECKING:
    from utils.bot import AluBot
    from utils.context import Context


class ColourRolesDropdown(discord.ui.RoleSelect):
    def __init__(self):
        super().__init__(
            custom_id='colour_roles_dropdown',
            placeholder='Type \N{KEYBOARD} name of a colour and Select it.'
        )

    async def callback(self, ntr: discord.Interaction[AluBot]):
        colour_category_role = ntr.client.community.guild.get_role(851786344354938880)
        activity_category_role = ntr.client.community.guild.get_role(852199351808032788)

        def is_colour_role(role: discord.Role) -> bool:
            return  activity_category_role < role < colour_category_role

        role = self.values[0]
        try:
            if is_colour_role(role):
                pass
            else:
                raise ValueError
        except ValueError:
            e = discord.Embed(color=Clr.error)
            e.description = 'You are trying to choose non-colour role, which I won\'t give.'
            await ntr.response.send_message(embed=e, ephemeral=True)
        else:
            member = ntr.client.community.guild.get_member(ntr.user.id)
            if member is not None:
                if role in member.roles:
                    await member.remove_roles(role)

                    e = discord.Embed(color=role.color)
                    e.description = f'Removed {role.mention} colour role!'
                    await ntr.response.send_message(embed=e, ephemeral=True)
                else:
                    for r in member.roles:
                        if is_colour_role(r):
                            await member.remove_roles(r)
                    await member.add_roles(role)

                    e = discord.Embed(color=role.color)
                    e.description = f'Added {role.mention} colour role!'
                    await ntr.response.send_message(embed=e, ephemeral=True)
            else:
                return ntr.response.send_message('Something went wrong...', ephemeral=True)


class ColourRolesView(discord.ui.View):
    def __init__(self):
        super().__init__(timeout=None)
        # Adds the dropdown to our view object.
        self.add_item(ColourRolesDropdown())


class ColourRoles(commands.Cog):
    def __init__(self, bot: AluBot):
        self.bot: AluBot = bot

    @commands.Cog.listener()
    async def on_ready(self):
        self.bot.add_view(ColourRolesView())

    @is_owner()
    @commands.command(hidden=True)
    async def role_selection(self, ctx: Context):
        e = discord.Embed(title='\N{LOWER LEFT PAINTBRUSH} Colour Roles \N{LOWER LEFT PAINTBRUSH}')
        e.colour = 0x9400D3
        e.description = (
            '\N{HEAVY BLACK HEART} If you want to have a custom colour to your username/nickname, then please: do the following\n'
            '* \N{DIGIT ONE}\N{COMBINING ENCLOSING KEYCAP} Find your desired colour from 140 available colours in a table in the attached image below.\n'
            '* \N{DIGIT TWO}\N{COMBINING ENCLOSING KEYCAP} **(!)Type** name of your chosen role in drop-down menu below and Select it.\n'
            '* \N{DIGIT THREE}\N{COMBINING ENCLOSING KEYCAP} Done! You should get your desired role and colour.\n'
            '\n'
            '* Note that the bot won\'t give you any other roles than colour roles.\n'
            '\n'
            '\N{PURPLE HEART} And by the way, your chosen custom colour will override colours of special roles if you have ones.'
        )
        e.set_image(url='https://i.imgur.com/bHEpVlb.png')

        await ctx.send(embed=e, view=ColourRolesView())
        # await self.bot.community.role_selection.send(embed=e, view=ColourRolesView())


async def setup(bot: AluBot):
    await bot.add_cog(ColourRoles(bot))
