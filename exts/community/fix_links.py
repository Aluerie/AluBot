from __future__ import annotations

import asyncio
import datetime
import re
from typing import TYPE_CHECKING

import discord
from discord import app_commands
from discord.ext import commands

from exts.utilities.utilities.fix_links import fix_link_worker
from utils import const, errors, webhook

from ._category import CommunityCog

if TYPE_CHECKING:
    pass


class FixLinksCommunity(CommunityCog):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.delete_mimic_ctx_menu = app_commands.ContextMenu(
            name='Delete Mimic message', callback=self.delete_mimic_ctx_menu_callback
        )

    def cog_load(self) -> None:
        self.bot.tree.add_command(self.delete_mimic_ctx_menu)

    def cog_unload(self) -> None:
        c = self.delete_mimic_ctx_menu
        self.bot.tree.remove_command(c.name, type=c.type)

    async def delete_mimic_ctx_menu_callback(self, ntr: discord.Interaction[commands.Bot], message: discord.Message):
        if self.bot.mimic_message_user_mapping.get(message.id) == ntr.user.id:  # type: ignore # it's not int, it's Tuple[int, float]
            # ^ userid_ttl[0] represents both
            # the message in cache and belongs to the interaction author (user)
            await message.delete()
            e = discord.Embed(colour=const.Colour.prpl())
            e.description = 'Successfully deleted your Mimic message.'
            await ntr.response.send_message(embed=e, ephemeral=True)
            return
        elif not message.webhook_id:
            raise errors.UserError('This message was not mimicked by my MimicUser functionality.')
        else:
            raise errors.SomethingWentWrong(
                'Either this message\n'
                '* was not mimicked by me\n'
                '* expired from cache (7 days)\n'
                '* or cache was reset (because of reboot). \nSorry. You have to ask moderators to delete it.'
            )

    @commands.Cog.listener('on_message')
    async def fix_links(self, message: discord.Message):
        if not message.guild:
            return
        elif message.guild.id not in const.MY_GUILDS:
            return
        if message.author.bot:
            return

        fixed_links = fix_link_worker(message.content)
        if not fixed_links:
            return

        try:
            mimic = webhook.MimicUserWebhook.from_message(bot=self.bot, message=message)
            msg = await mimic.send_user_message(message.author, message=message, content=fixed_links)
            await message.delete()
            await asyncio.sleep(1)

            # Okay discord is a bit stupid and does not allow hyperlinks from website embeds
            # this is why I will have to do the job myself.
            links = []
            colour = const.Colour.pink()
            for e in msg.embeds:
                e = e.copy()
                links += re.findall(const.REGEX_URL_LINK, str(e.description))
                colour = e.colour

            if links:
                e = discord.Embed(color=colour)
                e.description = '\n'.join(links)
                await mimic.send_user_message(message.author, embed=e)

        except Exception as err:
            print(err)


async def setup(bot):
    await bot.add_cog(FixLinksCommunity(bot))
