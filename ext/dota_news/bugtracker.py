from __future__ import annotations

import datetime
import itertools
import logging
import re
import textwrap
from enum import Enum
from operator import attrgetter
from typing import TYPE_CHECKING, Optional

import discord
from discord.ext import commands
from githubkit.exception import RequestError, RequestFailed
from PIL import Image

from utils import AluCog, aluloop, const

if TYPE_CHECKING:
    from githubkit.rest import Issue, SimpleUser

    from bot import AluBot
    from utils import AluContext

log = logging.getLogger(__name__)
log.setLevel(logging.INFO)

# this might backfire but why the hell githubkit put GET REST logs from httpx as log.INFO, jesus christ.
logging.getLogger("httpx").setLevel(logging.WARNING)

GITHUB_REPO = "ValveSoftware/Dota2-Gameplay"
GITHUB_REPO_URL = f"https://github.com/{GITHUB_REPO}"


class ActionBase:
    """_summary_

    Attributes
    ----------
    name : str
        Event's name. Matches github terminology from API.
    colour : int
        Colour to assign for embed when sending the bugtracker news message.
    word : str
        Verb to put into author string in the said embed.
    emote : str
        Emote to use in a special type of embed where there is many different events per one issue.
        Emote differentiates "actions" from each other.
    """

    def __init__(self, name: str, *, colour: int, word: str, emote: str) -> None:
        self.name: str = name
        self.colour: int = colour
        self.word: str = word
        self.emote: str = emote

    @property
    def file_path(self) -> str:
        """Get path to the image file to put into thumbnail for the embed."""
        return f"./assets/images/git/{self.name}.png"

    def file(self, number: int) -> discord.File:
        """Get discord.File linked to the action image."""
        # without a `number` we had a "bug" where the image would go outside embeds
        return discord.File(self.file_path, filename=f"{self.name}_{number}.png")


class EventBase(ActionBase):
    """Base class for github issue event

    In a context of this file git issue "event" means stuff that doesn't have to have text with it, i.e.
    closed, assigned, reopened.
    """

    pass


class CommentBase(ActionBase):
    """Base class for github issue comment

    In a context of this file git issue "comment" means stuff that has to have text with it, i.e.
    commented, opened.

    An often case for github developers is to leave a comment and do one of the events.
    We will build a Timeline for each issue and then:
        * if mentioned above case happens - we will try to combine
        comments and event into one embed assuming they are related.
        * if there is many more events - we will list them with emotes
        * if there is only one - then easy life.
    """

    pass


# I kindly ask you to have same matching names for
# * variables below
# * PNG-picture in assets folder
# * emote name in wink server
class EventType(Enum):
    """Kinda data-mapping for git issue events."""

    assigned = EventBase("assigned", colour=0x21262D, word="self-assigned", emote=str(const.GitIssueEvent.assigned))
    closed = EventBase("closed", colour=0x9B6CEA, word="closed", emote=str(const.GitIssueEvent.closed))
    reopened = EventBase("reopened", colour=0x238636, word="reopened", emote=str(const.GitIssueEvent.reopened))


class CommentType(Enum):
    """Kinda data-mapping for git issue comments."""

    commented = CommentBase("commented", colour=0x4285F4, word="commented", emote=str(const.GitIssueEvent.commented))
    opened = CommentBase("opened", colour=0x52CC99, word="opened", emote=str(const.GitIssueEvent.opened))


class Action:
    """Action. These are ordered properly in the Git Issue's Timeline.

    Attributes
    ----------
    enum_type : EventBase | CommentBase
        Action type to gather common data, like picture file path from it.
    created_at : datetime.datetime
        Datetime for when the action was taken place.
    actor : SimpleUser
        Github issue whom created the event/comment.
    issue_number : int
        GitHub issue number.
    """

    def __init__(
        self,
        *,
        enum_type: EventBase | CommentBase,
        created_at: datetime.datetime,
        actor: SimpleUser,
        issue_number: int,
        **kwargs,
    ):
        self.event_type: EventBase | CommentBase = enum_type
        self.created_at: datetime.datetime = created_at.replace(tzinfo=datetime.timezone.utc)
        self.actor: SimpleUser = actor
        self.issue_number: int = issue_number

    @property
    def author_str(self) -> str:
        """Author string to put into the embed."""
        return f"@{self.actor.login} {self.event_type.word} bugtracker issue #{self.issue_number}"


class Event(Action):
    """Github Issue Timeline's Event"""

    # this needs to be separate classes bcs `isinstance` check
    pass


