from __future__ import annotations

import asyncio
import datetime
import zoneinfo
from typing import TYPE_CHECKING, NamedTuple, Optional, overload

import discord
from discord import app_commands
from discord.ext import commands
from lxml import etree

from utils import fuzzy

if TYPE_CHECKING:
    from bot import AluBot
    from utils import AluContext

from ._base import UserSettingsBaseCog


class TimeZone(NamedTuple):
    label: str  # display value that will be shown to the user like '(UTC+01:00) Berlin, Germany'
    key: str  # IANA alias string that will be used in zoneinfo.ZoneInfo(key=key) like 'Europe/Berlin'

    @classmethod
    async def convert(cls, ctx: AluContext, argument: str) -> TimeZone:  # Self won't proc cause of try
        assert isinstance(ctx.cog, UserSettingsCog)

        # Prioritise aliases because they handle short codes slightly better
        if argument in ctx.cog._timezone_aliases:
            # list of display_name -> IANA key so we look in display names here
            return cls(key=ctx.cog._timezone_aliases[argument], label=argument)

        if argument in ctx.cog.valid_timezones:
            # list of IANA timezone keys from zoneinfo.available_timezones()
            return cls(key=argument, label=argument)

        # else we need to fuzzy-search the best suited timezone
        timezones = ctx.cog.find_timezones(argument)

        try:
            return await ctx.disambiguate(timezones, lambda t: t[0], ephemeral=True)
        except ValueError:
            raise commands.BadArgument(f"Could not find timezone for {argument!r}")

    def to_choice(self) -> app_commands.Choice[str]:
        return app_commands.Choice(name=self.label, value=self.key)


class CLDRDataEntry(NamedTuple):
    description: str
    aliases: list[str]
    deprecated: bool
    preferred: Optional[str]


