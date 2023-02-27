from __future__ import annotations
from typing import TYPE_CHECKING, List, Set, Optional, Tuple

import asyncio
import re
import datetime
import textwrap

import discord
from discord.ext import commands, tasks
from github.GithubException import GithubException
from PIL import Image

from .utils.var import Sid, Cid, Lmt

if TYPE_CHECKING:
    from github import Issue, NamedUser
    from .utils.bot import AluBot


class BaseEvent:
    def __init__(
            self,
            name: str,
            *,
            colour: int,
            word: str,
            text_flag: Optional[bool] = False
    ) -> None:
        self.name: str = name
        self.colour: int = colour
        self.word: str = word
        self.text_flag: Optional[bool] = text_flag

    @property
    def file_path(self) -> str:
        return f'./assets/images/git/{self.name}.png'

    @property
    def file(self) -> discord.File:
        return discord.File(self.file_path)

    def emote(self, bot: AluBot) -> discord.Emoji | None:
        return discord.utils.find(lambda m: m.name == self.name, bot.test_guild.emojis)


class EventType:
    # pictures are taken from 16px versions here https://primer.style/octicons/
    # and background circles are added with simple online editor https://iconscout.com/color-editor
    # make pics to be 128x128, so it's consistent for all sizes
    # I kindly ask you to have same matching names for
    # * variable below
    # * PNG-picture in assets folder
    # * emote name in wink server
    assigned = BaseEvent('assigned', colour=0x21262D, word='self-assigned')
    closed = BaseEvent('closed', colour=0x9B6CEA, word='closed')
    reopened = BaseEvent('reopened', colour=0x238636, word='reopened')
    commented = BaseEvent('commented', colour=0x4285F4, word='commented', text_flag=True)
    opened = BaseEvent('opened', colour=0x52CC99, word='opened', text_flag=True)

    # these should match one of event names from GitHub documentation 
    issue_events = ['assigned', 'closed', 'reopened']


class TimeLinePoint:

    def __init__(
            self,
            *,
            event_type: BaseEvent,
            created_at: datetime.datetime,
            actor: NamedUser.NamedUser,
            issue_number: int,
            body: str = '',
            comment_url: Optional[str] = None
    ):
        self.event_type: BaseEvent = event_type
        self.created_at: datetime.datetime = created_at.replace(tzinfo=datetime.timezone.utc)
        self.actor: NamedUser.NamedUser = actor
        self.issue_number: int = issue_number
        self.body: str = body
        self.comment_url: Optional[str] = comment_url

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
            issue: Issue.Issue,
    ):
        self.issue: Issue.Issue = issue

        self.events: List[TimeLinePoint] = []
        self.comments: List[TimeLinePoint] = []
        self.authors: Set[NamedUser.NamedUser] = set()

    def add_event(self, event: TimeLinePoint):
        if event.event_type.text_flag:
            self.comments.append(event)
        else:
            self.events.append(event)
        self.authors.add(event.actor)

    def sorted_points_list(self):
        return sorted(self.events + self.comments, key=lambda x: x.created_at, reverse=False)

    def embed_and_file(self, bot: AluBot) -> Tuple[discord.Embed, discord.File | None]:
        e = discord.Embed(title=textwrap.shorten(self.issue.title, width=Lmt.Embed.title), url=self.issue.html_url)
        if len(self.events) < 2 and len(self.comments) < 2 and len(self.authors) < 2:
            # we just send a small embed
            # 1 author and 1 event with possible comment event to it
            ev = next(iter(self.events), None)  # first element in self.events or None if not exist
            co = next(iter(self.comments), None)  # first element in self.comments or None if not exist

            le = ev or co  # lead_event
            if le is None:
                raise RuntimeError('Somehow lead_event is None')

            e.colour = le.event_type.colour
            e.set_author(
                name=le.author_str,
                icon_url=le.actor.avatar_url,
                url=co.comment_url if co else None
            )
            e.description = co.markdown_body if co else ''
            file = le.event_type.file
            e.set_thumbnail(url=f'attachment://{file.filename}')
        else:
            e.colour = 0x4078c0  # git colour, first in google :D
            pil_pics = []
            for p in (sorted_points := self.sorted_points_list()):
                pil_pics.append(p.event_type.file_path)
                if not p.body:
                    p.body = ' '  # so event-actions get printed in the following chunking
                chunks, chunk_size = len(p.markdown_body), Lmt.Embed.field_value
                fields = [p.markdown_body[i:i+chunk_size] for i in range(0, chunks, chunk_size)]
                for x in fields:
                    e.add_field(name=f'{p.event_type.emote(bot)}{p.author_str}', value=x, inline=False)
            e.set_author(
                name=f'Bugtracker issue #{self.issue.number} update',
                url=sorted_points[-1].comment_url,
                icon_url='https://em-content.zobj.net/thumbs/120/microsoft/319/frog_1f438.png'
            )
            delta_x_y = 32
            size_x_y = 128 + (len(pil_pics) - 1) * delta_x_y  # 128 is images size
            dst = Image.new('RGBA', (size_x_y, size_x_y), (0, 0, 0, 0))
            for i, pic_name in enumerate(pil_pics):
                im = Image.open(pic_name)
                dst.paste(im, (i*delta_x_y, i*delta_x_y), im)

            file = bot.img_to_file(dst, filename=f'bugtracker_update_{self.issue.number}.png')
            e.set_thumbnail(url=f'attachment://{file.filename}')
        return e, file


