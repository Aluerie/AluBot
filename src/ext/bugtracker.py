"""Bug Tracker.

Notices
-------
* MPL-2.0 License, see LICENSE file for more details.
* Copyright (C) 2020-present @Aluerie.
"""

from __future__ import annotations

import datetime as dt
import itertools
import logging
import re
import textwrap
from dataclasses import dataclass, field
from operator import attrgetter
from typing import TYPE_CHECKING, Final, override

import discord
from githubkit import GitHub
from githubkit.exception import RequestError, RequestFailed
from PIL import Image

from config import env
from core import Cog
from shared import clock, fmt
from shared.concepts import loop
from utils import const

if TYPE_CHECKING:
    from githubkit_schemas.latest.models import Issue, SimpleUser

    from core import Bot

log = logging.getLogger(__name__)
log.setLevel(logging.INFO)

# this might backfire but why the hell `githubkit` put `GET REST` logs from `httpx` as `log.INFO`, jesus christ.
logging.getLogger("httpx").setLevel(logging.WARNING)

GITHUB_OWNER = "ValveSoftware"
GITHUB_REPO = "Dota2-Gameplay"
GITHUB_REPO_URL = f"https://github.com/{GITHUB_OWNER}/{GITHUB_REPO}"
ISSUE_URL_REGEX = re.compile(rf"({re.escape(GITHUB_REPO_URL)}/issues/(\d+))")

type Timelines = dict[int, TimeLine]


@dataclass(frozen=True)
class ActionKind:
    """Kind of a GitHub Issue "Action".

    In the context of this file "git issue action" is something that can happen within a GitHub issue:
    opened, closed, commented, assigned, reopened.

    If we spot a Valve developer doing one of these things - we want to make a news post out of it.

    Names must match across three places: this `name`, the PNG picture in the assets folder
    and the emote name in the extra emote server. Event names additionally match GitHub API terminology.

    Emote notes:
    * pictures are taken from 16px versions here https://primer.style/octicons/
      and background circles are added with a simple online editor https://iconscout.com/color-editor;
    * make pics to be 128x128, so it's consistent for all sizes.

    Attributes
    ----------
    name
        Action's name.
    color
        Color to assign for embed when sending the bugtracker news message.
    word
        Verb to put into author string in the said embed.
    emoji
        Emoji to use in a special type of embed where there are many different actions per one issue.
    """

    name: str
    color: int
    word: str
    emoji: const.Emoji

    @property
    def file_path(self) -> str:
        """Path to the image file to put into thumbnail for the embed."""
        return f"./assets/images/git/{self.name}.png"

    def file(self, number: int) -> discord.File:
        """Get discord.File linked to the action image."""
        # without a `number` we had a "bug" where the image would go outside embeds
        return discord.File(self.file_path, filename=f"{self.name}_{number}.png")


# "events" - stuff that doesn't have to have text with it
ASSIGNED = ActionKind("assigned", color=0x21262D, word="assigned", emoji=const.Emoji.assigned)
CLOSED = ActionKind("closed", color=0x9B6CEA, word="closed", emoji=const.Emoji.closed)
REOPENED = ActionKind("reopened", color=0x238636, word="reopened", emoji=const.Emoji.reopened)
EVENT_KINDS = {kind.name: kind for kind in (ASSIGNED, CLOSED, REOPENED)}

# "comments" - stuff that has to have text with it
COMMENTED = ActionKind("commented", color=0x4285F4, word="commented", emoji=const.Emoji.commented)
OPENED = ActionKind("opened", color=0x52CC99, word="opened", emoji=const.Emoji.opened)


@dataclass(kw_only=True)
class Action:
    """Action. These are ordered properly in the Git Issue's Timeline.

    Attributes
    ----------
    kind
        Action kind to gather common data, like picture file path from it.
    created_at
        Datetime for when the action took place.
    actor
        GitHub user who created the event/comment.
    issue_number
        GitHub issue number.
    """

    kind: ActionKind
    created_at: dt.datetime
    actor: SimpleUser
    issue_number: int

    @property
    def author_str(self) -> str:
        """Author string to put into the embed."""
        return f"@{self.actor.login} {self.kind.word} bugtracker issue #{self.issue_number}"


