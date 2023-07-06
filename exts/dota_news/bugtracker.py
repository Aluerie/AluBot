from __future__ import annotations

import asyncio
import datetime
import logging
import re
import textwrap
from enum import Enum
from typing import TYPE_CHECKING, Optional

import discord
from discord.ext import commands, tasks
from github.GithubException import GithubException
from PIL import Image

from utils import AluCog, const

if TYPE_CHECKING:
    from github import Issue, NamedUser

    from utils import AluBot, AluContext

log = logging.getLogger(__name__)
log.setLevel(logging.INFO)


GITHUB_REPO = "ValveSoftware/Dota2-Gameplay"
GITHUB_REPO_URL = f"https://github.com/{GITHUB_REPO}"


class ActionBase:
    def __init__(self, name: str, *, colour: int, word: str, emote: str) -> None:
        self.name: str = name
        self.colour: int = colour
        self.word: str = word
        self.emote: str = emote

    @property
    def file_path(self) -> str:
        return f'./assets/images/git/{self.name}.png'

    def file(self, number: int) -> discord.File:
        # without a `number` we had a "bug" where the image would go outside embeds
        return discord.File(self.file_path, filename=f'{self.name}_{number}.png')


class EventBase(ActionBase):
    pass


class CommentBase(ActionBase):
    pass


# I kindly ask you to have same matching names for
# * variables below
# * PNG-picture in assets folder
# * emote name in wink server
class EventType(Enum):
    assigned = EventBase('assigned', colour=0x21262D, word='self-assigned', emote=str(const.GitIssueEvent.assigned))
    closed = EventBase('closed', colour=0x9B6CEA, word='closed', emote=str(const.GitIssueEvent.closed))
    reopened = EventBase('reopened', colour=0x238636, word='reopened', emote=str(const.GitIssueEvent.reopened))


class CommentType(Enum):
    commented = CommentBase('commented', colour=0x4285F4, word='commented', emote=str(const.GitIssueEvent.commented))
    opened = CommentBase('opened', colour=0x52CC99, word='opened', emote=str(const.GitIssueEvent.opened))


class Action:
    def __init__(
        self,
        *,
        enum_type: EventBase,
        created_at: datetime.datetime,
        actor: NamedUser.NamedUser,
        issue_number: int,
        **kwargs,
    ):
        self.event_type: EventBase = enum_type
        self.created_at: datetime.datetime = created_at.replace(tzinfo=datetime.timezone.utc)
        self.actor: NamedUser.NamedUser = actor
        self.issue_number: int = issue_number

    @property
    def author_str(self) -> str:
        return f'@{self.actor.login} {self.event_type.word} bugtracker issue #{self.issue_number}'


class Event(Action):
    pass


class Comment(Action):
    def __init__(self, *, comment_body: str, comment_url: Optional[str] = None, **kwargs):
        super().__init__(**kwargs)
        self.comment_body: str = comment_body
        self.comment_url: Optional[str] = comment_url

    @property
    def markdown_body(self) -> str:
        url_regex = re.compile(fr'({GITHUB_REPO_URL}/issues/(\d+))')
        body = url_regex.sub(r'[#\2](\1)', self.comment_body)
        body = '\n'.join([line for line in body.splitlines() if line])
        return body.replace('<br>', '')