class DotaBugtracker(commands.Cog):
    def __init__(self, bot: AluBot):
        self.bot: AluBot = bot
        self.retries: int = 0

    async def cog_load(self) -> None:
        self.bot.ini_github()
        self.git_comments_check.start()

    async def cog_unload(self) -> None:
        self.git_comments_check.stop()  # .cancel()

    @tasks.loop(minutes=3)
    async def git_comments_check(self):
        repo = self.bot.git_gameplay

        assignees = [x.login for x in repo.get_assignees()]

        query = 'SELECT git_checked_dt FROM botinfo WHERE id=$1'
        dt: datetime.datetime = await self.bot.pool.fetchval(query, Sid.alu)

        # if self.bot.test:  # TESTING
        #     dt = datetime.datetime.now(datetime.timezone.utc) - datetime.timedelta(hours=29)

        issue_dict = dict()

        # Closed / Self-assigned / Reopened
        for i in repo.get_issues(sort='updated', state='all', since=dt):
            events = [
                x for x in i.get_events()
                if x.created_at.replace(tzinfo=datetime.timezone.utc) > dt
                and x.actor  # apparently some people just delete their accounts after closing their issues, #6556 :D
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

        # Issues opened by Valve devs
        for i in repo.get_issues(sort='created', state='open', since=dt):
            if i.created_at.replace(tzinfo=datetime.timezone.utc) < dt:
                continue
            if i.user.login in assignees:
                if i.number not in issue_dict:
                    issue_dict[i.number] = TimeLine(issue=i)
                issue_dict[i.number].add_event(
                    TimeLinePoint(
                        event_type=EventType.opened,
                        created_at=i.created_at,
                        actor=i.user,
                        body=i.body,
                        issue_number=i.number
                    )
                )

        # Comments left by Valve devs
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
                    comment_url=c.html_url,
                    issue_number=issue_num
                )
            )

        efs = [v.embed_and_file(self.bot) for v in issue_dict.values()]

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
        await self.bot.pool.execute(query, discord.utils.utcnow(), Sid.alu)
        self.retries = 0

    @git_comments_check.before_loop
    async def before(self):
        await self.bot.wait_until_ready()

    @git_comments_check.error
    async def git_comments_check_error(self, error):
        if isinstance(error, GithubException):
            if error.status == 502:
                if self.retries == 0:
                    e = discord.Embed(description='DotaBugtracker: Server Error 502')
                    await self.bot.spam_channel.send(embed=e)
                await asyncio.sleep(60 * 10 * 2**self.retries)
                self.retries += 1
                self.git_comments_check.restart()
                return

        await self.bot.send_traceback(error, where='Dota2 BugTracker comments task')
        # self.git_comments_check.restart()


async def setup(bot: AluBot):
    await bot.add_cog(DotaBugtracker(bot))