class Event(Action):
    """Github Issue Timeline's Event: closed, assigned, reopened."""

    # this needs to be a separate class bcs of the `isinstance` checks


@dataclass(kw_only=True)
class Comment(Action):
    """Github Issue Timeline's Comment: commented, opened."""

    comment_body: str
    comment_url: str | None = None

    @property
    def markdown_body(self) -> str:
        """Convert GitHub issue body to Discord markdown-friendly string."""
        body = ISSUE_URL_REGEX.sub(r"[#\2](\1)", self.comment_body).replace("<br>", "")
        return "\n".join(line for line in body.splitlines() if line)


@dataclass
class TimeLine:
    """Timeline representing collection of ordered Events and Comments.

    Used to sort/order/combine said events/comments and create an embed out of it.

    A common case for github developers is to leave a comment and do one of the events.
    * if there is one author with one event and/or one comment - we send a small embed;
    * otherwise we list everything in chronological order with emotes.

    Attributes
    ----------
    issue
        GitHub Issue to sort events/comments for the embed.
    actions
        List of those events/comments to sort later.
    """

    issue: Issue
    actions: list[Action] = field(default_factory=list)

    def add_action(self, action: Action) -> None:
        """Add action to the Timeline."""
        self.actions.append(action)

    def sorted_actions(self) -> list[Action]:
        """Sort actions by created time."""
        return sorted(self.actions, key=attrgetter("created_at"))

    @property
    def events(self) -> list[Event]:
        """List of event actions."""
        return [a for a in self.actions if isinstance(a, Event)]

    @property
    def comments(self) -> list[Comment]:
        """List of comment actions."""
        return [a for a in self.actions if isinstance(a, Comment)]

    @property
    def actor_ids(self) -> set[int]:
        """Ids of github actors who created those events/comments."""
        return {a.actor.id for a in self.actions}

    @property
    def last_comment_url(self) -> str | None:
        """Last comment url."""
        last = max(self.comments, key=attrgetter("created_at"), default=None)
        return last.comment_url if last else None

    def embed_and_file(self, bot: Bot) -> tuple[discord.Embed, discord.File]:
        """Get embed and file to send in the discord."""
        title = textwrap.shorten(self.issue.title, width=fmt.EMBED_TITLE_LIMIT)
        embed = discord.Embed(title=title, url=self.issue.html_url)

        is_simple = len(self.events) < 2 and len(self.comments) < 2 and len(self.actor_ids) < 2
        file = self._fill_simple(embed) if is_simple else self._fill_combined(embed, bot)

        embed.set_thumbnail(url=f"attachment://{file.filename}")
        return embed, file

    def _fill_simple(self, embed: discord.Embed) -> discord.File:
        """Fill the embed for 1 author and 1 event with a possible comment to it."""
        lead = (self.events or self.comments)[0]
        comment = next(iter(self.comments), None)

        embed.color = lead.kind.color
        url = comment.comment_url if comment else None
        embed.set_author(name=lead.author_str, icon_url=lead.actor.avatar_url, url=url)
        if comment:
            embed.description = comment.markdown_body
        return lead.kind.file(self.issue.number)

    def _fill_combined(self, embed: discord.Embed, bot: Bot) -> discord.File:
        """Fill the embed with every action listed chronologically."""
        embed.color = 0x4078C0  # git color, first in google :D
        actions = self.sorted_actions()

        for action in actions:
            body = action.markdown_body if isinstance(action, Comment) else ""
            # discord doesn't allow empty field values, so fall back to a space
            chunks = itertools.batched(body or " ", fmt.EMBED_FIELD_VALUE_LIMIT, strict=False)
            for chunk in map("".join, chunks):
                embed.add_field(name=f"{action.kind.emoji}{action.author_str}", value=chunk, inline=False)
        embed.set_author(
            name=f"Bugtracker issue #{self.issue.number} update",
            url=self.last_comment_url,
            icon_url="https://em-content.zobj.net/thumbs/120/microsoft/319/frog_1f438.png",
        )

        # stack the action icons diagonally, each one shifted by `offset` pixels
        icon_size, offset = 128, 32
        canvas_size = icon_size + (len(actions) - 1) * offset
        canvas = Image.new("RGBA", (canvas_size, canvas_size), (0, 0, 0, 0))
        for i, action in enumerate(actions):
            with Image.open(action.kind.file_path) as icon:
                canvas.paste(icon, (i * offset, i * offset), icon)
        return bot.image_to_file(canvas, filename=f"bugtracker_update_{self.issue.number}.png")


