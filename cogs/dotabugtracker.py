from __future__ import annotations

import re
from datetime import datetime, timezone
from typing import TYPE_CHECKING

from discord import Embed, File
from discord.ext import commands, tasks

from .utils.var import Sid, Cid

if TYPE_CHECKING:
    from .utils.bot import AluBot


class DotaBugtracker(commands.Cog):
    def __init__(self, bot):
        self.bot: AluBot = bot
        self.git_comments_check.start()

    def cog_load(self) -> None:
        self.bot.ini_github()

    def cog_unload(self) -> None:
        self.git_comments_check.cancel()

    @tasks.loop(minutes=5)
    async def git_comments_check(self):
        repo = self.bot.git_gameplay

        assignees = [x.login for x in repo.get_assignees()]

        query = 'SELECT git_checked_dt FROM botinfo WHERE id=$1'
        dt: datetime = await self.bot.pool.fetchval(query, Sid.alu)

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

        clr_dict = {
            'assigned': {
                'clr': 0x21262D,
                'pic': './media/person.png',
                'word': 'self-assigned'
            },
            'closed': {
                'clr': 0x9B6CEA,
                'pic': './media/check-circle.png',
                'word': 'closed'
            },
            'reopened': {
                'clr': 0x238636,
                'pic': './media/issue-reopened.png',
                'word': 'reopened'
            }
        }
        for i in repo.get_issues(sort='updated', state='all', since=dt):
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
                    title=e.issue.title,
                    url=e.issue.html_url
                ).set_author(
                    name=f'@{e.actor.login} {clr_dict[e.event]["word"]} bugtracker issue #{e.issue.number}',
                    icon_url=e.actor.avatar_url,
                    url=e.issue.html_url
                ).set_thumbnail(
                    url=f'attachment://{image_name}'
                )
                msg = await self.bot.get_channel(Cid.dota_news).send(embed=em, file=img_file)
                await msg.publish()

        query = 'UPDATE botinfo SET git_checked_dt=$1 WHERE id=$2'
        await self.bot.pool.execute(query, datetime.now(timezone.utc), Sid.alu)

    @git_comments_check.before_loop
    async def before(self):
        await self.bot.wait_until_ready()


async def setup(bot):
    await bot.add_cog(DotaBugtracker(bot))
