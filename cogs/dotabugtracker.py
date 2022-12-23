from __future__ import annotations

import re
from datetime import datetime, timezone
from typing import TYPE_CHECKING, Literal, List, Set

from discord import Embed, File
from discord.ext import commands, tasks

from .utils.var import Sid, Cid, Clr, Lmt

if TYPE_CHECKING:
    from .utils.bot import AluBot
    from github import Issue, NamedUser

# fancy dictionary with all actions

clr_dict = {
    'assigned': {'clr': 0x21262D, 'pic': './media/person.png', 'word': 'self-assigned'},
    'closed': {'clr': 0x9B6CEA, 'pic': './media/check-circle.png', 'word': 'closed'},
    'reopened': {'clr': 0x238636, 'pic': './media/issue-reopened.png', 'word': 'reopened'},
    'commented': {'clr': 0x4078c0, 'pic': './media/person.png', 'word': 'commented'}  # todo: make a new picture
}


class TimeLinePoint:

    def __init__(
            self,
            *,
            event_type: Literal['assigned', 'closed', 'reopened', 'commented'],
            created_at: datetime,
            actor: NamedUser,
            issue_number: int,
            body: str = '',
            html_url: str = ''
    ):
        self.event_type = event_type
        self.comment_flag = True if event_type == 'commented' else False
        self.created_at = created_at.replace(tzinfo=timezone.utc)
        self.actor: NamedUser = actor
        self.body = body
        self.html_url = html_url
        self.issue_number = issue_number

    @property
    def colour(self):
        return clr_dict[self.event_type]['clr']

    @property
    def file(self):
        return File(clr_dict[self.event_type]['pic'], filename='gitcheck.png')

    @property
    def author_str(self) -> str:
        return f'@{self.actor.login} {clr_dict[self.event_type]["word"]} bugtracker issue #{self.issue_number}'

    @property
    def markdown_body(self) -> str:
        if self.body == '':  # just skip the work if it is empty
            return self.body
        url_regex = re.compile(r'(https://github.com/ValveSoftware/Dota2-Gameplay/issues/(\d+))')
        body = url_regex.sub(r'[#\2](\1)', self.body)
        body = '\n'.join([line for line in body.splitlines() if line])
        return body.replace('<br>', '')


class TimeLine:

    def __init__(
            self,
            issue: Issue,
    ):
        self.issue: Issue = issue

        self.events: List[TimeLinePoint] = []
        self.comments: List[TimeLinePoint] = []
        self.authors: Set[str] = set()

    def add_event(self, event: TimeLinePoint):
        if event.comment_flag:
            self.comments.append(event)
        else:
            self.events.append(event)
        self.authors.add(event.actor)

    def sorted_points_list(self):
        return sorted(self.events + self.comments, key=lambda x: x.created_at, reverse=False)

    @property
    def embed_and_file(self) -> (Embed, File):  # todo: is there any better way than make your own constants?
        em = Embed(title=self.issue.title[:Lmt.Embed.title], url=self.issue.html_url)
        if len(self.events) < 2 and len(self.comments) < 2 and len(self.authors) < 2:
            # we just send a small embed
            # 1 author and 1 event with possible comment event to it
            e = next(iter(self.events), None)  # first element in self.events or None if not exist
            c = next(iter(self.comments), None)  # first element in self.comments or None if not exist

            l = e or c  # lead_event
            if l is None:
                raise RuntimeError('Somehow lead_event is None')

            em.colour = l.colour
            em.set_author(name=l.author_str, icon_url=l.actor.avatar_url, url=l.html_url)
            em.description = c.markdown_body if c else ''
            file = l.file
            em.set_thumbnail(url=f'attachment://{file.filename}')
        else:
            em.colour = Clr.prpl
            for p in (sorted_points := self.sorted_points_list()):
                em.add_field(name=p.author_str, value=p.markdown_body)  # todo: this might go beyond 6k symbols
            em.set_author(name=f'bugtracker issue #{self.issue.number} update', url=sorted_points[-1].html_url)
            file = None
        return em, file


class DotaBugtracker(commands.Cog):
    def __init__(self, bot):
        self.bot: AluBot = bot
        self.git_comments_check.start()

    def cog_load(self) -> None:
        self.bot.ini_github()

    def cog_unload(self) -> None:
        self.git_comments_check.cancel()

    @tasks.loop(minutes=10)
    async def git_comments_check(self):
        repo = self.bot.git_gameplay

        assignees = [x.login for x in repo.get_assignees()]

        query = 'SELECT git_checked_dt FROM botinfo WHERE id=$1'
        dt: datetime = await self.bot.pool.fetchval(query, Sid.alu)

        # from datetime import timedelta  # <- for testing
        # dt = datetime.now(timezone.utc) - timedelta(days=2)  # <- for testing

        issue_dict = dict()

        for i in repo.get_issues(sort='updated', state='all', since=dt):
            events = [
                x for x in i.get_events()
                if x.created_at.replace(tzinfo=timezone.utc) > dt
                and x.actor.login in assignees
                and x.event in clr_dict
            ]
            for e in events:
                if e.issue.number not in issue_dict:
                    issue_dict[e.issue.number] = TimeLine(issue=e.issue)
                issue_dict[e.issue.number].add_event(
                    TimeLinePoint(
                        event_type=e.event,
                        created_at=e.created_at,
                        actor=e.actor,
                        issue_number=e.issue.number
                    )
                )

        for c in [x for x in repo.get_issues_comments(sort='updated', since=dt) if x.user.login in assignees]:
            # just take numbers from url string ".../Dota2-Gameplay/issues/2524" with `.split`
            issue_num = int(c.issue_url.split('/')[-1])
            if issue_num not in issue_dict:
                issue = repo.get_issue(issue_num)
                issue_dict[issue.number] = TimeLine(issue=issue)
            issue_dict[issue_num].add_event(
                TimeLinePoint(
                    event_type='commented',
                    created_at=c.created_at,
                    actor=c.user,
                    body=c.body,
                    html_url=c.html_url,
                    issue_number=issue_num
                )
            )

        efs = [v.embed_and_file for v in issue_dict.values()]
        efs_10list = [efs[x: x + 10] for x in range(0, len(efs), 10)]
        for i in efs_10list:
            msg = await self.bot.get_channel(Cid.dota_news).send(embeds=[e for e, _ in i], files=[f for _, f in i])
            await msg.publish()
        
        query = 'UPDATE botinfo SET git_checked_dt=$1 WHERE id=$2'
        await self.bot.pool.execute(query, datetime.now(timezone.utc), Sid.alu)

    @git_comments_check.before_loop
    async def before(self):
        await self.bot.wait_until_ready()

    @git_comments_check.error
    async def git_comments_check_error(self, error):
        await self.bot.send_traceback(error, where='dotabugtracker comments task')
        # self.git_comments_check.restart()


async def setup(bot):
    await bot.add_cog(DotaBugtracker(bot))
