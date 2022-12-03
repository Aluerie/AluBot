from __future__ import annotations

import re
from datetime import datetime, timezone, timedelta
from typing import TYPE_CHECKING, Literal

from discord import Embed, File
from discord.ext import commands, tasks

from .utils.var import Sid, Cid

if TYPE_CHECKING:
    from .utils.bot import AluBot
    from github import Issue, NamedUser


# fancy dictionary with all actions

clr_dict = {
    'assigned': {'clr': 0x21262D, 'pic': './media/person.png', 'word': 'self-assigned'},
    'closed': {'clr': 0x9B6CEA, 'pic': './media/check-circle.png', 'word': 'closed'},
    'reopened': {'clr': 0x238636, 'pic': './media/issue-reopened.png', 'word': 'reopened'}
}


class GitEvent:

    def __init__(
            self,
            *,
            event_type: Literal['assigned', 'closed', 'reopened', 'commented'],
            created_at: datetime,
            actor: NamedUser,
            body: str = None
    ):
        self.event_type = event_type
        self.created_at = created_at.replace(tzinfo=timezone.utc)
        self.title = issue.title
        self.issue_url = issue.url

        self.body = body





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
        # dt: datetime = await self.bot.pool.fetchval(query, Sid.alu)

        dt = datetime.now(timezone.utc) - timedelta(days=2)  # testing

        issue_dict = dict()

        for i in repo.get_issues(sort='updated', state='all', since=dt):
            events = [
                x for x in i.get_events()
                if x.created_at.replace(tzinfo=timezone.utc) > dt
                and x.actor.login in assignees
                and x.event in clr_dict
            ]
            for e in events:

                img_file = File(clr_dict[e.event]['pic'], filename='gitcheck.png')

                em = Embed(colour=clr_dict[e.event]['clr'], title=e.issue.title, url=e.issue.html_url)
                action_str = f'@{e.actor.login} {clr_dict[e.event]["word"]} bugtracker issue #{e.issue.number}'
                em.set_author(name=action_str, icon_url=e.actor.avatar_url, url=e.issue.html_url)
                em.set_thumbnail(url=f'attachment://{img_file.filename}')

                key = f'{e.issue.number}_{e.actor.login}'
                issue_dict.setdefault(key, []).append(
                    {'created_at': e.created_at, 'embed': em, 'file': img_file}
                )

        for c in [x for x in repo.get_issues_comments(sort='updated', since=dt) if x.user.login in assignees]:

            # just take numbers from url string ".../Dota2-Gameplay/issues/2524" with `.split`
            issue_num = int(c.issue_url.split('/')[-1])
            issue = repo.get_issue(issue_num)

            if cem := issue_dict.get(f'{issue.number}_{c.user.login}'):
                def work_with_body(body: str) -> str:
                    url_regex = re.compile(r'(https://github.com/ValveSoftware/Dota2-Gameplay/issues/(\d+))')
                    body = url_regex.sub(r'[#\2](\1)', body)
                    body = '\n'.join([line for line in body.splitlines() if line])
                    return body.replace('<br>', '')

                # find closest to created_at event to give it the comment
                curr_delta, curr_i = timedelta(days=30), 0
                for i in range(len(cem)):
                    if abs(cem[i]['created_at'] - c.created_at) < curr_delta:
                        curr_i = i

                if cem[curr_i]['embed'].description:
                    cem[curr_i]['embed'].add_field(name='And later added', value=work_with_body(c.body))
                else:
                    cem[curr_i]['embed'].description = work_with_body(c.body)
            else:
                em = Embed(colour=0x4078c0, title=issue.title, url=issue.html_url, description=c.body)
                action_str = f'@{c.user.login} commented bugtracker issue #{issue.number}'
                em.set_author(name=action_str, icon_url=c.user.avatar_url, url=c.html_url)
                key = f'{issue.number}_{c.user.login}'
                issue_dict.setdefault(key, []).append({'embed': em, 'file': None})

        #query = 'UPDATE botinfo SET git_checked_dt=$1 WHERE id=$2'
        #await self.bot.pool.execute(query, datetime.now(timezone.utc), Sid.alu)

        for v in issue_dict.values():
            for i in v:
                await self.bot.get_channel(Cid.spam_me).send(embed=i['embed'], file=i['file'])

    @git_comments_check.before_loop
    async def before(self):
        await self.bot.wait_until_ready()


async def setup(bot):
    await bot.add_cog(DotaBugtracker(bot))