class TimeLine:
    def __init__(self, issue: Issue.Issue):
        self.issue: Issue.Issue = issue

        self.actions: list[Action] = []
        self.authors: set[NamedUser.NamedUser] = set()

    def add_action(self, action: Action):
        self.actions.append(action)
        self.authors.add(action.actor)

    def sorted_points_list(self) -> list[Action]:
        return sorted(self.actions, key=lambda x: x.created_at, reverse=False)

    @property
    def events(self) -> list[Event]:
        return [e for e in self.actions if isinstance(e, Event)]

    @property
    def comments(self) -> list[Comment]:
        return [e for e in self.actions if isinstance(e, Comment)]

    @property
    def last_comment_url(self) -> Optional[str]:
        sorted_comments = sorted(self.comments, key=lambda x: x.created_at, reverse=False)
        try:
            last_comment_url = sorted_comments[-1].comment_url
        except IndexError:
            last_comment_url = None
        return last_comment_url

    def embed_and_file(self, bot: AluBot) -> tuple[discord.Embed, discord.File]:
        title = textwrap.shorten(self.issue.title, width=const.Limit.Embed.title)
        e = discord.Embed(title=title, url=self.issue.html_url)
        if len(self.events) < 2 and len(self.comments) < 2 and len(self.authors) < 2:
            # we just send a small embed
            # 1 author and 1 event with possible comment to it
            event = next(iter(self.events), None)  # first element in self.events or None if not exist
            comment = next(iter(self.comments), None)  # first element in self.comments or None if not exist

            lead_action = event or comment
            if lead_action is None:
                raise RuntimeError('Somehow lead_event is None')

            e.colour = lead_action.event_type.colour
            url = comment.comment_url if comment else None
            e.set_author(name=lead_action.author_str, icon_url=lead_action.actor.avatar_url, url=url)
            e.description = comment.markdown_body if comment else ''
            file = lead_action.event_type.file(self.issue.number)
            e.set_thumbnail(url=f'attachment://{file.filename}')
        else:
            e.colour = 0x4078C0  # git colour, first in google :D
            pil_pics = []
            for p in self.sorted_points_list():
                pil_pics.append(p.event_type.file_path)
                markdown_body = getattr(p, 'markdown_body', ' ')
                chunks, chunk_size = len(markdown_body), const.Limit.Embed.field_value
                fields = [markdown_body[i : i + chunk_size] for i in range(0, chunks, chunk_size)]
                for x in fields:
                    e.add_field(name=f'{p.event_type.emote}{p.author_str}', value=x, inline=False)
            e.set_author(
                name=f'Bugtracker issue #{self.issue.number} update',
                url=self.last_comment_url,
                icon_url='https://em-content.zobj.net/thumbs/120/microsoft/319/frog_1f438.png',
            )
            delta_x_y = 32
            size_x_y = 128 + (len(pil_pics) - 1) * delta_x_y  # 128 is images size
            dst = Image.new('RGBA', (size_x_y, size_x_y), (0, 0, 0, 0))
            for i, pic_name in enumerate(pil_pics):
                im = Image.open(pic_name)
                dst.paste(im, (i * delta_x_y, i * delta_x_y), im)

            file = bot.imgtools.img_to_file(dst, filename=f'bugtracker_update_{self.issue.number}.png')
            e.set_thumbnail(url=f'attachment://{file.filename}')
        return e, file


