from __future__ import annotations

from typing import TYPE_CHECKING, Any, override

import discord
from discord import app_commands

from bot import AluCog
from utils import const, errors

if TYPE_CHECKING:
    from bot import AluBot, AluInteraction


class Mimics(AluCog):
    """Manage your mimic messages.

    Mimic messages are messages that the bot sends from users name by copying your name/avatar and
    using a webhook to send it so it looks like you sent it (but it has "bot" tag).
    Commands here allow proper managing of those messages,
    i.e. edit/delete/check functionality via application context menu commands.

    Currently, mimic messages are used for:
    * Fix social links to proper embeds;
    """

    def __init__(self, *args: Any, **kwargs: Any) -> None:
        super().__init__(*args, **kwargs)
        self.delete_mimic = app_commands.ContextMenu(
            name="Delete Mimic Message",
            callback=self.delete_mimic_callback,
        )

    @override
    async def cog_load(self) -> None:
        await super().cog_load()
        self.bot.tree.add_command(self.delete_mimic)

    @override
    async def cog_unload(self) -> None:
        await super().cog_unload()
        c = self.delete_mimic
        self.bot.tree.remove_command(c.name, type=c.type)

    async def delete_mimic_callback(self, interaction: AluInteraction, message: discord.Message) -> None:
        """Callback function for Application Context Menu command "Delete Mimic Message"."""
        if self.bot.mimic_messages.get(message.id) == interaction.user.id:
            # the message is in cache and belongs to the interaction author (user)
            await message.delete()
            embed = discord.Embed(color=const.Color.prpl, description="Successfully deleted your Mimic message.")
            await interaction.response.send_message(embed=embed, ephemeral=True)
            return

        if not message.webhook_id:
            msg = "This message was not mimicked by my MimicUser functionality."
            raise errors.UserError(msg)

        msg = (
            "Either this message\n"
            "* was not mimicked by me\n"
            "* expired from cache (7 days)\n"
            "* or cache was reset (because of reboot). \nSorry. You have to ask moderators to delete it."
        )
        raise errors.SomethingWentWrong(msg)


async def setup(bot: AluBot) -> None:
    """Load AluBot extension. Framework of discord.py."""
    await bot.add_cog(Mimics(bot))