class Comment(Action):
    """Github Issue Timeline's Comment"""

    def __init__(self, *, comment_body: str, comment_url: Optional[str] = None, **kwargs):
        super().__init__(**kwargs)
        self.comment_body: str = comment_body
        self.comment_url: Optional[str] = comment_url

    @property
    def markdown_body(self) -> str:
        url_regex = re.compile(rf"({GITHUB_REPO_URL}/issues/(\d+))")
        body = url_regex.sub(r"[#\2](\1)", self.comment_body)
        body = "\n".join([line for line in body.splitlines() if line])
        return body.replace("<br>", "")


class TimeLine:
    """Timeline representing collection of ordered Events and Comments.

    Used to sort/order/combine said events/comments and create an embed out of it.

    Attributes
    ----------
    issue : Issue
        GItHub Issue to sort events/comments for the embed.
    actions : list[Action]
        List of those events/comments to sort later.
    actor_ids : set[int]
        ids of github actors who created those events/comments.
    """

    def __init__(self, issue: Issue):
        self.issue: Issue = issue

        self.actions: list[Action] = []
        self.actor_ids: set[int] = set()

    def add_action(self, action: Action):
        """Add action to the Timeline."""
        self.actions.append(action)
        self.actor_ids.add(action.actor.id)

    def sorted_points_list(self) -> list[Action]:
        """Sort actions by created time."""
        return sorted(self.actions, key=attrgetter("created_at"), reverse=False)

    @property
    def events(self) -> list[Event]:
        """List of event actions."""
        return [e for e in self.actions if isinstance(e, Event)]

    @property
    def comments(self) -> list[Comment]:
        """List of comment actions."""
        return [e for e in self.actions if isinstance(e, Comment)]

    @property
    def last_comment_url(self) -> Optional[str]:
        """Get url for the last comment."""
        sorted_comments = sorted(self.comments, key=lambda x: x.created_at, reverse=False)
        try:
            last_comment_url = sorted_comments[-1].comment_url
        except IndexError:
            last_comment_url = None
        return last_comment_url

    def embed_and_file(self, bot: AluBot) -> tuple[discord.Embed, discord.File]:
        """Get embed and file to send in the discord."""
        title = textwrap.shorten(self.issue.title, width=const.Limit.Embed.title)
        embed = discord.Embed(title=title, url=self.issue.html_url)
        if len(self.events) < 2 and len(self.comments) < 2 and len(self.actor_ids) < 2:
            # we just send a small embed
            # 1 author and 1 event with possible comment to it
            event = next(iter(self.events), None)  # first element in self.events or None if not exist
            comment = next(iter(self.comments), None)  # first element in self.comments or None if not exist

            lead_action = event or comment
            if lead_action is None:
                raise RuntimeError("Somehow lead_event is None")

            embed.colour = lead_action.event_type.colour
            url = comment.comment_url if comment else None
            embed.set_author(name=lead_action.author_str, icon_url=lead_action.actor.avatar_url, url=url)
            if comment:
                embed.description = comment.markdown_body
            file = lead_action.event_type.file(self.issue.number)
            embed.set_thumbnail(url=f"attachment://{file.filename}")
        else:
            embed.colour = 0x4078C0  # git colour, first in google :D
            pil_pics: list[str] = []
            for p in self.sorted_points_list():
                pil_pics.append(p.event_type.file_path)
                markdown_body = getattr(p, "markdown_body", " ")
                chunks, chunk_size = len(markdown_body), const.Limit.Embed.field_value
                fields = [markdown_body[i : i + chunk_size] for i in range(0, chunks, chunk_size)]
                for x in fields:
                    embed.add_field(name=f"{p.event_type.emote}{p.author_str}", value=x, inline=False)
            embed.set_author(
                name=f"Bugtracker issue #{self.issue.number} update",
                url=self.last_comment_url,
                icon_url=const.Picture.Frog,
            )
            delta_x_y = 32
            size_x_y = 128 + (len(pil_pics) - 1) * delta_x_y  # 128 is images size
            dst = Image.new("RGBA", (size_x_y, size_x_y), (0, 0, 0, 0))
            for i, pic_name in enumerate(pil_pics):
                im = Image.open(pic_name)
                dst.paste(im, (i * delta_x_y, i * delta_x_y), im)

            file = bot.transposer.image_to_file(dst, filename=f"bugtracker_update_{self.issue.number}.png")
            embed.set_thumbnail(url=f"attachment://{file.filename}")
        return (embed, file)