class BugTracker(AluCog):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.retries: int = 0  # todo: find better solution

    async def cog_load(self) -> None:
        self.bot.ini_github()
        self.dota2gameplay_repo = self.bot.github.get_repo(GITHUB_REPO)
        self.valve_devs = await self.get_valve_devs()
        self.git_comments_check.start()

    async def cog_unload(self) -> None:
        self.git_comments_check.stop()  # .cancel()

    @discord.utils.cached_property
    def news_channel(self):
        channel = self.hideout.spam if self.bot.test else self.community.bugtracker_news
        return channel

    async def get_valve_devs(self) -> list[str]:
        query = 'SELECT login FROM valve_devs'
        valve_devs: list[str] = [i for i, in await self.bot.pool.fetch(query)]
        return valve_devs

    @commands.is_owner()
    @commands.group(name="valve", hidden=True)
    async def valve(self, ctx: AluContext):
        """Group for valve devs commands. Use it together with subcommands"""
        await ctx.scnf()

    @commands.is_owner()
    @valve.command()
    async def add(self, ctx: AluContext, *, login: str):
        logins = [b for x in login.split(",") if (b := x.lstrip().rstrip())]
        query = """ INSERT INTO valve_devs (login) VALUES ($1)
                    ON CONFLICT DO NOTHING
                    RETURNING True;
                """

        error_logins = []
        success_logins = []
        for l in logins:
            # looks like executemany wont work bcs it executes strings letter by letter!
            val = await self.bot.pool.fetchval(query, l)
            if val:
                success_logins.append(l)
            else:
                error_logins.append(l)
        if success_logins:
            self.valve_devs.extend(success_logins)
            e = discord.Embed(color=const.MaterialPalette.green())
            answer = ', '.join(f'`{l}`' for l in logins)
            e.description = f'Added user(-s) to the list of Valve devs.\n{answer}'
            await ctx.reply(embed=e)
        if error_logins:
            e = discord.Embed(color=const.MaterialPalette.red())
            answer = ', '.join(f'`{l}`' for l in logins)
            e.description = f'User(-s) were already in the list of Valve devs.\n{answer}'
            await ctx.reply(embed=e)

    @commands.is_owner()
    @valve.command()
    async def remove(self, ctx: AluContext, login: str):
        query = "DELETE FROM valve_devs WHERE login=$1"
        await self.bot.pool.execute(query, login)
        self.valve_devs.remove(login)
        e = discord.Embed(color=const.MaterialPalette.orange())
        e.description = f'Removed user `{login}` from the list of Valve devs.'
        await ctx.reply(embed=e)

    @commands.is_owner()
    @valve.command()
    async def list(self, ctx: AluContext):
        query = "SELECT login FROM valve_devs"
        valve_devs: list[str] = [i for i, in await self.bot.pool.fetch(query)]
        e = discord.Embed(color=const.MaterialPalette.blue(), title='List of known Valve devs')
        valve_devs.sort()
        e.description = '\n'.join([f'\N{BLACK CIRCLE} {i}' for i in valve_devs])
        await ctx.reply(embed=e)

    @tasks.loop(minutes=3)
    async def git_comments_check(self):
        log.debug('BugTracker task started')
        repo = self.dota2gameplay_repo

        query = 'SELECT git_checked_dt FROM botinfo WHERE id=$1'
        dt: datetime.datetime = await self.bot.pool.fetchval(query, const.Guild.community)
        now = discord.utils.utcnow()

        # if self.bot.test:  # TESTING
        #     dt = datetime.datetime.now(datetime.timezone.utc) - datetime.timedelta(hours=2)

        issue_dict: dict[int, TimeLine] = dict()
        issues_list = repo.get_issues(sort='updated', state='all', since=dt)

        for i in issues_list:
            # Closed / Self-assigned / Reopened
            events = [
                x
                for x in i.get_events()
                if now > x.created_at.replace(tzinfo=datetime.timezone.utc) > dt
                and x.actor  # apparently some people just delete their accounts after closing their issues, #6556 :D
                and x.event in [x.name for x in list(EventType)]
            ]
            for e in events:
                if (login := e.actor.login) in self.valve_devs:
                    pass
                elif login != e.issue.user.login:
                    # if actor is not OP of the issue then we can consider
                    # that this person is a valve dev
                    self.valve_devs.append(login)
                    query = """ INSERT INTO valve_devs (login) VALUES ($1)
                                ON CONFLICT DO NOTHING;
                            """
                    await self.bot.pool.execute(query, login)
                else:
                    continue

                issue_dict.setdefault(e.issue.number, TimeLine(issue=e.issue)).add_action(
                    Event(
                        enum_type=(getattr(EventType, e.event)).value,
                        created_at=e.created_at,
                        actor=e.actor,
                        issue_number=e.issue.number,
                    )
                )

        # Issues opened by Valve devs
        for i in issues_list:
            if not dt < i.created_at.replace(tzinfo=datetime.timezone.utc) < now:
                continue
            if i.user.login in self.valve_devs:
                issue_dict.setdefault(i.number, TimeLine(issue=i)).add_action(
                    Comment(
                        enum_type=CommentType.opened.value,
                        created_at=i.created_at,
                        actor=i.user,
                        issue_number=i.number,
                        comment_body=i.body,
                    )
                )

        # Comments left by Valve devs
        for c in [x for x in repo.get_issues_comments(sort='updated', since=dt) if x.user.login in self.valve_devs]:
            # just take numbers from url string ".../Dota2-Gameplay/issues/2524" with `.split`
            issue_num = int(c.issue_url.split('/')[-1])

            issue_dict.setdefault(issue_num, TimeLine(issue=repo.get_issue(issue_num))).add_action(
                Comment(
                    enum_type=CommentType.commented.value,
                    created_at=c.created_at,
                    actor=c.user,
                    issue_number=issue_num,
                    comment_body=c.body,
                    comment_url=c.html_url,
                )
            )

        efs = [v.embed_and_file(self.bot) for v in issue_dict.values()]

        batches_to_send: list[list[tuple[discord.Embed, discord.File]]] = []
        character_counter, embed_counter = 0, 0
        for em, file in efs:
            character_counter += len(em)
            embed_counter += 1
            if character_counter < const.Limit.Embed.sum_all and embed_counter < 10 + 1:
                try:
                    batches_to_send[-1].append((em, file))
                except IndexError:
                    batches_to_send.append([(em, file)])
            else:
                character_counter, embed_counter = len(em), 1
                batches_to_send.append([(em, file)])

        for batch in batches_to_send:
            msg = await self.news_channel.send(
                embeds=[embed for (embed, _file) in batch],
                files=[file for (_embed, file) in batch],
            )
            await msg.publish()

        query = 'UPDATE botinfo SET git_checked_dt=$1 WHERE id=$2'
        await self.bot.pool.execute(query, now, const.Guild.community)
        self.retries = 0
        log.debug('BugTracker task is finished')

    @git_comments_check.before_loop
    async def before(self):
        await self.bot.wait_until_ready()

    @git_comments_check.error
    async def git_comments_check_error(self, error):
        if isinstance(error, GithubException):
            if error.status == 502:
                if self.retries == 0:
                    e = discord.Embed(description='DotaBugtracker: Server Error 502')
                    await self.hideout.spam.send(embed=e)
                await asyncio.sleep(60 * 10 * 2**self.retries)
                self.retries += 1
                self.git_comments_check.restart()
                return

        txt = 'Dota2 BugTracker task'
        await self.bot.exc_manager.register_error(error, txt, where=txt)
        # self.git_comments_check.restart()


async def setup(bot: AluBot):
    await bot.add_cog(BugTracker(bot))
