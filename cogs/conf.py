from __future__ import annotations
from typing import TYPE_CHECKING

from discord import ButtonStyle, Embed, TextStyle
from discord.ext import commands
from discord.ui import Modal, TextInput, View, button

from utils.var import Clr, Ems
from utils.format import humanize_time
from datetime import datetime, timedelta, timezone

if TYPE_CHECKING:
    from discord import Interaction

cd_dct = {}


class ConfModal(Modal):
    def __init__(self, *args, **kwargs) -> None:
        super().__init__(*args, **kwargs)

    conf = TextInput(
        label="Make confession to the server",
        style=TextStyle.long,
        placeholder='Type your confession text here',
        max_length=4000,
    )

    async def on_submit(self, ntr: Interaction):
        embed = Embed(colour=Clr.prpl, title=self.title)
        if self.title == "Non-anonymous confession":
            embed.set_author(name=ntr.user.display_name, icon_url=ntr.user.display_avatar.url)
        embed.description = self.conf.value
        embed.set_footer(text="Use buttons below to make a new confession in this channel")
        await ntr.channel.send(embeds=[embed])
        sacred_string = '{0} {0} {0} {1} {1} {1} {2} {2} {2}'.format(Ems.bubuChrist, '⛪', Ems.PepoBeliever)
        await ntr.channel.send(sacred_string)
        await ntr.response.send_message(content=f"The Lord be with you {Ems.PepoBeliever}", ephemeral=True)
        await ntr.message.delete()
        await ntr.channel.send(view=ConfView())
        cd_dct[ntr.user.id] = datetime.now(timezone.utc)


class ConfView(View):
    def __init__(self):
        super().__init__(timeout=None)

    async def interaction_check(self, ntr) -> bool:
        if ntr.user.id in cd_dct:
            if (time_pass := datetime.now(timezone.utc) - cd_dct[ntr.user.id]) < timedelta(minutes=30):
                embed = Embed(colour=Clr.prpl)
                embed.description = \
                    f"Sorry, you are on cooldown \n" \
                    f"Time left {humanize_time(timedelta(minutes=30) - time_pass)}"
                await ntr.response.send_message(embed=embed, ephemeral=True)
                return False
        return True

    @button(
        label="Anonymous confession",
        custom_id="anonconf-button",
        style=ButtonStyle.primary,
        emoji=Ems.bubuChrist
    )
    async def button0_callback(self, ntr, btn):
        await ntr.response.send_modal(ConfModal(title=btn.label))

    @button(
        label="Non-anonymous confession",
        custom_id="nonanonconf-button",
        style=ButtonStyle.primary,
        emoji=Ems.PepoBeliever
    )
    async def button1_callback(self, ntr, btn):
        await ntr.response.send_modal(ConfModal(title=btn.label))


class Confession(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @commands.Cog.listener()
    async def on_ready(self):
        self.bot.add_view(ConfView())  # Registers a View for persistent listening


async def setup(bot):
    await bot.add_cog(Confession(bot))
