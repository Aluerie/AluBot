from __future__ import annotations
from typing import TYPE_CHECKING

from discord.ext import commands, tasks
from discord import Embed, File

from utils.var import *
from utils import database as db

import re
from datetime import datetime, timezone, timedelta

if TYPE_CHECKING:
    from utils.bot import AluBot


class DotaComments(commands.Cog):
    def __init__(self, bot: AluBot):
        self.bot = bot
        self.git_comments_check.start()

    @tasks.loop(minutes=5)
    async def git_comments_check(self):
        repo = self.bot.git_gameplay

        assignees = [x.login for x in repo.get_assignees()]

        dt = db.get_value(db.g, Sid.alu, 'git_checked_dt').replace(tzinfo=timezone.utc)
        db.set_value(db.g, Sid.alu, git_checked_dt=datetime.now(timezone.utc))

        # dt = datetime.now(timezone.utc) - timedelta(days=8) # testing
        for c in [x for x in repo.get_issues_comments(sort='updated', since=dt) if x.user.login in assignees]:
            c_num = [int(s) for s in re.findall(r'\d+', c.issue_url)][1]  # first is 2 from Dota2, second is issues/32
            issue = repo.get_issue(c_num)
            em = Embed(
                colour=0x4078c0,
                title=issue.title,
                url=issue.html_url,
                description=c.body
            ).set_author(
                name=f'@{c.user.login} commented in bugtracker issue #{issue.number}',
                icon_url=c.user.avatar_url,
                url=c.html_url
            )
            msg = await self.bot.get_channel(Cid.dota_news).send(embed=em)
            await msg.publish()

        for i in repo.get_issues(sort='updated', state='all', since=dt):
            clr_dict = {
                'assigned': {'clr': 0x21262D, 'pic': './media/person.png'},
                'closed': {'clr': 0x9B6CEA, 'pic': './media/check-circle.png'},
                'reopened': {'clr': 0x238636, 'pic': './media/issue-reopened.png'}
            }

            events = [
                x for x in i.get_events()
                if x.created_at.replace(tzinfo=timezone.utc) > dt
                and x.actor.login in assignees
                and x.event in clr_dict
            ]
            for e in events:
                image_name = 'gitcheck.png'
                img_file = File(clr_dict[e.event]['pic'], filename=image_name)

                em = Embed(
                    colour=clr_dict[e.event]['clr'],
                    description=f'[{e.issue.title}]({e.issue.html_url})'
                ).set_author(
                    name=f'@{e.actor.login} {e.event} bugtracker issue #{e.issue.number}',
                    icon_url=e.actor.avatar_url,
                    url=e.issue.html_url
                ).set_thumbnail(
                    url=f'attachment://{image_name}'
                )
                msg = await self.bot.get_channel(Cid.dota_news).send(embed=em, file=img_file)
                await msg.publish()

    @git_comments_check.before_loop
    async def before(self):
        await self.bot.wait_until_ready()


async def setup(bot):
    await bot.add_cog(DotaComments(bot))
