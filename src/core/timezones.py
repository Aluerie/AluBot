"""Timezones.

User-friendly timezone handling: picking a timezone with autocomplete, remembering the choice of each user
and converting between UTC and the user's timezone.

Notices
-------
* MPL-2.0 License, see LICENSE file for more details.
* Copyright (C) 2020-present @Aluerie.
"""

from __future__ import annotations

import asyncio
import datetime as dt
import logging
import zoneinfo
from typing import TYPE_CHECKING, Final, NamedTuple, override

import aiohttp
from discord import app_commands
from lxml import etree  # ty: ignore[unresolved-import]

from shared import cache, clock, errors, fuzzy

if TYPE_CHECKING:
    from core import Bot, Interaction

__all__ = (
    "TimeZone",
    "TimeZoneTransformer",
    "TimezoneManager",
    "TransformTimeZone",
)

log = logging.getLogger(__name__)
log.setLevel(logging.INFO)

CLDR_TIMEZONE_URL: Final = "https://raw.githubusercontent.com/unicode-org/cldr/main/common/bcp47/timezone.xml"
LABELS_REFRESH_INTERVAL: Final = dt.timedelta(hours=6)
"""Labels contain the current UTC offset, which changes with DST, so they are rebuilt from time to time."""
FETCH_RETRY_DELAYS: Final = (5.0, 30.0, 120.0)
"""Seconds to wait between attempts to download the CLDR data. The bot works without it, just with raw IANA keys."""
MAX_CHOICE_LENGTH: Final = 100
"""Discord limit for the name of an autocomplete choice."""

# Extra manual timezone names/aliases that the CLDR data doesn't have (or doesn't have in the way people type them).
EXTRA_TIMEZONES: Final = {
    "Eastern Time": "America/New_York",
    "Central Time": "America/Chicago",
    "Mountain Time": "America/Denver",
    "Pacific Time": "America/Los_Angeles",
    # (Unfortunately) special case American timezone abbreviations
    "EST": "America/New_York",
    "CST": "America/Chicago",
    "MST": "America/Denver",
    "PST": "America/Los_Angeles",
    "EDT": "America/New_York",
    "CDT": "America/Chicago",
    "MDT": "America/Denver",
    "PDT": "America/Los_Angeles",
}

# CLDR identifiers for the most common timezones for the default autocomplete drop down.
# N.B. limited to 25 choices.
# cSpell:disable
POPULAR_CLDR_IDS: Final = (
    # America
    "usnyc",  # America/New_York
    "uslax",  # America/Los_Angeles
    "uschi",  # America/Chicago
    "usden",  # America/Denver
    # India
    "inccu",  # Asia/Kolkata
    # Europe
    "trist",  # Europe/Istanbul
    "rumow",  # Europe/Moscow
    "gblon",  # Europe/London
    "frpar",  # Europe/Paris
    "esmad",  # Europe/Madrid
    "deber",  # Europe/Berlin
    "grath",  # Europe/Athens
    "uaiev",  # Europe/Kyiv
    "itrom",  # Europe/Rome
    "nlams",  # Europe/Amsterdam
    "plwaw",  # Europe/Warsaw
    # Canada
    "cator",  # America/Toronto
    # Australia
    "aubne",  # Australia/Brisbane
    "ausyd",  # Australia/Sydney
    # Brazil
    "brsao",  # America/Sao_Paulo
    # Japan
    "jptyo",  # Asia/Tokyo
    # China
    "cnsha",  # Asia/Shanghai
)
# cSpell:enable

# Used for the default autocomplete drop down while the CLDR data is not downloaded (yet).
POPULAR_IANA_KEYS: Final = (
    "America/New_York",
    "America/Los_Angeles",
    "America/Chicago",
    "America/Denver",
    "Asia/Kolkata",
    "Europe/Istanbul",
    "Europe/Moscow",
    "Europe/London",
    "Europe/Paris",
    "Europe/Madrid",
    "Europe/Berlin",
    "Europe/Athens",
    "Europe/Kyiv",
    "Europe/Rome",
    "Europe/Amsterdam",
    "Europe/Warsaw",
    "America/Toronto",
    "Australia/Brisbane",
    "Australia/Sydney",
    "America/Sao_Paulo",
    "Asia/Tokyo",
    "Asia/Shanghai",
)


