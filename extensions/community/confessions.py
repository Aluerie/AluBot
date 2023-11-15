from __future__ import annotations

from typing import TYPE_CHECKING

import discord
from discord.ext import commands

from utils.const import Colour, Emote
from utils.formats import human_timedelta

from ._base import CommunityCog

if TYPE_CHECKING:
    from utils import AluBot


class ButtonOnCooldown(commands.CommandError):
    def __init__(self, retry_after: float):
        self.retry_after: float = retry_after


def key(ntr: discord.Interaction):
    return ntr.user


# rate of 1 token per 30 minutes using our key function
cd = commands.CooldownMapping.from_cooldown(1.0, 30.0 * 60, key)


class ConfModal(discord.ui.Modal):
    def __init__(self, *args, **kwargs) -> None:
        super().__init__(*args, **kwargs)

    conf = discord.ui.TextInput(
        label="Make confession to the server",
        style=discord.Textensionstyle.long,
        placeholder='Type your confession text here',
        max_length=4000,
    )

    async def on_submit(self, ntr: discord.Interaction):
        e = discord.Embed(title=self.title, colour=Colour.prpl(), description=self.conf.value)
        e.set_footer(text="Use buttons below to make a new confession in this channel")
        if self.title == "Non-anonymous confession":
            e.set_author(name=ntr.user.display_name, icon_url=ntr.user.display_avatar.url)
        channel = ntr.channel
        assert isinstance(channel, discord.TextChannel)

        await channel.send(embeds=[e])
        saint_string = '{0} {0} {0} {1} {1} {1} {2} {2} {2}'.format(Emote.bubuChrist, '\N{CHURCH}', Emote.PepoBeliever)
        await channel.send(saint_string)
        await ntr.response.send_message(content=f"The Lord be with you {Emote.PepoBeliever}", ephemeral=True)
        if ntr.message:
            await ntr.message.delete()
        await channel.send(view=ConfView())
        cd.update_rate_limit(ntr)


class ConfView(discord.ui.View):
    def __init__(self):
        super().__init__(timeout=None)

    async def interaction_check(self, ntr: discord.Interaction) -> bool:
        # retry_after = self.cd.update_rate_limit(ntr) # returns retry_after which is nice
        bucket = cd.get_bucket(ntr)
        if bucket and (retry_after := bucket.get_retry_after()):
            raise ButtonOnCooldown(retry_after)
        return True

    async def on_error(self, ntr: discord.Interaction[AluBot], error: Exception, item: discord.ui.Item):
        if isinstance(error, ButtonOnCooldown):
            e = discord.Embed(colour=Colour.error()).set_author(name=error.__class__.__name__)
            e.description = (
                "Sorry, you are on cooldown \n" f"Time left `{human_timedelta(error.retry_after, brief=True)}`"
            )
            await ntr.response.send_message(embed=e, ephemeral=True)
        else:
            # await super().on_error(ntr, error, item) # original on_error
            await ntr.client.exc_manager.register_error(error, 'Confessions', where='Confessions')

    @discord.ui.button(
        label="Anonymous confession",
        custom_id="anonconf-button",
        style=discord.ButtonStyle.primary,
        emoji=Emote.bubuChrist,
    )
    async def button0_callback(self, ntr: discord.Interaction, btn: discord.ui.Button):
        await ntr.response.send_modal(ConfModal(title=btn.label))

    @discord.ui.button(
        label="Non-anonymous confession",
        custom_id="nonanonconf-button",
        style=discord.ButtonStyle.primary,
        emoji=Emote.PepoBeliever,
    )
    async def button1_callback(self, ntr: discord.Interaction, btn: discord.ui.Button):
        await ntr.response.send_modal(ConfModal(title=btn.label))


class Confession(CommunityCog):
    @commands.Cog.listener()
    async def on_ready(self):
        self.bot.add_view(ConfView())  # Registers a View for persistent listening

        # very silly testing way
        # print('hello')
        # await self.bot.get_channel(Channel.spam_me).send(view=ConfView())


async def setup(bot: AluBot):
    await bot.add_cog(Confession(bot))
