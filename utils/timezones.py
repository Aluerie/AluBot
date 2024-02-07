from __future__ import annotations

import datetime
import zoneinfo
from typing import TYPE_CHECKING, NamedTuple, override

import discord
from discord import app_commands
from discord.ext import commands
from lxml import etree

from . import AluContext, cache, fuzzy

if TYPE_CHECKING:
    from bot import AluBot


class TimeZone(NamedTuple):
    """Timezone Named-Tuple.

    !!! Note that we STILL need to use
    >>> timezone: app_commands.Transform[TimeZone, TimeZoneTransformer]
    in hybrid commands to make autocomplete work
    (in app commands to make it work at all)

    Attributes
    ----------
    label: str
        display value that will be shown to the user like '(UTC+01:00) Berlin, Germany'
    key: str
        IANA alias string that will be used in zoneinfo.ZoneInfo(key=key) like 'Europe/Berlin'
        or you can just use timezone.to_tz()

    """

    label: str
    key: str

    def to_tzinfo(self) -> zoneinfo.ZoneInfo:
        return zoneinfo.ZoneInfo(self.key)

    @classmethod
    async def convert(cls, ctx: AluContext, argument: str) -> TimeZone:  # Self won't proc cause of try
        tz_manager = ctx.bot.tz_manager

        # Prioritise aliases because they handle short codes slightly better
        if argument in tz_manager._timezone_aliases:
            # list of display_name -> IANA key so we look in display names here
            return cls(key=tz_manager._timezone_aliases[argument], label=argument)

        if argument in tz_manager.valid_timezones:
            # list of IANA timezone keys from zoneinfo.available_timezones()
            return cls(key=argument, label=argument)

        # else we need to fuzzy-search the best suited timezone
        timezones = tz_manager.find_timezones(argument)

        try:
            return await ctx.bot.disambiguator.disambiguate(ctx, timezones, lambda t: t.label, ephemeral=True)
        except ValueError:
            msg = (
                f"Could not find timezone for input:```\n{argument!r}```\n"
                "I insist that you should be using user-friendly suggestions from autocomplete for "
                "`timezone` argument in `/timezone set`, `/birthday set`, etc. slash commands to ease your choice. "
                "You can also use IANA aliases for timezones which you can find here: "
                "[TimeZonePicker](https://kevinnovak.github.io/Time-Zone-Picker/) or "
                "[WikiPage](https://en.wikipedia.org/wiki/List_of_tz_database_time_zones)'s `TZ identifier` column"
            )
            raise commands.BadArgument(msg)

    def to_choice(self) -> app_commands.Choice[str]:
        return app_commands.Choice(name=self.label, value=self.key)


class TimeZoneTransformer(app_commands.Transformer):
    """Transformer to use in app_commands.

    Note that we need to use
    >>> timezone: app_commands.Transform[TimeZone, TimeZoneTransformer]
    in app commands for them to work
    and in hybrid if we need autocomplete to work
    """

    @override
    async def transform(self, interaction: discord.Interaction[AluBot], value: str) -> TimeZone:
        ctx = await AluContext.from_interaction(interaction)
        return await TimeZone.convert(ctx, value)

    @override
    async def autocomplete(self, interaction: discord.Interaction[AluBot], arg: str) -> list[app_commands.Choice[str]]:
        tz_manager = interaction.client.tz_manager

        if not arg:
            return tz_manager._default_timezones
        matches = tz_manager.find_timezones(arg)
        return [tz.to_choice() for tz in matches[:25]]


class CLDRDataEntry(NamedTuple):
    description: str
    aliases: list[str]
    deprecated: bool
    preferred: str | None


