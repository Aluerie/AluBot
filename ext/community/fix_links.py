from __future__ import annotations

from typing import TYPE_CHECKING

import discord
from discord import app_commands
from discord.ext import commands

from ext.utilities.utilities.fix_links import fix_link_worker
from utils import const, errors, links, webhook_mimicry

from ._base import CommunityCog

if TYPE_CHECKING:
    pass


class FixLinksCommunity(CommunityCog):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.delete_mimic_ctx_menu = app_commands.ContextMenu(
            name="Delete Mimic message",
            callback=self.delete_mimic_ctx_menu_callback,
        )

    def cog_load(self) -> None:
        self.bot.tree.add_command(self.delete_mimic_ctx_menu)

    def cog_unload(self) -> None:
        c = self.delete_mimic_ctx_menu
        self.bot.tree.remove_command(c.name, type=c.type)

    async def delete_mimic_ctx_menu_callback(
        self, interaction: discord.Interaction[commands.Bot], message: discord.Message
    ):
        # todo: why it's there, wrong cog
        if self.bot.mimic_message_user_mapping.get(message.id) == interaction.user.id:
            # ^ userid_ttl[0] represents both
            # the message in cache and belongs to the interaction author (user)
            await message.delete()
            e = discord.Embed(colour=const.Colour.blueviolet)
            e.description = "Successfully deleted your Mimic message."
            await interaction.response.send_message(embed=e, ephemeral=True)
            return
        elif not message.webhook_id:
            raise errors.UserError("This message was not mimicked by my MimicUser functionality.")
        else:
            raise errors.SomethingWentWrong(
                "Either this message\n"
                "* was not mimicked by me\n"
                "* expired from cache (7 days)\n"
                "* or cache was reset (because of reboot). \nSorry. You have to ask moderators to delete it."
            )

    @commands.Cog.listener("on_message")
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

        mimic = webhook_mimicry.MimicUserWebhook.from_message(bot=self.bot, message=message)
        msg = await mimic.send_user_message(message.author, message=message, content=fixed_links)
        await message.delete()
        await links.extra_send_fxtwitter_links(msg)


async def setup(bot):
    await bot.add_cog(FixLinksCommunity(bot))
