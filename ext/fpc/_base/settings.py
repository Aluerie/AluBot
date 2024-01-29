from __future__ import annotations

import abc
from typing import TYPE_CHECKING, Any, Awaitable, Callable, Mapping, Optional, Self, TypedDict

import asyncpg
import discord
from discord import app_commands
from discord.ext import commands

from utils import AluGuildContext, const, errors, formats, fuzzy
from utils.cache import KeysCache

from . import FPCCog, views

if TYPE_CHECKING:
    from bot import AluBot

    # currently
    # * `steam_id` are `int`
    # * `summoner_id` are `str`
    type AccountIDType = int | str

    class SetupPlayerQueryRow(TypedDict):
        player_id: int
        display_name: str

    class PlayerListQueryRow(TypedDict):
        display_name: str
        twitch_id: str

    class SetupMiscQueryRow(TypedDict):
        enabled: bool
        spoil: bool
        twitch_live_only: bool


__all__ = (
    "BaseSettings",
    "Account",
)


class Account(abc.ABC):
    if TYPE_CHECKING:
        player_display_name: str
        twitch_id: Optional[int]
        profile_image: str

    def __init__(self, player_name: str, is_twitch_streamer: bool = True) -> None:
        self.player_name: str = player_name
        self.is_twitch_streamer: bool = is_twitch_streamer

    @abc.abstractmethod
    async def set_game_specific_attrs(self, bot: AluBot, flags: commands.FlagConverter):
        """Set game specific attributes."""

    @abc.abstractmethod
    def to_pseudo_record(self) -> dict[str, Any]:
        """Return dict mirroring what should be put into the database."""

    @property
    @abc.abstractmethod
    def hint_database_add_command_args(self) -> str:
        """Formatted args for `/database {game} add` command for easy copy&paste"""

    @staticmethod
    @abc.abstractmethod
    def static_account_name_with_links(**kwargs: Any) -> str:
        """Static method for `account_string_with_links` so we can get it
        when we don't need to initiate a full account
        """

    @property
    @abc.abstractmethod
    def account_string_with_links(self) -> str:
        """Account string with links"""

    # todo: i dont like it, why there is two things of those
    # todo: maybe we need to do like Player Account and then PlayerAccount class?
    @staticmethod
    @abc.abstractmethod
    def static_account_string(**kwargs: Any) -> str:
        """Static method for `account_string` so we can get it
        when we don't need to initiate a full account
        """

    @property
    @abc.abstractmethod
    def account_string(self) -> str:
        """Account string"""

    async def set_base_attrs(self, bot: AluBot):
        if self.is_twitch_streamer:
            twitch_user = next(iter(await bot.twitch.fetch_users(names=[self.player_name])), None)
            if not twitch_user:
                raise errors.BadArgument(
                    f"Error checking twitch user `{self.player_name}`.\n User either does not exist or is banned."
                )
            display_name, twitch_id, profile_image = twitch_user.display_name, twitch_user.id, twitch_user.profile_image
        else:
            display_name, twitch_id, profile_image = self.player_name, None, discord.utils.MISSING

        self.player_display_name = display_name
        self.twitch_id = twitch_id
        self.profile_image = profile_image

    @classmethod
    async def create(cls, bot: AluBot, flags: commands.FlagConverter) -> Self:
        name: str = getattr(flags, "name")
        try:
            is_twitch_streamer: bool = getattr(flags, "twitch")
        except AttributeError:
            # doesn't have .twitch attribute, thus we assume it's a streamer-only
            # since the feature will prioritize twitch-streamers in its development.
            is_twitch_streamer = True

        self = cls(name, is_twitch_streamer)
        await self.set_base_attrs(bot)
        await self.set_game_specific_attrs(bot, flags)
        return self

    @staticmethod
    def static_player_embed_name(display_name: str, is_twitch_streamer: bool):
        if is_twitch_streamer:
            return f"\N{BLACK CIRCLE} [{display_name}](https://www.twitch.tv/{display_name})"
        else:
            return f"\N{BLACK CIRCLE} {display_name}"

    @property
    def player_embed_name(self) -> str:
        return self.static_player_embed_name(self.player_display_name, self.is_twitch_streamer)


