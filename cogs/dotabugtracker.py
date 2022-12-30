from __future__ import annotations

import asyncio
import re
from datetime import datetime, timezone
from typing import TYPE_CHECKING, List, Set, Optional

import github.GithubException
from discord import Embed, File
from discord.ext import commands, tasks

from .utils.var import Sid, Cid, Clr, Lmt

if TYPE_CHECKING:
    from .utils.bot import AluBot
    from github import Issue, NamedUser


class BaseEvent:
    def __init__(
            self,
            name: str,
            *,
            colour: int,
            picture: str,
            word: str,
            text_flag: Optional[bool] = False
    ) -> None:
        self.name: str = name
        self.colour: int = colour
        self._picture = picture
        self.word: str = word
        self.text_flag: bool = text_flag

    @property
    def file(self) -> File:
        return File(f'./media/{self._picture}', filename=self._picture)


class EventType:
    assigned = BaseEvent('assigned', colour=0x21262D, picture='assigned.png', word='self-assigned')
    closed = BaseEvent('closed', colour=0x9B6CEA, picture='closed.png', word='closed')
    reopened = BaseEvent('reopened', colour=0x238636, picture='reopened.png', word='reopened')
    commented = BaseEvent('commented', colour=0x4078c0, picture='assigned.png', word='commented', text_flag=True)
    opened = BaseEvent('opened', colour=0x789001, picture='assigned.png', word='opened', text_flag=True)

    issue_events = ['assigned', 'closed', 'reopened']


class TimeLinePoint:

    def __init__(
            self,
            *,
            event_type: BaseEvent,
            created_at: datetime,
            actor: NamedUser,
            issue_number: int,
            body: str = '',
            html_url: str = ''
    ):
        self.event_type: BaseEvent = event_type
        self.created_at: datetime = created_at.replace(tzinfo=timezone.utc)
        self.actor: NamedUser = actor
        self.issue_number: int = issue_number
        self.body: str = body
        self.html_url: str = html_url

    @property
    def author_str(self) -> str:
        return f'@{self.actor.login} {self.event_type.word} bugtracker issue #{self.issue_number}'

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
        if event.event_type.text_flag:
            self.comments.append(event)
        else:
            self.events.append(event)
        self.authors.add(event.actor)

    def sorted_points_list(self):
        return sorted(self.events + self.comments, key=lambda x: x.created_at, reverse=False)

    @property
    def embed_and_file(self) -> (Embed, File):
        em = Embed(title=self.issue.title[:Lmt.Embed.title], url=self.issue.html_url)
        if len(self.events) < 2 and len(self.comments) < 2 and len(self.authors) < 2:
            # we just send a small embed
            # 1 author and 1 event with possible comment event to it
            e = next(iter(self.events), None)  # first element in self.events or None if not exist
            c = next(iter(self.comments), None)  # first element in self.comments or None if not exist

            l = e or c  # lead_event
            if l is None:
                raise RuntimeError('Somehow lead_event is None')

            em.colour = l.event_type.colour
            em.set_author(name=l.author_str, icon_url=l.actor.avatar_url, url=l.html_url)
            em.description = c.markdown_body if c else ''
            file = l.event_type.file
            em.set_thumbnail(url=f'attachment://{file.filename}')
        else:
            em.colour = Clr.prpl
            for p in (sorted_points := self.sorted_points_list()):
                chunks, chunk_size = len(p.markdown_body), Lmt.Embed.field_value
                fields = [p.markdown_body[i:i+chunk_size] for i in range(0, chunks, chunk_size)]
                for x in fields:
                    em.add_field(name=p.author_str, value=x, inline=False)
            em.set_author(name=f'bugtracker issue #{self.issue.number} update', url=sorted_points[-1].html_url)
            file = None
        return em, file


class DotaBugtracker(commands.Cog):
    def __init__(self, bot: AluBot):
        self.bot: AluBot = bot
        self.retries = 0

    async def cog_load(self) -> None:
        self.bot.ini_github()
        self.git_comments_check.start()

    async def cog_unload(self) -> None:
        self.git_comments_check.stop()  # .cancel()

    @tasks.loop(minutes=10)
    async def git_comments_check(self):
        repo = self.bot.git_gameplay

        assignees = [x.login for x in repo.get_assignees()]

        query = 'SELECT git_checked_dt FROM botinfo WHERE id=$1'
        dt: datetime = await self.bot.pool.fetchval(query, Sid.alu)

        # from datetime import timedelta  # <- for testing
        # dt = datetime.now(timezone.utc) - timedelta(hours=9)  # <- for testing

        issue_dict = dict()

        for i in repo.get_issues(sort='updated', state='all', since=dt):
            events = [
                x for x in i.get_events()
                if x.created_at.replace(tzinfo=timezone.utc) > dt
                and x.actor.login in assignees
                and x.event in EventType.issue_events
            ]
            for e in events:
                if e.issue.number not in issue_dict:
                    issue_dict[e.issue.number] = TimeLine(issue=e.issue)
                issue_dict[e.issue.number].add_event(
                    TimeLinePoint(
                        event_type=getattr(EventType, e.event),
                        created_at=e.created_at,
                        actor=e.actor,
                        issue_number=e.issue.number
                    )
                )

        # now about opened by Valve assignees issues
        for i in repo.get_issues(sort='created', state='open', since=dt):
            if i.user.login in assignees:
                if i.number not in issue_dict:
                    issue_dict[i.number] = TimeLine(issue=i)
                issue_dict[i.number].add_event(
                    TimeLinePoint(
                        event_type=EventType.opened,
                        created_at=i.created_at,
                        actor=i.user,
                        body=i.body,
                        html_url=i.html_url,
                        issue_number=i.number
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
                    event_type=EventType.commented,
                    created_at=c.created_at,
                    actor=c.user,
                    body=c.body,
                    html_url=c.html_url,
                    issue_number=issue_num
                )
            )

        efs = [v.embed_and_file for v in issue_dict.values()]

        batches_to_send, character_counter, embed_counter = [], 0, 0
        for em, file in efs:
            character_counter += len(em)
            embed_counter += 1
            if character_counter < Lmt.Embed.sum_all and embed_counter < 10 + 1:
                try:
                    batches_to_send[-1].append((em, file))
                except IndexError:
                    batches_to_send.append([(em, file)])
            else:
                character_counter, embed_counter = len(em), 1
                batches_to_send.append([(em, file)])

        for i in batches_to_send:
            msg = await self.bot.get_channel(Cid.dota_news).send(
                embeds=[e for e, _ in i], files=[f for _, f in i if f]
            )
            if msg.channel.id == Cid.dota_news:
                await msg.publish()
        
        query = 'UPDATE botinfo SET git_checked_dt=$1 WHERE id=$2'
        await self.bot.pool.execute(query, datetime.now(timezone.utc), Sid.alu)
        self.retries = 0

    @git_comments_check.before_loop
    async def before(self):
        await self.bot.wait_until_ready()

    @git_comments_check.error
    async def git_comments_check_error(self, error):
        if isinstance(error, github.GithubException):
            if error.status == 502:
                if self.retries == 0:
                    em = Embed(description='DotaBugtracker: Server Error 502')
                    await self.bot.get_channel(Cid.spam_me).send(embed=em)
                await asyncio.sleep(60 * 10 * 2**self.retries)
                self.retries += 1
                self.git_comments_check.restart()
                return

        await self.bot.send_traceback(error, where='dotabugtracker comments task')
        # self.git_comments_check.restart()


async def setup(bot: AluBot):
    await bot.add_cog(DotaBugtracker(bot))