class BugTracker(AluCog):
    """BugTracker News

    Track Valve developers activity in the Dota2-Gameplay repository
    and send a notification to #bugtracker-news in my discord server.

    Useful to know what the devs are up to and to quickly test, respond to their actions.

    A bit of privacy-abuse to track people's activity like that, but the repository is public and
    the information is valuable and interesting,
    and helpful to valve devs themselves since I can help asap when they ask for it.

    So hopefully, it's not much of a problem. If there is - please, contact me.

    Attributes
    ----------
    valve_devs : list[str]
        The list of known Valve developers who ever interacted with the Bug Tracker.
    bugtracker_news_worker : utils.bases.tasks.Loop
        The main task of the cog that tracks, analyzes GitHub events and sends news messages.
    """

    async def cog_load(self) -> None:
        self.bot.initialize_github()
        self.valve_devs: list[str] = await self.get_valve_devs()

        self.bugtracker_news_worker.add_exception_type(RequestError, RequestFailed)
        self.bugtracker_news_worker.start()

    async def cog_unload(self) -> None:
        self.bugtracker_news_worker.stop()  # .cancel()

    @discord.utils.cached_property
    def news_channel(self) -> discord.TextChannel:
        """Dota 2 Bug tracker news channel."""
        channel = self.hideout.spam if self.bot.test else self.community.bugtracker_news
        return channel

    async def get_valve_devs(self) -> list[str]:
        """Get the list of known Valve developers."""
        query = "SELECT login FROM valve_devs"
        valve_devs: list[str] = [i for (i,) in await self.bot.pool.fetch(query)]
        return valve_devs

    @commands.is_owner()
    @commands.group(name="bugtracker", aliases=["valve"], hidden=True)
    async def bugtracker(self, ctx: AluContext):
        """Commands to retrieve or manually control the list of known Valve developers' github accounts."""
        await ctx.send_help(ctx.command)

    @bugtracker.command(name="add")
    async def bugtracker_add(self, ctx: AluContext, *, login: str):
        """Manually add a user login to the list of known Valve developers."""
        logins = [b for x in login.split(",") if (b := x.lstrip().rstrip())]
        query = """
            INSERT INTO valve_devs (login) VALUES ($1)
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

        def embed_answer(logins: list[str], color: discord.Color, description: str) -> discord.Embed:
            logins_join = ", ".join(f"`{l}`" for l in logins)
            return discord.Embed(color=color, description=f"{description}\n{logins_join}")

        embeds: list[discord.Embed] = []
        if success_logins:
            self.valve_devs.extend(success_logins)
            embeds.append(
                embed_answer(success_logins, const.MaterialPalette.green(), "Added user(-s) to the list of Valve devs.")
            )
        if error_logins:
            embeds.append(
                embed_answer(
                    error_logins, const.MaterialPalette.red(), "User(-s) were already in the list of Valve devs."
                )
            )
        await ctx.reply(embeds=embeds)

    @bugtracker.command(name="remove")
    async def bugtracker_remove(self, ctx: AluContext, login: str):
        """Manually remove a user login from the list of known Valve developers."""
        query = "DELETE FROM valve_devs WHERE login=$1"
        await self.bot.pool.execute(query, login)
        self.valve_devs.remove(login)
        embed = discord.Embed(
            color=const.MaterialPalette.orange(),
            description=f"Removed user `{login}` from the list of Valve devs.",
        )
        await ctx.reply(embed=embed)

    @bugtracker.command(name="list", aliases=["devs"])
    async def bugtracker_list(self, ctx: AluContext):
        """Show the list of known Valve developers."""
        query = "SELECT login FROM valve_devs"
        valve_devs: list[str] = [i for (i,) in await self.bot.pool.fetch(query)]
        valve_devs.sort()
        embed = discord.Embed(
            color=const.MaterialPalette.blue(),
            title="List of known Valve devs",
            description="\n".join([f"\N{BLACK CIRCLE} {i}" for i in valve_devs]),
        )
        await ctx.reply(embed=embed)

    @aluloop(minutes=3)
    async def bugtracker_news_worker(self):
        """The task to
        * track GitHub events/comments in the Dota 2 Bug Tracker Repository
        * analyze them and build Timelines
        * send messages to news channel if Valve developers activity was spotted.
        """

        log.debug("^^^ BugTracker task started ^^^")

        query = "SELECT git_checked_dt FROM botinfo WHERE id=$1"
        dt: datetime.datetime = await self.bot.pool.fetchval(query, const.Guild.community)
        now = datetime.datetime.now(datetime.timezone.utc)

        # if self.bot.test:  # FORCE TESTING
        #     dt = now - datetime.timedelta(hours=2)

        issue_dict: dict[int, TimeLine] = dict()

        # Closed / Self-assigned / Reopened Events
        for page_number in itertools.count(start=1, step=1):
            async for event in self.bot.github.paginate(
                self.bot.github.rest.issues.async_list_events_for_repo,
                owner="ValveSoftware",
                repo="Dota2-Gameplay",
                # it's sorted by updated time descending
                # unfortunately, no "since" parameter.
                # this is why we need to have this page_number workaround
                page=page_number,
            ):
                if not event.actor or not event.issue or not event.issue.user:
                    # check if this is a valid issue event
                    continue

                event_created_at = event.created_at.replace(tzinfo=datetime.timezone.utc)
                log.debug(
                    "Found event: %s %s %s %s ", event.event, event.issue.number, event.actor.login, event_created_at
                )
                if event_created_at < dt:
                    # we reached events that we are supposedly already checked
                    break
                if event_created_at > now:
                    # these events got created after task start and before paginator
                    # therefore we leave them untouched for the next batch
                    continue
                if not event.event in [x.name for x in list(EventType)]:
                    continue

                if (login := event.actor.login) in self.valve_devs:
                    # it's confirmed that Valve dev is an actor of the event.
                    pass
                elif login != event.issue.user.login:
                    # if actor is not OP of the issue then we can consider that this person is a valve dev
                    self.valve_devs.append(login)
                    query = """
                        INSERT INTO valve_devs (login) VALUES ($1)
                        ON CONFLICT DO NOTHING;
                    """
                    await self.bot.pool.execute(query, login)
                else:
                    # looks like non-dev event
                    continue

                issue_dict.setdefault(event.issue.number, TimeLine(issue=event.issue)).add_action(
                    Event(
                        enum_type=(getattr(EventType, event.event)).value,
                        created_at=event.created_at,
                        actor=event.actor,
                        issue_number=event.issue.number,
                    )
                )
            else:
                continue  # only executed if the inner loop did NOT break
            break  # only executed if the inner loop DID break

        # Issues opened by Valve devs
        async for issue in self.bot.github.paginate(
            self.bot.github.rest.issues.async_list_for_repo,
            owner="ValveSoftware",
            repo="Dota2-Gameplay",
            sort="updated",
            state="open",
            since=dt,
        ):
            if not dt < issue.created_at.replace(tzinfo=datetime.timezone.utc) < now:
                continue

            if issue.user and issue.user.login in self.valve_devs:
                issue_dict.setdefault(issue.number, TimeLine(issue=issue)).add_action(
                    Comment(
                        enum_type=CommentType.opened.value,
                        created_at=issue.created_at,
                        actor=issue.user,
                        issue_number=issue.number,
                        comment_body=issue.body if issue.body else "",
                    )
                )

        # Comments left by Valve devs
        async for comment in self.bot.github.paginate(
            self.bot.github.rest.issues.async_list_comments_for_repo,
            owner="ValveSoftware",
            repo="Dota2-Gameplay",
            sort="updated",
            since=dt,
        ):
            if not comment.user or not comment.user.login in self.valve_devs:
                continue

            # comment doesn't have issue object attached directly so we need to manually grab it
            # just take numbers from url string ".../Dota2-Gameplay/issues/2524" with `.split`
            issue_number = int(comment.issue_url.split("/")[-1])

            # if the issue is not in the dict then we need to async_get it ourselves
            issue_dict.setdefault(issue_number, TimeLine(issue=await self.get_issue(issue_number))).add_action(
                Comment(
                    enum_type=CommentType.commented.value,
                    created_at=comment.created_at,
                    actor=comment.user,
                    issue_number=issue_number,
                    comment_body=comment.body if comment.body else "",
                    comment_url=comment.html_url,
                )
            )

        embed_and_files = [v.embed_and_file(self.bot) for v in issue_dict.values()]

        batches_to_send: list[list[tuple[discord.Embed, discord.File]]] = []
        character_counter, embed_counter = 0, 0
        for embed, file in embed_and_files:
            character_counter += len(embed)
            embed_counter += 1
            if character_counter < const.Limit.Embed.sum_all and embed_counter < 10 + 1:
                try:
                    batches_to_send[-1].append((embed, file))
                except IndexError:
                    batches_to_send.append([(embed, file)])
            else:
                character_counter, embed_counter = len(embed), 1
                batches_to_send.append([(embed, file)])

        for batch in batches_to_send:
            message = await self.news_channel.send(
                embeds=[embed for (embed, _file) in batch],
                files=[file for (_embed, file) in batch],
            )
            await message.publish()

        query = "UPDATE botinfo SET git_checked_dt=$1 WHERE id=$2"
        await self.bot.pool.execute(query, now, const.Guild.community)
        log.debug("^^^ BugTracker task is finished ^^^")

    async def get_issue(self, issue_number: int):
        """Shortcut to get a Dota 2 Bug Tracker issue by its number."""
        return (
            await self.bot.github.rest.issues.async_get(
                owner="ValveSoftware",
                repo="Dota2-Gameplay",
                issue_number=issue_number,
            )
        ).parsed_data


async def setup(bot: AluBot):
    await bot.add_cog(BugTracker(bot))
