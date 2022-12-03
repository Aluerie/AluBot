from __future__ import annotations

from typing import TYPE_CHECKING

from discord import ButtonStyle, Embed, TextStyle
from discord.ext import commands
from discord.ui import Modal, TextInput, View, button

from .utils.distools import send_traceback
from .utils.format import display_time
from .utils.var import Ems, Clr

if TYPE_CHECKING:
    from discord import Interaction
    from discord.ui import Item, Button
    from .utils.bot import AluBot


class ButtonOnCooldown(commands.CommandError):
    def __init__(self, retry_after: float):
        self.retry_after = retry_after


def key(ntr: Interaction):
    return ntr.user


# rate of 1 token per 30 minutes using our key function
cd = commands.CooldownMapping.from_cooldown(1.0, 30.0 * 60, key)


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
        em = Embed(
            colour=Clr.prpl,
            title=self.title,
            description=self.conf.value
        ).set_footer(
            text="Use buttons below to make a new confession in this channel"
        )
        if self.title == "Non-anonymous confession":
            em.set_author(
                name=ntr.user.display_name,
                icon_url=ntr.user.display_avatar.url
            )
        await ntr.channel.send(embeds=[em])
        await ntr.channel.send(
            '{0} {0} {0} {1} {1} {1} {2} {2} {2}'.format(Ems.bubuChrist, '⛪', Ems.PepoBeliever)
        )
        await ntr.response.send_message(content=f"The Lord be with you {Ems.PepoBeliever}", ephemeral=True)
        try:
            await ntr.message.delete()
        except AttributeError:  # was already deleted  `AttributeError: 'NoneType' object has no attribute 'delete'`
            pass
        await ntr.channel.send(view=ConfView())
        cd.update_rate_limit(ntr)


class ConfView(View):
    def __init__(self):
        super().__init__(timeout=None)

    async def interaction_check(self, ntr: Interaction) -> bool:
        # retry_after = self.cd.update_rate_limit(ntr) # returns retry_after which is nice
        retry_after = cd.get_bucket(ntr).get_retry_after()
        if retry_after:
            raise ButtonOnCooldown(retry_after)
        return True

    async def on_error(self, ntr: Interaction, error: Exception, item: Item):
        if isinstance(error, ButtonOnCooldown):
            em = Embed(colour=Clr.error)
            em.description = f"Sorry, you are on cooldown \nTime left `{display_time(error.retry_after, 3)}`"
            em.set_author(name=error.__class__.__name__)
            await ntr.response.send_message(embed=em, ephemeral=True)
        else:
            # await super().on_error(ntr, error, item) # original on_error
            await send_traceback(error, ntr.client)

    @button(
        label="Anonymous confession",
        custom_id="anonconf-button",
        style=ButtonStyle.primary,
        emoji=Ems.bubuChrist
    )
    async def button0_callback(self, ntr: Interaction, btn: Button):
        await ntr.response.send_modal(ConfModal(title=btn.label))

    @button(
        label="Non-anonymous confession",
        custom_id="nonanonconf-button",
        style=ButtonStyle.primary,
        emoji=Ems.PepoBeliever
    )
    async def button1_callback(self, ntr: Interaction, btn: Button):
        await ntr.response.send_modal(ConfModal(title=btn.label))


class Confession(commands.Cog):
    def __init__(self, bot):
        self.bot: AluBot = bot

    @commands.Cog.listener()
    async def on_ready(self):
        self.bot.add_view(ConfView())  # Registers a View for persistent listening

        # very silly testing way
        # print('hello')
        # await self.bot.get_channel(Cid.spam_me).send(view=ConfView())


async def setup(bot):
    await bot.add_cog(Confession(bot))