class BaseSettings(FPCCog):
    """Base class for cogs representing FPC (Favourite Player+Character) feature
    for different games:

    * Dota 2
    * League of Legends
    * and probably more to come.

    Since many base features can be generalized -
    here is the base class containing base methods.

    Attributes
    -----------
    prefix: str
        Code-name for the game, i.e. `lol`, `dota`.
        Important notes.
        1) It's assumed that SQL tables related to FPC are named accordingly to this prefix.
        For example, Game accounts table should be named f'{self.prefix}_accounts'`,
        i.e. `dota_accounts`.
        2) name for slash command is assumed to be starting with `/{self.prefix} as well,
        i.e. `/dota player setup`
    colour: discord.Colour
        The colour that will be used for all embeds related to this game notifications.
    game_display_name: str
        Display name of the game. This is used in response strings mentioning the game for user-end eyes.
    game_icon_url: str
        Display icon for the game. For example, this is used in footnote icons mentioning the game.
    character_singular_word: str
        Gathering word to describe the characters for the game,
        i.e. "hero" for Dota 2, "champion" for LoL, "agent" for Valorant.
    character_plural_word: str
        A plural form for the `character_singular_word` above.
        Sometimes adding -s is not enough.
    extra_account_info_columns: List[str]
        Extra column-names for columns in "{self.prefix}_accounts" table.
        For example, you need `platform` as region name in League of Legends in order to find the account.
    character_name_by_id: Callable[[int], Awaitable[str]]
        Function that gets character name by its id, i.e. 1 -> 'Anti-Mage'.
    character_id_by_name: Callable[[str], Awaitable[int]]
        Function that gets character id by its name, i.e. 'Anti-Mage' -> 1.
    get_character_name_by_id_cache: Callable[[], Awaitable[dict[int, str]]]
        Lambda function that gets "name_by_id" sub-dict from the game related cache.
    """

    def __init__(
        self,
        bot: AluBot,
        *args,
        prefix: str,
        colour: discord.Colour,
        game_display_name: str,
        game_icon_url: str,
        character_singular_word: str,
        character_plural_word: str,
        account_cls: type[Account],
        account_typed_dict_cls: type,
        character_cache: KeysCache,
        **kwargs,
    ) -> None:
        super().__init__(bot, *args, **kwargs)

        # game attrs
        self.prefix: str = prefix
        self.colour: discord.Colour = colour
        self.game_display_name: str = game_display_name
        self.game_icon_url: str = game_icon_url
        self.character_singular_word: str = character_singular_word
        self.character_plural_word: str = character_plural_word

        # account attrs
        self.account_cls: type[Account] = account_cls
        self.account_table_columns: list[str] = list(account_typed_dict_cls.__annotations__.keys())
        self.account_id_column: str = self.account_table_columns[0]

        # cache attrs
        self.character_name_by_id: Callable[[int], Awaitable[str]] = getattr(character_cache, "name_by_id")
        self.character_id_by_name: Callable[[str], Awaitable[int]] = getattr(character_cache, "id_by_name")
        self.character_name_by_id_cache: Callable[[], Awaitable[dict[int, str]]] = lambda: character_cache.get_cache(
            "name_by_id"
        )

    # fpc database management related functions ########################################################################

    async def check_if_account_already_in_database(self, account_id: AccountIDType) -> None:
        query = f"""
            SELECT display_name
            FROM {self.prefix}_players
            WHERE player_id = (
                SELECT player_id
                FROM {self.prefix}_accounts
                WHERE {self.account_id_column}=$1 
            )
        """
        display_name: Optional[str] = await self.bot.pool.fetchval(query, account_id)
        if display_name:
            raise errors.BadArgument(
                "This account is already in the database.\n"
                f"It is marked as {display_name}'s account.\n\n"
                f"You might have wanted to use `/{self.prefix} setup players` and chose this player from here."
            )

    async def request_player(self, ctx: AluGuildContext, flags: commands.FlagConverter) -> None:
        """Base function for `/{game} request player` command

        This allows people to request player accounts to be added into the bot's FPC database.
        """

        await ctx.typing()
        account = await self.account_cls.create(self.bot, flags)
        await self.check_if_account_already_in_database(account_id=getattr(account, self.account_id_column))

        confirm_embed = (
            discord.Embed(
                colour=self.colour,
                title="Confirmation Prompt",
                description=(
                    "Are you sure you want to request this streamer steam account to be added into the database?\n"
                    "This information will be sent to Aluerie. Please, double check before confirming."
                ),
            )
            .set_author(name="Request to add an account into the database")
            .set_thumbnail(url=account.profile_image)
            .add_field(name=account.player_embed_name, value=account.account_string_with_links)
            .set_footer(text=self.game_display_name, icon_url=self.game_icon_url)
        )

        if not await self.bot.disambiguator.confirm(ctx, embed=confirm_embed):
            return

        response_embed = discord.Embed(
            colour=self.colour,
            title="Successfully made a request to add the account into the database",
        ).add_field(name=account.player_embed_name, value=account.account_string_with_links)
        await ctx.reply(embed=response_embed)

        logs_embed = confirm_embed.copy()
        logs_embed.title = ""
        logs_embed.description = ""
        logs_embed.set_author(name=ctx.user, icon_url=ctx.user.display_avatar.url)
        logs_embed.add_field(
            name="Command", value=f"/database {self.prefix} add {account.hint_database_add_command_args}"
        )
        await self.hideout.global_logs.send(embed=logs_embed)

    async def database_add(self, ctx: AluGuildContext, flags: commands.FlagConverter) -> None:
        """Base function for `/database {game} add` command

        This allows bot owner to add player accounts into the bot's FPC database.
        """

        await ctx.typing()
        account = await self.account_cls.create(self.bot, flags)
        await self.check_if_account_already_in_database(account_id=getattr(account, self.account_id_column))

        query = f"""
            INSERT INTO {self.prefix}_players 
            (display_name, twitch_id)
            VALUES ($1, $2)
            ON CONFLICT (display_name) DO NOTHING
            RETURNING player_id
        """
        player_id: int = await ctx.pool.fetchval(query, account.player_display_name, account.twitch_id)

        database_dict = account.to_pseudo_record()
        database_dict["player_id"] = player_id
        dollars = ", ".join(f"${i}" for i in range(1, len(database_dict.keys()) + 1))
        columns = ", ".join(database_dict.keys())
        query = f"INSERT INTO {self.prefix}_accounts ({columns}) VALUES ({dollars})"
        await ctx.pool.execute(query, *database_dict.values())

        response_embed = (
            discord.Embed(colour=self.colour, title=f"Successfully added the account to the database")
            .add_field(name=account.player_embed_name, value=account.account_string_with_links)
            .set_author(name=self.game_display_name, icon_url=self.game_icon_url)
            .set_thumbnail(url=account.profile_image)
        )
        await ctx.reply(embed=response_embed)

        logs_embed = response_embed.copy()
        logs_embed.set_author(name=ctx.user, icon_url=ctx.user.display_avatar.url)
        await self.hideout.global_logs.send(embed=logs_embed)

    async def database_remove(self, ctx: AluGuildContext, player_name: str):
        """Base function for `/database {game} remove` command

        This allows bot owner to remove player accounts from the bot's FPC database.
        """

        await ctx.typing()

        player_id, display_name = await self.get_player_tuple(player_name)

        query = f"SELECT * FROM {self.prefix}_accounts WHERE player_id = $1"
        rows: list[dict] = await ctx.pool.fetch(query, player_id)
        account_ids_names: Mapping[AccountIDType, str] = {
            row[self.account_id_column]: self.account_cls.static_account_string(**row) for row in rows
        }

        view = views.DatabaseRemoveView(
            ctx.author.id, self, player_id, display_name, account_ids_names, self.account_id_column
        )
        await ctx.reply(view=view)

    # fpc settings related functions ###################################################################################

    async def setup_channel(self, ctx: AluGuildContext):
        """Base function for `/{game} setup channel` command.

        This gives
        * Embed with current state of channel setup
        * View to select a new channel for FPC notifications
        """

        await ctx.typing()
        # Get channel
        query = f"SELECT channel_id FROM {self.prefix}_settings WHERE guild_id=$1"
        channel_id: Optional[int] = await self.bot.pool.fetchval(query, ctx.guild.id)

        if channel_id:
            channel = self.bot.get_channel(channel_id) or await self.bot.fetch_channel(channel_id)
            if not isinstance(channel, discord.TextChannel):
                # todo: erm not sure about this
                channel = None
        else:
            channel = None

        if channel:
            desc = f"{self.game_display_name} FPC Notifications Channel is currently to {channel.mention}."
        else:
            desc = f"{self.game_display_name} FPC Notifications Channel is currently not set."

        embed = discord.Embed(
            colour=self.colour,
            title="FPC (Favourite Player+Character) Channel Setup",
            description=desc,
        ).set_footer(text=self.game_display_name, icon_url=self.game_icon_url)
        channel_setup_view = views.FPCSetupChannelView(self, ctx.author.id)
        await ctx.reply(embed=embed, view=channel_setup_view)

    async def is_fpc_channel_set(self, ctx: AluGuildContext) -> None:
        """Checks if the current guild has fpc channel set.

        It's somewhat needed because without it functions like `setup_characters`, `setup_players`
        will fail with ForeignKeyViolationError since there is nothing in `{self.prefix}_settings` table.
        """

        query = f"SELECT channel_id FROM {self.prefix}_settings WHERE guild_id=$1"
        channel_id: Optional[int] = await ctx.pool.fetchval(query, ctx.guild.id)
        if not channel_id:
            raise errors.ErroneousUsage(
                "I'm sorry! You cannot use this command without setting up "
                f"{self.game_display_name} FPC (Favourite Player+Character) channel first. "
                f"Please, use `/{self.prefix} setup channel` to assign it."
            )

    async def setup_misc(self, ctx: AluGuildContext):
        """Base function for `/{game} setup miscellaneous` command.

        This gives
        * Embed with current state of FPC settings
        * Buttons to toggle state of those settings
        * Button to remove the whole data and stop getting FPC notifications
        """
        await ctx.typing()
        await self.is_fpc_channel_set(ctx)

        query = f"SELECT enabled, spoil, twitch_live_only FROM {self.prefix}_settings WHERE guild_id=$1"
        row: SetupMiscQueryRow = await ctx.pool.fetchrow(query, ctx.guild.id)

        def state(bool: bool) -> str:
            word = "`on`" if bool else "`off`"
            return f"{word} {formats.tick(bool)}"

        embed = (
            discord.Embed(
                colour=self.colour,
                title="FPC (Favourite Player+Character) Misc Settings Setup",
                description=(
                    "Below there is a list of settings with descriptions and their current state.\n"
                    "\N{BLACK CIRCLE} Each setting has correspondent toggle/use button.\n"
                    "\N{BLACK CIRCLE} After pressing `Toggle` button the embed will be "
                    "edited to showcase the current state of that setting."
                ),
            )
            # REMEMBER that the following fields should have ":" in their names
            # it's because view buttons hackily use split by : to edit the field name
            .add_field(
                name=f"\N{BLACK SQUARE FOR STOP} Receive Notifications Setting: {state(row['enabled'])}",
                value=(
                    "If you want manually temporarily disable FPC Notifications feature then use this toggle button. "
                    "Your data will be intact in case you want to enable receiving notifications again."
                ),
                inline=False,
            )
            .add_field(
                name=f"\N{MICROSCOPE} Show Post-Match Results Setting: {state(row['spoil'])}",
                value=(
                    "By default, the bot edits messages with post-game results to include stats like Win/Loss, "
                    "KDA. However, if you don't like such behavior - toggle this setting. "
                    "Note that the current ongoing match will still use old setting "
                    "(i.e. only next notification will use the updated value)."
                ),
                inline=False,
            )
            .add_field(
                name=f"\N{CLAPPER BOARD} Only Twitch Live Players Setting: {state(row['twitch_live_only'])}",
                value=(
                    "By default, the bot sends notifications no matter if a person is streaming or not at the moment. "
                    "However, if you only want to catch [twitch.tv](https://www.twitch.tv/) streamers playing your "
                    f"favourite {self.character_plural_word} live - toggle this setting."
                ),
            )
            .add_field(
                name="\N{WASTEBASKET} Delete Your Data and Stop Notifications",
                value=(
                    "In case you don't want to receive notifications anymore "
                    "and you want to erase all your FPC related data - use this button."
                ),
                inline=False,
            )
            .set_footer(text="Buttons below correspond embed fields above. Read them!")
        )
        view = views.FPCSetupMiscView(self, embed, author_id=ctx.author.id)
        await ctx.reply(embed=embed, view=view)

    # async def get_character_name_by_id_cache(self) -> dict[int, str]:
    #     raise NotImplementedError

    async def setup_characters(self, ctx: AluGuildContext):
        """Base function for `/{game} setup {characters}` command.

        This gives
        * View of buttons to add/remove characters to/from person favourite characters
        """

        await ctx.typing()
        await self.is_fpc_channel_set(ctx)

        name_by_id_cache = await self.character_name_by_id_cache()
        name_by_id_cache.pop(0, None)  # 0 id is special

        character_tuples: list[tuple[int, str]] = [
            (character_id, character_name) for character_id, character_name in name_by_id_cache.items()
        ]
        character_tuples.sort(key=lambda x: x[1])

        paginator = views.FPCSetupCharactersPaginator(ctx, character_tuples, self)
        await paginator.start()

    async def setup_players(self, ctx: AluGuildContext):
        """Base function for `/{game} setup players` command.

        This gives
        * View of buttons to add/remove players to/from person favourite players
        """

        await ctx.typing()
        await self.is_fpc_channel_set(ctx)

        query = f"SELECT player_id, display_name FROM {self.prefix}_players"
        rows: list[SetupPlayerQueryRow] = await ctx.pool.fetch(query)

        player_tuples: list[tuple[int, str]] = [(row["player_id"], row["display_name"]) for row in rows]
        player_tuples.sort(key=lambda x: x[1])

        paginator = views.FPCSetupPlayersPaginator(ctx, player_tuples, self)
        await paginator.start()

    # HIDEOUT ONLY RELATED FUNCTIONS ###################################################################################

    # The reason they are hideout-only is because I like using autocomplete for development.
    # But I think it might be confusing for end-user if I have several commands to add/remove players/characters.
    # One simple interactive view is enough for them granted they aren't supposed to change their preferences much.
    # I'm also just hesitant to completely delete all my previous work so let's at least leave one-name version
    # so we can put it as hybrid command, which is easier to maintain.

    async def hideout_add_worker(
        self,
        ctx: AluGuildContext,
        name: str,
        get_object_tuple: Callable[[str], Awaitable[tuple[int, str]]],
        column: str,
        object_word: str,
    ):
        """Worker function for commands /{game}-fpc {character}/player add

        Parameters
        ----------
        ctx : AluGuildContext
            Context
        name : str
            `name` from user input
        get_object_tuple: Callable[[str], Awaitable[tuple[int, str]]]
            function to get `object_id`, `object_display_name` tuple, where object is character/player
        column : str
            Suffix of the table, also column in the database like "character", "player"
            so it's "dota_favourite_characters" table with a column "character_id".
        object_word : str
            gathering word like "hero", "champion", "player"
        """

        await ctx.typing()
        object_id, object_display_name = await get_object_tuple(name)

        query = f"INSERT INTO {self.prefix}_favourite_{column}s (guild_id, {column}_id) VALUES ($1, $2)"
        try:
            await ctx.pool.execute(query, ctx.guild.id, object_id)
        except asyncpg.UniqueViolationError:
            raise errors.BadArgument(
                f"{object_word.capitalize()} {object_display_name} was already in your favourite list."
            )

        embed = discord.Embed(colour=self.colour).add_field(
            name=f"Succesfully added a {object_word} to your favourites.",
            value=object_display_name,
        )
        await ctx.reply(embed=embed)

    async def hideout_remove_worker(
        self,
        ctx: AluGuildContext,
        name: str,
        get_object_tuple: Callable[[str], Awaitable[tuple[int, str]]],
        column: str,
        object_word: str,
    ):
        """Worker function for commands /{game}-fpc {character}/player remove

        Parameters
        ----------
        ctx : AluGuildContext
            Context
        name : str
            `name` from user input
        get_object_tuple: Callable[[str], Awaitable[tuple[int, str]]]
            function to get `object_id`, `object_display_name` tuple, where object is character/player
        column : str
            Suffix of the table, also column in the database like "character", "player"
            so it's "dota_favourite_characters" table with a column "character_id".
        object_word : str
            gathering word like "hero", "champion", "player"
        """

        await ctx.typing()
        object_id, object_display_name = await get_object_tuple(name)

        query = f"DELETE FROM {self.prefix}_favourite_{column}s WHERE guild_id=$1 AND {column}_id=$2"
        result = await ctx.pool.execute(query, ctx.guild.id, object_id)
        if result == "DELETE 1":
            embed = discord.Embed(
                colour=self.colour,
                title=f"Succesfully removed a {object_word} from your favourites.",
                description=object_display_name,
            )
            await ctx.reply(embed=embed)
        elif result == "DELETE 0":
            raise errors.BadArgument(
                f"{object_word.capitalize()} {object_display_name} is already not in your favourite list."
            )
        else:
            raise errors.BadArgument("Unknown error.")

    async def get_player_tuple(self, player_name: str) -> tuple[int, str]:
        """Get player_id, display_name by their name from FPC database."""
        query = f"SELECT player_id, display_name FROM {self.prefix}_players WHERE lower(display_name)=$1"
        player_row: Optional[SetupPlayerQueryRow] = await self.bot.pool.fetchrow(query, player_name.lower())
        if player_row is None:
            raise errors.BadArgument(
                f"There is no player named {player_name} in the database. Please, double check everything."
            )
        return player_row["player_id"], player_row["display_name"]

    async def hideout_player_add(self, ctx: AluGuildContext, player_name: str):
        """Base function for `/{game}-fpc player add` Hideout-only command."""
        await self.hideout_add_worker(ctx, player_name, self.get_player_tuple, "player", "player")

    async def hideout_player_remove(self, ctx: AluGuildContext, player_name: str):
        """Base function for `/{game}-fpc player remove` Hideout-only command."""
        await self.hideout_remove_worker(ctx, player_name, self.get_player_tuple, "player", "player")

    async def get_character_tuple(self, character_name: str) -> tuple[int, str]:
        try:
            character_id = await self.character_id_by_name(character_name)
        except KeyError:
            raise errors.BadArgument(
                f"{self.character_singular_word.capitalize()} {character_name} does not exist. "
                "Please, double check everything."
            )
        character_display_name = await self.character_name_by_id(character_id)
        return character_id, character_display_name

    async def hideout_character_add(self, ctx: AluGuildContext, character_name: str):
        """Base function for `/{game}-fpc {character} add` Hideout-only command."""
        await self.hideout_add_worker(
            ctx, character_name, self.get_character_tuple, "character", self.character_singular_word
        )

    async def hideout_character_remove(self, ctx: AluGuildContext, character_name: str):
        """Base function for `/{game}-fpc {character} remove` Hideout-only command."""
        await self.hideout_remove_worker(
            ctx, character_name, self.get_character_tuple, "character", self.character_singular_word
        )

    async def get_player_list_embed(self, guild_id: int) -> discord.Embed:
        query = f"""
            SELECT display_name, twitch_id
            FROM {self.prefix}_players
            WHERE player_id=ANY(SELECT player_id FROM {self.prefix}_favourite_players WHERE guild_id=$1)
        """
        rows: list[PlayerListQueryRow] = await self.bot.pool.fetch(query, guild_id)
        favourite_player_names = (
            "\n".join([Account.static_player_embed_name(row["display_name"], bool(row["twitch_id"])) for row in rows])
            or "Empty list"
        )
        return discord.Embed(
            colour=self.colour,
            title="List of your favourite players",
            description=favourite_player_names,
        ).set_footer(text=self.game_display_name, icon_url=self.game_icon_url)

    async def hideout_player_list(self, ctx: AluGuildContext):
        """Base function for `/{game}-fpc player list` Hideout-only command."""
        await ctx.typing()
        embed = await self.get_player_list_embed(ctx.guild.id)
        await ctx.reply(embed=embed)

    async def get_character_list_embed(self, guild_id: int) -> discord.Embed:
        query = f"SELECT character_id FROM {self.prefix}_favourite_characters WHERE guild_id=$1"
        favourite_character_ids: list[int] = [
            character_id for character_id, in await self.bot.pool.fetch(query, guild_id)
        ]
        favourite_character_names = (
            "\n".join([await self.character_name_by_id(i) for i in favourite_character_ids]) or "Empty list"
        )
        return discord.Embed(
            colour=self.colour,
            title=f"List of your favourite {self.character_plural_word}",
            description=favourite_character_names,
        )

    async def hideout_character_list(self, ctx: AluGuildContext):
        """Base function for `/{game}-fpc {character} list` Hideout-only command."""

        await ctx.typing()
        embed = await self.get_character_list_embed(ctx.guild.id)
        await ctx.reply(embed=embed)

    async def hideout_player_add_remove_autocomplete(
        self, interaction: discord.Interaction[AluBot], current: str, *, mode_add_remove: bool
    ) -> list[app_commands.Choice[str]]:
        """Base function to define autocomplete for player_name in `/{game}-fpc player add/remove`."""

        assert interaction.guild

        query = f"""
            SELECT display_name 
            FROM {self.prefix}_players
            WHERE {'NOT' if mode_add_remove else ''} player_id=ANY(
                SELECT player_id FROM {self.prefix}_favourite_players WHERE guild_id=$1
            )
            ORDER BY similarity(display_name, $2) DESC
            LIMIT 6;
        """
        return [
            app_commands.Choice(name=name, value=name)
            for name, in await interaction.client.pool.fetch(query, interaction.guild.id, current)
        ]

    async def hideout_character_add_remove_autocomplete(
        self, interaction: discord.Interaction[AluBot], current: str, *, mode_add_remove: bool
    ) -> list[app_commands.Choice[str]]:
        """Base function to define autocomplete for character_name in `/{game}-fpc {character} add/remove`."""

        query = f"SELECT character_id FROM {self.prefix}_favourite_characters WHERE guild_id=$1"

        favourite_character_ids: list[int] = [
            character_id for character_id, in await interaction.client.pool.fetch(query, interaction.guild_id)
        ]

        name_by_id_cache = await self.character_name_by_id_cache()
        name_by_id_cache.pop(0, None)  # 0 id is special

        if mode_add_remove:
            # add
            choice_ids = [id for id in name_by_id_cache.keys() if id not in favourite_character_ids]
        else:
            # remove
            choice_ids = favourite_character_ids

        choice_names = [name_by_id_cache[id] for id in choice_ids]
        fuzzy_names = fuzzy.finder(current, choice_names)
        return [app_commands.Choice(name=name, value=name) for name in fuzzy_names[:7]]

    async def database_remove_autocomplete(
        self, interaction: discord.Interaction[AluBot], current: str
    ) -> list[app_commands.Choice[str]]:
        """Base function to define autocomplete for player_name in `/database {game} remove`."""

        query = f"""
            SELECT display_name 
            FROM {self.prefix}_players
            ORDER BY similarity(display_name, $1) DESC
            LIMIT 6;
        """
        return [
            app_commands.Choice(name=name, value=name) for name, in await interaction.client.pool.fetch(query, current)
        ]

    async def tutorial(self, ctx: AluGuildContext):
        """Base function for `/{game} tutorial` command."""
        await ctx.typing()

        file = discord.File("assets/images/local/fpc_tutorial.png")
        embed = (
            discord.Embed(
                colour=self.colour,
                title="FPC Notifications Setup Tutorial",
                description=(
                    "This embed will explain how to set up __F__avourite __P__layers + __C__haracters Notifications "
                    "(or shortly FPC Notifications). Just follow the easy intuitive steps below."
                ),
            )
            .set_footer(
                text=self.game_display_name,
                icon_url=self.game_icon_url,
            )
            .set_image(url=f"attachment://{file.filename}")
        )

        cmd_field_tuples: list[tuple[str, str]] = [
            (
                "setup channel",
                (
                    "First, we need to set up a channel for the bot to send Notifications in. "
                    "The bot will send notifications here and then edit those messages if needed."
                ),
            ),
            (
                "setup players",
                (
                    "Second, you need to choose your __F__avourite __P__layers from the list of already known players."
                    "Don't worry, if the list doesn't have a player you like "
                    "- you will possibly be able to request adding them."
                ),
            ),
            (
                f"setup {self.character_plural_word}",
                (
                    "Third, you need to choose your __F__avourite __C__haracters from the list of "
                    f"{self.game_display_name} {self.character_plural_word}."
                ),
            ),
            (
                "setup miscellaneous",
                (
                    "Forth, now you can fine-tune settings for the notifications. For example, turn off post-match "
                    "editing or make the bot only send twitch-live games. Also, here you can delete your whole data."
                ),
            ),
            (
                "request player",
                (
                    "Fifth, as section#2 says - you can request players to be added to the bot database. "
                    "Note, that due to high rate-limit nature of the bot - I only accept high mmr players/streamers."
                ),
            ),
        ]

        for count, (almost_qualified_name, field_value) in enumerate(cmd_field_tuples, start=1):
            app_command = self.bot.tree.get_app_command(f"{self.prefix} {almost_qualified_name}", guild=ctx.guild)
            if app_command:
                embed.add_field(
                    name=f"{const.DIGITS[count]}. Use {app_command.mention}", value=field_value, inline=False
                )
            else:
                raise RuntimeError("Somehow FPC related command is None.")

        await ctx.reply(embed=embed, file=file)