class UserSettingsCog(UserSettingsBaseCog):
    def __init__(self, bot: AluBot) -> None:
        super().__init__(bot)
        self._timezone_aliases: dict[str, str] = {}
        self.valid_timezones: set[str] = zoneinfo.available_timezones()
        self._default_timezones: list[app_commands.Choice[str]] = []

    async def cog_load(self) -> None:
        await self.parse_bcp47_timezones()

    async def parse_bcp47_timezones(self) -> None:
        """Get user-friendly timezone data from CLDR (the Unicode Common Locale Data Repository)

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

            for entry in entries.values():
                # These use the first entry in the alias list as the "canonical" name to use when mapping the
                # timezone to the IANA database.
                # The CLDR database is not particularly correct when it comes to these, but neither is the IANA database.
                # It turns out the notion of a "canonical" name is a bit of a mess. This works fine for users where
                # this is only used for display purposes, but it's not ideal.
                if entry.preferred is not None:
                    preferred = entries.get(entry.preferred)
                    if preferred is not None:
                        alias = preferred.aliases[0]
                    else:
                        alias = entry.aliases[0]
                else:
                    alias = entry.aliases[0]

                utc_offset_string = self.get_utc_offset_string(iana_alias=alias)
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
                utc_offset_string = self.get_utc_offset_string(iana_alias=alias)
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
                    utc_offset_string = self.get_utc_offset_string(iana_alias=alias)
                    description = f"(UTC{utc_offset_string}) {entry.description}"
                    self._default_timezones.append(app_commands.Choice(name=description, value=alias))

    def find_timezones(self, query: str) -> list[TimeZone]:
        # A bit hacky, but if '/' is in the query then it's looking for a raw identifier
        # otherwise it's looking for a CLDR alias
        if "/" in query:
            return [TimeZone(key=a, label=a) for a in fuzzy.finder(query, self.valid_timezones)]

        keys = fuzzy.finder(query, self._timezone_aliases.keys())
        return [TimeZone(label=k, key=self._timezone_aliases[k]) for k in keys]

    @commands.hybrid_group()
    async def timezone(self, ctx: AluContext):
        """Commands related to managing or retrieving timezone info."""
        await ctx.send_help(ctx.command)

    @timezone.command(name="set")
    @app_commands.describe(timezone="The timezone to change to.")
    async def timezone_set(self, ctx: AluContext, *, timezone: TimeZone):
        """Sets your timezone.

        This is used to convert times to your local timezone when
        using the reminder command and other miscellaneous commands
        such as birthday set.
        """

        query = """ INSERT INTO user_settings (id, timezone)
                    VALUES ($1, $2)
                    ON CONFLICT (id) DO UPDATE SET timezone = $2;
                """
        await ctx.pool.execute(query, ctx.author.id, timezone.key)

        self.bot.get_timezone.invalidate(self, ctx.author.id)
        content = f"Your timezone has been set to {timezone.label} (IANA ID: {timezone.key})."
        await ctx.send(content, ephemeral=True)

    @overload
    def get_utc_offset_string(*, iana_alias: str) -> str:
        ...

    @overload
    def get_utc_offset_string(*, dt: datetime.datetime) -> str:
        ...

    @staticmethod
    def get_utc_offset_string(*, iana_alias: Optional[str] = None, dt: Optional[datetime.datetime] = None) -> str:
        """Get UTC offset string like +03:00"""

        # why do I need to construct a datetime object to get UTC offset, sadge
        # this data is not affected by DST, isn't it ?
        if dt is None:
            if iana_alias is not None:
                now = datetime.datetime.now(datetime.timezone.utc).astimezone(tz=zoneinfo.ZoneInfo(key=iana_alias))
            else:
                raise ValueError("Both `iana_alias` and `dt` cannot be None")
        else:
            now = dt

        offset = now.utcoffset()
        if offset is not None:
            minutes, _ = divmod(int(offset.total_seconds()), 60)
            hours, minutes = divmod(minutes, 60)
            return f"{hours:+03d}:{minutes:02d}"
        else:
            return "+00:00"

    @timezone.command(name="info")
    @app_commands.describe(timezone="The timezone to get info about.")
    async def timezone_info(self, ctx: AluContext, *, timezone: TimeZone):
        """Retrieves info about a timezone."""

        embed = discord.Embed(title=timezone.label, colour=discord.Colour.blurple())
        dt = discord.utils.utcnow().astimezone(tz=zoneinfo.ZoneInfo(key=timezone.key))
        embed.add_field(name="Current Time", value=dt.strftime("%Y-%m-%d %I:%M %p"))
        embed.add_field(name="UTC Offset", value=self.get_utc_offset_string(dt=dt))
        embed.add_field(name="IANA Database Alias", value=timezone.key)

        await ctx.send(embed=embed)

    @timezone_set.autocomplete("timezone")
    @timezone_info.autocomplete("timezone")
    async def timezone_set_autocomplete(
        self, _ntr: discord.Interaction, argument: str
    ) -> list[app_commands.Choice[str]]:
        if not argument:
            return self._default_timezones
        matches = self.find_timezones(argument)
        return [tz.to_choice() for tz in matches[:25]]

    @timezone.command(name="get")
    @app_commands.describe(user="The member to get the timezone of. Defaults to yourself.")
    async def timezone_get(self, ctx: AluContext, *, user: discord.User = commands.Author):
        """Shows the timezone of a user."""
        self_query = user.id == ctx.author.id
        tz = await self.bot.get_timezone(user.id)
        if tz is None:
            return await ctx.send(f"{user} has not set their timezone.")

        time = discord.utils.utcnow().astimezone(zoneinfo.ZoneInfo(tz)).strftime("%Y-%m-%d %I:%M %p")
        if self_query:
            msg = await ctx.send(f"Your timezone is {tz!r}. The current time is {time}.")
            await asyncio.sleep(5.0)
            await msg.edit(content=f"Your current time is {time}.")
        else:
            await ctx.send(f"The current time for {user} is {time}.")

    @timezone.command(name="clear")
    async def timezone_clear(self, ctx: AluContext):
        """Clears your timezone."""
        await ctx.pool.execute("UPDATE user_settings SET timezone = NULL WHERE id=$1", ctx.author.id)
        self.bot.get_timezone.invalidate(self, ctx.author.id)
        await ctx.send("Your timezone has been cleared.", ephemeral=True)


async def setup(bot: AluBot):
    await bot.add_cog(UserSettingsCog(bot))
