from __future__ import annotations

from datetime import datetime, timezone
from typing import TYPE_CHECKING

from PIL import Image, ImageDraw, ImageFilter, ImageFont
from discord import Embed, Member
from discord.ext import commands

from .utils.checks import is_owner
from .utils.imgtools import url_to_img, img_to_file, get_text_wh
from .utils.var import Cid, Clr, Ems, Rid, Sid, Uid, umntn

if TYPE_CHECKING:
    from .utils.bot import AluBot


class Milestone(commands.Cog):
    def __init__(self, bot):
        self.bot: AluBot = bot

    @commands.Cog.listener()
    async def on_member_join(self, member):
        if member.guild.id != Sid.alu:
            return
        mile_rl = member.guild.get_role(Rid.milestone)
        milestone_achieved = db.get_value(db.b, Sid.alu, 'milestone_achieved')
        amount_members = member.guild.member_count

        if amount_members > milestone_achieved and amount_members % 50 == 0:
            milestone_achieved = amount_members
            db.set_value(db.b, Sid.alu, milestone_achieved=milestone_achieved)
            await member.add_roles(mile_rl)

            em = Embed(
                color=Clr.prpl,
                title=f'{Ems.PogChampPepe} Milestone reached !',
                description=
                f'Our server reached {milestone_achieved} members ! '
                f'{member.mention} is our latest milestone member '
                f'who gets a special lucky {mile_rl.mention} role. Congrats !'
            ).set_thumbnail(
                url=member.guild.icon_url
            ).set_footer(
                text=f"With love, {member.guild.me.display_name}"
            )
            await self.bot.get_channel(Cid.welcome).send(embed=em)


async def setup(bot):
    await bot.add_cog(Milestone(bot))