class TimeZone(NamedTuple):
    """Timezone Named-Tuple.

    Attributes
    ----------
    label
        Display value that will be shown to the user like '(UTC+01:00) Berlin, Germany'.
    key
        IANA alias string that will be used in ``zoneinfo.ZoneInfo(key=key)`` like 'Europe/Berlin'
        or you can just use `to_tzinfo`.
    """

    label: str
    key: str

    def to_tzinfo(self) -> zoneinfo.ZoneInfo:
        """Convert to tzinfo compatible ZoneInfo object.

        These can be put into `tz` argument of datetime library functions.
        """
        return zoneinfo.ZoneInfo(self.key)

    def to_choice(self) -> app_commands.Choice[str]:
        """Convert to an autocomplete choice."""
        return app_commands.Choice(name=self.label[:MAX_CHOICE_LENGTH], value=self.key)


class CLDRDataEntry(NamedTuple):
    """Single timezone entry of the CLDR (Unicode Common Locale Data Repository) data."""

    description: str
    aliases: list[str]
    deprecated: bool
    preferred: str | None


def parse_cldr_timezones(xml: bytes) -> dict[str, CLDRDataEntry]:
    """Parse the CLDR ``bcp47/timezone.xml`` into entries by their CLDR identifier.

    Parameters
    ----------
    xml
        Raw content of the XML file.

    Returns
    -------
    dict[str, CLDRDataEntry]
        Mapping of CLDR identifier (like "deber") to its entry.
    """
    parser = etree.XMLParser(ns_clean=True, recover=True, encoding="utf-8")
    tree = etree.fromstring(xml, parser=parser)

    return {
        node.attrib["name"]: CLDRDataEntry(
            description=node.get("description", node.attrib["name"]),
            aliases=node.get("alias", "Etc/Unknown").split(" "),
            deprecated=node.get("deprecated", "false") == "true",
            preferred=node.get("preferred"),
        )
        for node in tree.iter("type")
        # Filter the Etc/ entries (except UTC)
        if not node.attrib["name"].startswith(("utcw", "utce", "unk"))  # cspell: disable-line
        and not node.get("description", "").startswith("POSIX")
    }