def batch_embeds(
    embed_and_files: list[tuple[discord.Embed, discord.File]],
) -> list[list[tuple[discord.Embed, discord.File]]]:
    """Group embeds into batches that fit into one discord message (10 embeds, limited total characters)."""
    batches: list[list[tuple[discord.Embed, discord.File]]] = []
    characters = 0
    for embed, file in embed_and_files:
        if batches and len(batches[-1]) < 10 and characters + len(embed) < fmt.EMBED_SUM_ALL_LIMIT:
            batches[-1].append((embed, file))
            characters += len(embed)
        else:
            batches.append([(embed, file)])
            characters = len(embed)
    return batches


class BugTracker(Cog):
    """BugTracker News.

    Track Valve developers activity in the Dota2-Gameplay repository
    and send a notification to #bugtracker-news in my discord server.

    Useful to know what the devs are up to and to quickly test, respond to their actions.

    A bit of privacy-abuse to track people's activity like that, but the repository is public and
    the information is valuable and interesting,
    and helpful to valve devs themselves since I can help asap when they ask for it.

    So hopefully, it's not much of a problem. If there is - please, contact me.

    Attributes
    ----------
    valve_devs
        The known Valve developers who ever interacted with the Bug Tracker.
    bugtracker_worker
        The main task of the cog that tracks, analyzes GitHub events and sends news messages.
    """

    valve_devs: set[str]

    BUGTRACKER_CHANNEL_ID: Final = const.ChannelId(1119041743002800138)
    HIDEOUT_SPAM_CHANNEL_ID: Final = const.ChannelId(970823670702411810)

    @override
    async def cog_load(self) -> None:
        self.github = GitHub(env.GIT_PERSONAL_TOKEN)
        self.valve_devs = await self.get_valve_devs()

        self.bugtracker_worker.add_exception_type(RequestError, RequestFailed)
        self.bugtracker_worker.start()

    @override
    async def cog_unload(self) -> None:
        self.bugtracker_worker.stop()

    @discord.utils.cached_property
    def bugtracker_channel(self) -> discord.TextChannel:
        """Dota 2 Bug tracker news channel."""
        channel_id = self.HIDEOUT_SPAM_CHANNEL_ID if self.bot.test else self.BUGTRACKER_CHANNEL_ID
        return self.bot.get_text_channel(channel_id)

    async def get_valve_devs(self) -> set[str]:
        """Get the set of known Valve developers."""
        rows = await self.bot.pool.fetch("SELECT login FROM valve_devs")
        return {login for (login,) in rows}

    async def get_issue(self, issue_number: int) -> Issue:
        """Shortcut to get a Dota 2 Bug Tracker issue by its number."""
        response = await self.github.rest.issues.async_get(
            owner=GITHUB_OWNER,
            repo=GITHUB_REPO,
            issue_number=issue_number,
        )
        return response.parsed_data

    @loop(minutes=10)
    async def bugtracker_worker(self) -> None:
        """Bugtracker News Task.

        * tracks GitHub events/comments in the Dota 2 Bug Tracker Repository
        * analyzes them and build Timelines
        * sends messages to news channel if Valve developers activity was spotted.
        """
        log.debug("^^^ BugTracker task started ^^^")

        query = "SELECT git_checked_dt FROM botinfo WHERE id=$1"
        last_checked: dt.datetime = await self.bot.pool.fetchval(query, const.Guild.community)
        now = clock.utcnow()

        if self.bot.test:
            # FORCE TESTING
            last_checked = now - dt.timedelta(hours=2)

        timelines: dict[int, TimeLine] = {}
        await self._collect_events(timelines, last_checked, now)
        await self._collect_opened_issues(timelines, last_checked, now)
        await self._collect_comments(timelines, last_checked, now)
        await self._send_news(timelines)

        query = "UPDATE botinfo SET git_checked_dt=$1 WHERE id=$2"
        await self.bot.pool.execute(query, now, const.Guild.community)
        log.debug("^^^ BugTracker task is finished ^^^")

    async def _collect_events(
        self, timelines: dict[int, TimeLine], last_checked: dt.datetime, now: dt.datetime
    ) -> None:
        """Collect Closed / Assigned / Reopened events from Valve devs.

        `paginate` goes through all pages on its own. Events are sorted by updated time descending
        and there is no "since" parameter, so we `break` once we reach already checked events.
        """
        async for event in self.github.paginate(
            self.github.rest.issues.async_list_events_for_repo,
            owner=GITHUB_OWNER,
            repo=GITHUB_REPO,
        ):
            if not event.actor or not event.issue or not event.issue.user:
                # check if this is a valid issue event
                continue

            created_at = event.created_at
            log.debug("Found event: %s %s %s %s ", event.event, event.issue.number, event.actor.login, created_at)
            if created_at < last_checked:
                # we reached events that we already checked
                break
            if created_at > now:
                # these events got created after task start and before paginator
                # therefore we leave them untouched for the next batch
                continue
            if (kind := EVENT_KINDS.get(event.event)) is None:
                continue

            login = event.actor.login
            if login not in self.valve_devs:
                if login in {event.issue.user.login, "github-actions[bot]"}:
                    # actor is OP of the issue or the bot - looks like a non-dev event
                    continue
                # otherwise we can consider that this person is a valve dev
                self.valve_devs.add(login)
                query = "INSERT INTO valve_devs (login) VALUES ($1) ON CONFLICT DO NOTHING"
                await self.bot.pool.execute(query, login)

            timelines.setdefault(event.issue.number, TimeLine(issue=event.issue)).add_action(
                action=Event(
                    kind=kind, created_at=event.created_at, actor=event.actor, issue_number=event.issue.number
                ),
            )

    async def _collect_opened_issues(self, timelines: Timelines, last_checked: dt.datetime, now: dt.datetime) -> None:
        """Collect issues opened by Valve devs."""
        async for issue in self.github.paginate(
            request=self.github.rest.issues.async_list_for_repo,
            owner=GITHUB_OWNER,
            repo=GITHUB_REPO,
            sort="updated",
            state="open",
            since=last_checked,
        ):
            created_at = issue.created_at
            if not last_checked < created_at < now:
                continue
            if not issue.user or issue.user.login not in self.valve_devs:
                continue

            timelines.setdefault(issue.number, TimeLine(issue=issue)).add_action(
                action=Comment(
                    kind=OPENED,
                    created_at=issue.created_at,
                    actor=issue.user,
                    issue_number=issue.number,
                    comment_body=issue.body or "",
                ),
            )

    async def _collect_comments(self, timelines: Timelines, last_checked: dt.datetime, now: dt.datetime) -> None:
        """Collect comments left by Valve devs."""
        async for comment in self.github.paginate(
            request=self.github.rest.issues.async_list_comments_for_repo,
            owner=GITHUB_OWNER,
            repo=GITHUB_REPO,
            sort="updated",
            since=last_checked,
        ):
            # `since` filters by update time, so edited old comments would slip through without this check
            created_at = comment.created_at
            if not last_checked < created_at < now:
                continue
            if not comment.user or comment.user.login not in self.valve_devs:
                continue

            # comment doesn't have issue object attached directly so we need to manually grab it
            # just take numbers from url string ".../Dota2-Gameplay/issues/2524" with `.split`
            issue_number = int(comment.issue_url.split("/")[-1])

            if (timeline := timelines.get(issue_number)) is None:
                timeline = timelines[issue_number] = TimeLine(issue=await self.get_issue(issue_number))
            timeline.add_action(
                action=Comment(
                    kind=COMMENTED,
                    created_at=comment.created_at,
                    actor=comment.user,
                    issue_number=issue_number,
                    comment_body=comment.body or "",
                    comment_url=comment.html_url,
                ),
            )

    async def _send_news(self, timelines: Timelines) -> None:
        """Build embeds out of the timelines and publish them in the news channel."""
        embed_and_files = [timeline.embed_and_file(self.bot) for timeline in timelines.values()]
        for batch in batch_embeds(embed_and_files):
            message = await self.bugtracker_channel.send(
                embeds=[embed for embed, _ in batch],
                files=[file for _, file in batch],
            )
            await message.publish()


async def setup(bot: Bot) -> None:
    """Load the extension (discord.py entry point)."""
    await bot.add_cog(BugTracker(bot))