class TimezoneManager:
    """Timezone Manager Client.

    Due to client-like need to fill the cache of timezones, I decided to move the
    whole thing into separate entity that will be in bot attribute and available
    for the whole bot so different cogs like reminders/birthdays can use it.

    Note that we need to
    >>> async def cog_load(self) -> None:
    >>>    self.bot.initiate_tz_manager()

    in cogs with timezone functionality.
    """

    def __init__(self, bot: AluBot) -> None:
        self.bot: AluBot = bot

        self._timezone_aliases: dict[str, str] = {}
        self.valid_timezones: set[str] = zoneinfo.available_timezones()
        self._default_timezones: list[app_commands.Choice[str]] = []

        self.bot.loop.create_task(self.parse_bcp47_timezones())

    async def parse_bcp47_timezones(self) -> None:
        """Get user-friendly timezone data from CLDR (the Unicode Common Locale Data Repository).

        Apparently official python documentation recommend doing this in this caution note
        https://docs.python.org/3/library/zoneinfo.html#zoneinfo.ZoneInfo.key

        This functions sets self._timezone_aliases into dictionary mapping of
        user-friendly `display_timezone_name` -> `alias` in IANA format to pass into zoneinfo.ZoneInfo(key=key)
        """
        async with self.bot.session.get(
            "https://raw.githubusercontent.com/unicode-org/cldr/main/common/bcp47/timezone.xml"
        ) as resp:
            if resp.status != 200:
                return

            parser = etree.XMLParser(ns_clean=True, recover=True, encoding="utf-8")
            tree = etree.fromstring(await resp.read(), parser=parser)

            # Build a temporary dictionary to resolve "preferred" mappings
            entries: dict[str, CLDRDataEntry] = {
                node.attrib["name"]: CLDRDataEntry(
                    description=node.attrib["description"],
                    aliases=node.get("alias", "Etc/Unknown").split(" "),
                    deprecated=node.get("deprecated", "false") == "true",
                    preferred=node.get("preferred"),
                )
                for node in tree.iter("type")
                # Filter the Etc/ entries (except UTC)
                if not node.attrib["name"].startswith(("utcw", "utce", "unk"))  # /* cspell: disable-line */
                and not node.attrib["description"].startswith("POSIX")
            }

            now_utc = datetime.datetime.now(datetime.UTC)

            for entry in entries.values():
                # These use the first entry in the alias list as the "canonical" name to use when mapping the
                # timezone to the IANA database.
                # The CLDR database is not particularly correct when it comes to these, but neither is the IANA database.
                # It turns out the notion of a "canonical" name is a bit of a mess. This works fine for users where
                # this is only used for display purposes, but it's not ideal.
                if entry.preferred is not None:
                    preferred = entries.get(entry.preferred)
                    alias = preferred.aliases[0] if preferred is not None else entry.aliases[0]
                else:
                    alias = entry.aliases[0]

                utc_offset_string = self.get_utc_offset_string(alias, now_utc)
                description = f"(UTC{utc_offset_string}) {entry.description}"
                self._timezone_aliases[description] = alias

            # Extra manual timezone names/aliases
            extra_entries: dict[str, str] = {
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
            for timezone_name, alias in extra_entries.items():
                utc_offset_string = self.get_utc_offset_string(alias, now_utc)
                description = f"(UTC{utc_offset_string}) {timezone_name}"
                self._timezone_aliases[description] = alias

            # CLDR identifiers for most common timezones for the default autocomplete drop down
            # n.b. limited to 25 choices
            # /* cSpell:disable */
            default_popular_timezone_ids = (
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
                "uaiev",  # Europe/Kyev
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
            # /* cSpell:enable */

            for key in default_popular_timezone_ids:
                entry = entries.get(key)
                if entry is not None:
                    alias = entry.aliases[0]
                    utc_offset_string = self.get_utc_offset_string(alias, now_utc)
                    description = f"(UTC{utc_offset_string}) {entry.description}"
                    self._default_timezones.append(app_commands.Choice(name=description, value=alias))

    def find_timezones(self, query: str) -> list[TimeZone]:
        # A bit hacky, but if '/' is in the query then it's looking for a raw identifier
        # otherwise it's looking for a CLDR alias
        if "/" in query:
            return [TimeZone(key=a, label=a) for a in fuzzy.finder(query, self.valid_timezones)]

        keys = fuzzy.finder(query, self._timezone_aliases.keys())
        return [TimeZone(label=k, key=self._timezone_aliases[k]) for k in keys]

    @staticmethod
    def get_utc_offset_string(iana_alias: str, now_utc: datetime.datetime) -> str:
        """Get UTC offset string like +03:00.

        Yes, please pass now_utc = datetime.datetime.now(datetime.timezone.utc) here
        I don't want to create it each function run.
        """
        # why do I need to have/construct a datetime object to get UTC offset, sadge
        # this data is not affected by DST, isn't it ?
        now_tz = now_utc.astimezone(tz=zoneinfo.ZoneInfo(key=iana_alias))

        offset = now_tz.utcoffset()
        if offset is not None:
            minutes, _ = divmod(int(offset.total_seconds()), 60)
            hours, minutes = divmod(minutes, 60)
            return f"{hours:+03d}:{minutes:02d}"
        else:
            return "+00:00"

    @cache.cache()
    async def get_timezone(self, user_id: int, /) -> str | None:
        query = "SELECT timezone from user_settings WHERE id = $1;"
        record = await self.bot.pool.fetchrow(query, user_id)
        return record["timezone"] if record else None

    async def get_tzinfo(self, user_id: int, /) -> datetime.tzinfo:
        tz = await self.get_timezone(user_id)
        if tz is None:
            return datetime.UTC
        return zoneinfo.ZoneInfo(tz) or datetime.UTC

    async def set_timezone(self, user_id: int, timezone: TimeZone) -> None:
        query = """
            INSERT INTO user_settings (id, timezone)
            VALUES ($1, $2)
            ON CONFLICT (id) DO UPDATE SET timezone = $2;
        """
        await self.bot.pool.execute(query, user_id, timezone.key)
        self.get_timezone.invalidate(self, user_id)


TransformTimeZone = app_commands.Transform[TimeZone, TimeZoneTransformer]