class TimezoneManager:
    """Timezone Manager Client.

    Due to client-like need to fill the cache of timezones, I decided to move the
    whole thing into separate entity that will be in bot attribute and available
    for the whole bot so different cogs like reminders/birthdays can use it.

    The user-friendly data is downloaded in the background by `start`. Until it's there (or if the download fails)
    the manager works with plain IANA keys.

    Attributes
    ----------
    bot
        The bot instance.
    valid_timezones
        All IANA timezone keys that the system knows about.
    """

    def __init__(self, bot: Bot) -> None:
        self.bot: Bot = bot

        self.valid_timezones: frozenset[str] = frozenset(zoneinfo.available_timezones())
        self._lowercase_timezones: dict[str, str] = {key.lower(): key for key in self.valid_timezones}

        self._entries: dict[str, CLDRDataEntry] = {}
        self._timezone_aliases: dict[str, str] = {}
        self._labels_built_at: dt.datetime | None = None
        self._load_task: asyncio.Task[None] | None = None

    ####################################################################################################################
    # LIFECYCLE
    ####################################################################################################################

    def start(self) -> None:
        """Start downloading the user-friendly timezone data in the background."""
        self._load_task = asyncio.create_task(self._load_cldr(), name="timezone-manager-load")

    def close(self) -> None:
        """Stop the background download if it's still going."""
        if self._load_task is not None:
            self._load_task.cancel()

    async def _load_cldr(self) -> None:
        """Download the CLDR data (with a few retries) and build the timezone labels from it."""
        for attempt, delay in enumerate((*FETCH_RETRY_DELAYS, None), start=1):
            try:
                self._entries = parse_cldr_timezones(await self._download_cldr())
            except aiohttp.ClientError, TimeoutError, etree.XMLSyntaxError, KeyError:
                log.warning("Could not load CLDR timezone data (attempt %s).", attempt, exc_info=True)
                if delay is None:
                    log.exception("Giving up on CLDR timezone data: falling back to plain IANA keys.")
                    return
                await asyncio.sleep(delay)
            else:
                self._build_aliases()
                log.info("Loaded %s CLDR timezone entries.", len(self._entries))
                return

    async def _download_cldr(self) -> bytes:
        """Download raw CLDR timezone XML.

        Apparently official python documentation recommend doing this in this caution note
        https://docs.python.org/3/library/zoneinfo.html#zoneinfo.ZoneInfo.key
        """
        timeout = aiohttp.ClientTimeout(total=30)
        async with self.bot.session.get(CLDR_TIMEZONE_URL, timeout=timeout) as response:
            response.raise_for_status()
            return await response.read()

    ####################################################################################################################
    # LABELS
    ####################################################################################################################

    def _pick_alias(self, entry: CLDRDataEntry) -> str | None:
        """Pick an IANA key for the entry that this system actually knows about.

        These use the first entry in the alias list as the "canonical" name to use when mapping the
        timezone to the IANA database.
        The CLDR database is not particularly correct when it comes to these, but neither is the IANA database.
        It turns out the notion of a "canonical" name is a bit of a mess. This works fine for users where
        this is only used for display purposes, but it's not ideal.
        """
        if entry.preferred is not None:
            preferred = self._entries.get(entry.preferred)
            if preferred is not None:
                entry = preferred
        return next((alias for alias in entry.aliases if alias in self.valid_timezones), None)

    def _build_aliases(self) -> None:
        """Build `display label -> IANA key` mapping from the CLDR entries using the current UTC offsets."""
        now = clock.utcnow()
        aliases: dict[str, str] = {}

        for entry in self._entries.values():
            if (alias := self._pick_alias(entry)) is not None:
                offset = self.get_utc_offset_string(alias, now)
                aliases[f"(UTC{offset}) {entry.description}"] = alias

        for name, alias in EXTRA_TIMEZONES.items():
            offset = self.get_utc_offset_string(alias, now)
            aliases[f"(UTC{offset}) {name}"] = alias

        self._timezone_aliases = aliases
        self._labels_built_at = now

    def _refresh_labels_if_stale(self) -> None:
        """Rebuild labels if they are old: the UTC offsets in them change with DST."""
        if self._labels_built_at is None:
            return
        if clock.utcnow() - self._labels_built_at > LABELS_REFRESH_INTERVAL:
            self._build_aliases()

    @staticmethod
    def get_utc_offset_string(iana_alias: str, when: dt.datetime | None = None) -> str:
        """Get UTC offset string like "+03:00" of the timezone at the given moment.

        Parameters
        ----------
        iana_alias
            IANA key of the timezone, i.e. "Europe/Berlin".
        when
            The moment to get the offset at, since it depends on DST. Defaults to now.

        Returns
        -------
        str
            Offset in ``±HH:MM`` format.
        """
        offset = (when or clock.utcnow()).astimezone(zoneinfo.ZoneInfo(iana_alias)).utcoffset() or dt.timedelta()

        # Hours and minutes are split from the absolute value: `divmod` on a negative total would give
        # "-4h +30m" for "-03:30" (Newfoundland), i.e. the wrong time.
        total_minutes = int(offset.total_seconds() // 60)
        hours, minutes = divmod(abs(total_minutes), 60)
        return f"{'-' if total_minutes < 0 else '+'}{hours:02d}:{minutes:02d}"

    ####################################################################################################################
    # SEARCH
    ####################################################################################################################

    def default_timezones(self) -> list[app_commands.Choice[str]]:
        """Get the most popular timezones for the default autocomplete drop down (when nothing is typed yet)."""
        self._refresh_labels_if_stale()
        now = clock.utcnow()

        if self._entries:
            keys_and_labels = [
                (alias, entry.description)
                for cldr_id in POPULAR_CLDR_IDS
                if (entry := self._entries.get(cldr_id)) and (alias := self._pick_alias(entry)) is not None
            ]
        else:
            keys_and_labels = [(key, key) for key in POPULAR_IANA_KEYS if key in self.valid_timezones]

        return [
            TimeZone(label=f"(UTC{self.get_utc_offset_string(key, now)}) {label}", key=key).to_choice()
            for key, label in keys_and_labels
        ]

    def find_timezones(self, query: str) -> list[TimeZone]:
        """Fuzzy-search timezones by the query.

        Parameters
        ----------
        query
            Text to search with. If it has a '/' in it then it's treated as a part of an IANA key,
            otherwise as a part of a user-friendly label.

        Returns
        -------
        list[TimeZone]
            Matching timezones, best matches first.
        """
        self._refresh_labels_if_stale()

        # A bit hacky, but if '/' is in the query then it's looking for a raw identifier
        # otherwise it's looking for a CLDR alias
        if "/" in query or not self._timezone_aliases:
            return [TimeZone(label=key, key=key) for key in fuzzy.finder(query, self.valid_timezones)]

        labels = fuzzy.finder(query, self._timezone_aliases.keys())
        return [TimeZone(label=label, key=self._timezone_aliases[label]) for label in labels]

    def resolve(self, query: str) -> TimeZone:
        """Turn user input into a single timezone.

        Parameters
        ----------
        query
            User input: an autocomplete label, an IANA key (case-insensitive) or just a part of the name.

        Returns
        -------
        TimeZone
            The timezone that the input stands for.

        Raises
        ------
        errors.BadUserInputError
            If the input doesn't match any timezone or matches several different ones.
        """
        query = query.strip()

        # Prioritize aliases because they handle short codes slightly better
        if query in self._timezone_aliases:
            # display label -> IANA key so we look in display names here
            return TimeZone(label=query, key=self._timezone_aliases[query])

        if (key := self._lowercase_timezones.get(query.lower())) is not None:
            return TimeZone(label=key, key=key)

        # else we need to fuzzy-search the best suited timezone
        matches = self.find_timezones(query)
        if len({tz.key for tz in matches}) == 1:
            return matches[0]

        help_text = (
            "I insist that you should be using user-friendly suggestions from autocomplete for "
            "`timezone` argument in `/timezone set`, `/birthday set`, etc. slash commands to ease your choice. "
            "You can also use IANA aliases for timezones which you can find here: "
            "[TimeZonePicker](https://kevinnovak.github.io/Time-Zone-Picker/) or "
            "[WikiPage](https://en.wikipedia.org/wiki/List_of_tz_database_time_zones)'s `TZ identifier` column"
        )
        if not matches:
            msg = f"Could not find timezone for input:```\n{query!r}```\n{help_text}"
        else:
            suggestions = "\n".join(f"* {tz.label}" for tz in matches[:5])
            msg = f"`{query}` matches several timezones, please be more specific:\n{suggestions}\n\n{help_text}"
        raise errors.BadUserInputError(msg)

    ####################################################################################################################
    # USER SETTINGS
    ####################################################################################################################

    @cache.cache()
    async def get_timezone(self, user_id: int, /) -> str | None:
        """Get the IANA key of the timezone the user has set.

        Parameters
        ----------
        user_id
            Discord ID of the user.

        Returns
        -------
        str | None
            The IANA key or `None` if the user has no timezone set.
        """
        query = "SELECT timezone FROM user_settings WHERE id = $1;"
        record = await self.bot.pool.fetchrow(query, user_id)
        return record["timezone"] if record else None

    async def get_tzinfo(self, user_id: int, /) -> dt.tzinfo:
        """Get the timezone of the user as `tzinfo`, UTC if the user has none (or the saved one is unusable).

        Parameters
        ----------
        user_id
            Discord ID of the user.
        """
        key = await self.get_timezone(user_id)
        if key is None:
            return dt.UTC
        try:
            return zoneinfo.ZoneInfo(key)
        except zoneinfo.ZoneInfoNotFoundError, ValueError:
            log.warning("User %s has an unknown timezone saved: %r", user_id, key)
            return dt.UTC

    async def set_timezone(self, user_id: int, timezone: TimeZone, /) -> None:
        """Save the timezone of the user.

        Parameters
        ----------
        user_id
            Discord ID of the user.
        timezone
            The timezone to save.
        """
        query = """
            INSERT INTO user_settings (id, timezone)
            VALUES ($1, $2)
            ON CONFLICT (id) DO UPDATE SET timezone = $2;
        """
        await self.bot.pool.execute(query, user_id, timezone.key)
        self.get_timezone.invalidate(self, user_id)

    async def clear_timezone(self, user_id: int, /) -> None:
        """Forget the timezone of the user.

        Parameters
        ----------
        user_id
            Discord ID of the user.
        """
        await self.bot.pool.execute("UPDATE user_settings SET timezone = NULL WHERE id = $1", user_id)
        self.get_timezone.invalidate(self, user_id)


class TimeZoneTransformer(app_commands.Transformer):
    """Transformer to use in app_commands."""

    @override
    async def transform(self, interaction: Interaction, value: str) -> TimeZone:  # ty: ignore[invalid-method-override]
        return interaction.client.tz_manager.resolve(value)

    @override
    async def autocomplete(self, interaction: Interaction, value: str) -> list[app_commands.Choice[str]]:  # ty: ignore[invalid-method-override]
        tz_manager = interaction.client.tz_manager
        if not value:
            return tz_manager.default_timezones()
        return [tz.to_choice() for tz in tz_manager.find_timezones(value)[:25]]


TransformTimeZone = app_commands.Transform[TimeZone, TimeZoneTransformer]
