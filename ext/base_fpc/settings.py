from __future__ import annotations

import abc
from dataclasses import dataclass
from typing import TYPE_CHECKING, Any, Generic, NamedTuple, Self, TypedDict, TypeVar, get_args, override

import asyncpg
import discord
from discord import app_commands

from bot import AluCog, AluLayoutView, AluView
from utils import const, errors, fmt, mimics, pages

if TYPE_CHECKING:
    from collections.abc import Mapping

    from bot import AluBot, AluInteraction

    from .storage import Character, CharacterStorage

    class AccountListButtonQueryRow(TypedDict):
        display_name: str
        twitch_id: str | None
        # fake, query row has more keys

    class AccountListButtonPlayerSortDict(TypedDict):
        name: str
        accounts: list[str]

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
    "BaseAccount",
    "BasePlayer",
    "BaseRequestPlayerArguments",
    "BaseSettingsCog",
)


@dataclass
class BaseRequestPlayerArguments:
    """Base Arguments for the following slash commands.

    * /dota request player
    * /database-dota-dev add

    Base in the sense that all games are going to have them so they can just subclass this dataclass.
    """

    name: str
    is_twitch_streamer: bool


@dataclass
class BaseAccount(abc.ABC):
    """Base DataClass for Account subclasses.

    Note, that subclasses of this should have their dataclass fields matching the respective columns in the database.
    Because some methods in here use `.__annotations__` and assume the match.
    """

    @classmethod
    @abc.abstractmethod
    async def create(cls, bot: AluBot, account_tuple: BaseRequestPlayerArguments) -> Self:
        """Create an instance of `Account` class."""

    @abc.abstractmethod
    def links(self) -> str:
        """Give links to see the account via various 3rd party services, i.e. Dotabuff, OPGG, etc."""

    @property
    @abc.abstractmethod
    def display_name(self) -> str:
        """Account's display name."""


def field_name(display_name: str, twitch_id: str | None) -> str:
    """Helper function to get field names for Players without a need to instantiate the whole GamePlayer object.

    Useful for database calls where we get `display_name` and `twitch_id` out of the box.
    """
    if twitch_id is not None:
        return f"\N{BLACK CIRCLE} [{display_name}](https://www.twitch.tv/{display_name})"
    return f"\N{BLACK CIRCLE} {display_name}"


AccountT = TypeVar("AccountT", bound=BaseAccount, covariant=True)


class IdentityPlayerTuple(NamedTuple):
    """Identity Tuple."""

    display_name: str
    twitch_id: str | None
    profile_image: str | None


class BasePlayer(abc.ABC, Generic[AccountT]):  # noqa: UP046 # we need covariance
    """Base class for other Game Player classes, i.e. DotaPlayer.

    Includes identity information as well as account information.
    """

    def __init__(self, identity: IdentityPlayerTuple, account: AccountT) -> None:
        self.display_name: str = identity.display_name
        self.twitch_id: str | None = identity.twitch_id
        self.avatar_url: str | None = identity.profile_image
        self.account: AccountT = account

    def __init_subclass__(cls: type[BasePlayer[AccountT]], **kwargs: Any) -> None:
        # https://stackoverflow.com/a/71720366/19217368
        cls.account_cls: type[AccountT] = get_args(cls.__orig_bases__[0])[0]  # type: ignore[reportAttributeAccessIssue]
        return super().__init_subclass__(**kwargs)

    @staticmethod
    async def get_identity_data(bot: AluBot, arguments: BaseRequestPlayerArguments) -> IdentityPlayerTuple:
        """Get player's identity data."""
        if arguments.is_twitch_streamer:
            twitch_user = next(iter(await bot.twitch.fetch_users(logins=[arguments.name])), None)
            if not twitch_user:
                msg = f"Error checking twitch user `{arguments.name}`.\n User either does not exist or is banned."
                raise errors.BadArgument(msg)
            return IdentityPlayerTuple(twitch_user.display_name, twitch_user.id, twitch_user.profile_image.url)
        return IdentityPlayerTuple(arguments.name, None, discord.utils.MISSING)

    @classmethod
    async def create(cls, bot: AluBot, arguments: BaseRequestPlayerArguments) -> Self:
        """Create."""
        return cls(
            identity=await cls.get_identity_data(bot, arguments),
            account=await cls.account_cls.create(bot, arguments),
        )

    def field_name(self) -> str:
        """A string to be put into embed fields to describe the player."""
        return field_name(self.display_name, self.twitch_id)

    @abc.abstractmethod
    def hint_database_add_command_arguments(self) -> str:
        """A hint for player related arguments for the `/database {game} add` commands.

        After subscribers use `request player` command,
        developers can quickly use this hint to add the player to the database.
        Should mirror `database {game} add` command arguments structure.
        """


class FPCView(AluView):
    """Base Class for FPC View classes."""

    def __init__(self, cog: BaseSettingsCog, *, author_id: int | None) -> None:
        super().__init__(author_id=author_id)
        self.cog: BaseSettingsCog = cog
        # overwrite the name
        self.name: str = f"{cog.game_display_name} FPC {self.__class__.__name__} Menu"

    @override
    async def on_timeout(self) -> None:
        await super().on_timeout()
        self.cog.setup_messages_cache.pop(self.message.id, None)


class SetupChannel(FPCView):
    """View for a command `/{game} setup channel`.

    This gives
    * Dropdown menu to select a new channel for notifications.
    """

    def __init__(self, cog: BaseSettingsCog, *, author_id: int | None, embed: discord.Embed) -> None:
        super().__init__(cog, author_id=author_id)
        self.embed: discord.Embed = embed

    @discord.ui.select(
        cls=discord.ui.ChannelSelect,
        channel_types=[discord.ChannelType.text, discord.ChannelType.news],
        placeholder="\N{BIRD} Select a new FPC notifications Channel",
        row=0,
    )
    async def set_channel(self, interaction: AluInteraction, select: discord.ui.ChannelSelect[Self]) -> None:
        """Set channel to receive FPC notifications."""
        chosen_channel = select.values[0]  # doesn't have all data thus we need to resolve
        channel = chosen_channel.resolve() or await chosen_channel.fetch()

        if not isinstance(channel, discord.TextChannel):
            msg = (
                f"You can't select a channel of this type for {self.cog.game_display_name} FPC channel."
                "Please, select normal text channel."
            )
            raise errors.ErroneousUsage(msg)

        if not channel.permissions_for(channel.guild.me).send_messages:
            msg = (
                "I do not have permission to `send_messages` in that channel. "
                "Please, select a channel where I can do that so I'm able to send notifications."
            )
            raise errors.ErroneousUsage(msg)

        if not channel.permissions_for(channel.guild.me).manage_webhooks:
            msg = (
                "I do not have permission to `manage_webhooks` in that channel. "
                "Please, grant me that permission so I can send cool messages using them."
            )
            raise errors.ErroneousUsage(msg)

        mimic = mimics.Mimic.from_channel(self.cog.bot, channel)
        webhook = await mimic.get_or_create_webhook()

        query = f"""
            INSERT INTO {self.cog.prefix}_settings (guild_id, guild_name, channel_id)
            VALUES ($1, $2, $3)
            ON CONFLICT (guild_id) DO UPDATE
                SET channel_id=$3;
        """
        await interaction.client.pool.execute(query, channel.guild.id, channel.guild.name, channel.id)

        self.embed.set_field_at(
            0, name=f"Channel {fmt.tick(bool(channel))}", value=channel.mention if channel else "Not set"
        )
        self.embed.set_field_at(
            1, name=f"Webhook {fmt.tick(bool(webhook))}", value="Properly Set" if webhook else "Not set"
        )
        await interaction.response.edit_message(embed=self.embed)


class DeleteDataButton(discord.ui.Button["SetupMiscView"]):
    def __init__(self, cog: BaseSettingsCog) -> None:
        super().__init__(emoji="\N{WARNING SIGN}", label="Delete Your Data", style=discord.ButtonStyle.red)
        self.cog: BaseSettingsCog = cog

    @override
    async def callback(self, interaction: AluInteraction) -> None:
        """Delete all data, stop all notifications and turn off everything related to FPC."""
        # Tell the type checker that a view is attached already
        assert self.view is not None

        # Confirmation
        confirm_embed = (
            discord.Embed(
                color=self.cog.color,
                title="Confirmation Prompt",
                description=(
                    f"Are you sure you want to stop {self.cog.game_display_name} FPC Notifications "
                    "and delete your data?"
                ),
            )
            .set_author(name=self.cog.game_display_name, icon_url=self.cog.game_icon_url)
            .add_field(
                name="The data that will be deleted",
                value=(
                    f"\N{BLACK CIRCLE} your favorite players data\n"
                    f"\N{BLACK CIRCLE} your favorite {self.cog.character_plural} data\n"
                    f"\N{BLACK CIRCLE} your {self.cog.character_plural} FPC Notifications channel data."
                ),
            )
        )

        if not await interaction.client.disambiguator.confirm(interaction, confirm_embed):
            return

        # Disable all the active setup views so the user can't mess up the database
        # code is copy of usual `on_timeout` habit
        for message_id in list(self.cog.setup_messages_cache.keys()):
            view = self.cog.setup_messages_cache.pop(message_id)
            for item in view.children:
                # item in self.children is Select/Button which have ``.disable`` but typehinted as Item
                item.disabled = True  # type:ignore[reportAttributeAccessIssue]
            await view.message.edit(view=view)

        # Disable the Channel
        query = f"DELETE FROM {self.cog.prefix}_settings WHERE guild_id=$1"
        await interaction.client.pool.execute(query, interaction.guild_id)

        response_embed = discord.Embed(
            color=discord.Color.green(),
            title="FPC (Favorite Player+Character) channel removed.",
            description="Notifications will not be sent anymore. Your data was deleted as well.",
        ).set_author(name=self.cog.game_display_name, icon_url=self.cog.game_icon_url)
        await interaction.followup.send(embed=response_embed)


class MiscSettingsToggleButton(discord.ui.Button["SetupMiscView"]):
    def __init__(self, cog: BaseSettingsCog, *, setting: str, initial_value: bool) -> None:
        super().__init__(label="\N{BELL}", style=discord.ButtonStyle.gray)
        self.cog: BaseSettingsCog = cog
        self.setting: str = setting
        self.value: bool = initial_value
        self.update_button()

    def update_button(self) -> None:
        if self.value:
            self.emoji = "\N{WHITE HEAVY CHECK MARK}"
            self.label = " Enabled"
        else:
            self.emoji = "\N{CROSS MARK}"
            self.label = "Disabled"

    async def toggle_worker(self, interaction: AluInteraction) -> None:
        """Helper function to toggle boolean settings for the subscriber's guild."""
        query = f"""
            UPDATE {self.cog.prefix}_settings
            SET {self.setting}=not({self.setting})
            WHERE guild_id = $1
            RETURNING {self.setting}
        """
        self.value: bool = await interaction.client.pool.fetchval(query, interaction.guild_id)

    @override
    async def callback(self, interaction: AluInteraction) -> None:
        await self.toggle_worker(interaction)
        self.update_button()
        await interaction.response.edit_message(view=self.view)


class SetupMiscView(AluLayoutView):
    """View for a command `/{game} setup misc`.

    This gives
    * Button to disable/enable notifications for a time being
    * Button to disable/enable spoil-ing post-match results
    * Button to delete user's FPC data from the database
    """

    def __init__(self, cog: BaseSettingsCog, *, author_id: int, settings: SetupMiscQueryRow) -> None:
        super().__init__(author_id=author_id)
        self.cog: BaseSettingsCog = cog
        self.settings: SetupMiscQueryRow = settings

        container = discord.ui.Container(accent_color=cog.color)

        # Header
        header = discord.ui.TextDisplay(
            content=(
                "## FPC (Favorite Player+Character) Misc Settings Setup\n"
                "Below there is a list of settings with descriptions and their current state.\n"
                "\N{BLACK CIRCLE} Each setting has correspondent toggle/use button.\n"
                "\N{BLACK CIRCLE} After pressing `Toggle` button the embed will be "
                "edited to showcase the current state of that setting."
            )
        )
        container.add_item(header)
        container.add_item(discord.ui.Separator(spacing=discord.SeparatorSpacing.large))

        # Receive Notifications = on/off
        container.add_item(
            discord.ui.Section(
                discord.ui.TextDisplay(
                    "### \N{BLACK SQUARE FOR STOP} Receive Notifications\n"
                    "If you want to manually temporarily disable FPC Notifications feature then use this toggle "
                    "button. Your data will be intact in case you want to enable receiving notifications again."
                ),
                accessory=MiscSettingsToggleButton(self.cog, setting="enabled", initial_value=self.settings["enabled"]),
            )
        )
        container.add_item(discord.ui.Separator(spacing=discord.SeparatorSpacing.large))

        # Show Post-Match Results = on/off
        container.add_item(
            discord.ui.Section(
                discord.ui.TextDisplay(
                    "### \N{MICROSCOPE} Show Post-Match Results\n"
                    "By default, the bot edits messages with post-game results to include stats like Win/Loss, "
                    "KDA. However, if you don't like such behavior - toggle this setting. "
                    "Note that the current ongoing match will still use old setting "
                    "(i.e. only next notification will use the updated value)."
                ),
                accessory=MiscSettingsToggleButton(self.cog, setting="spoil", initial_value=self.settings["spoil"]),
            )
        )
        container.add_item(discord.ui.Separator(spacing=discord.SeparatorSpacing.large))

        # Only Twitch Live = on/off
        container.add_item(
            discord.ui.Section(
                discord.ui.TextDisplay(
                    "### \N{CLAPPER BOARD} Only Twitch Live\n"
                    "By default, the bot sends notifications no matter if a person is streaming or not at the moment. "
                    "However, if you want to catch [twitch.tv](https://www.twitch.tv/) streamers only when they are "
                    "playing your favorite characters live - toggle this setting."
                ),
                accessory=MiscSettingsToggleButton(
                    self.cog, setting="twitch_live_only", initial_value=self.settings["twitch_live_only"]
                ),
            )
        )
        container.add_item(discord.ui.Separator(spacing=discord.SeparatorSpacing.large))

        # Delete Your Data = on/off
        container.add_item(
            discord.ui.Section(
                discord.ui.TextDisplay(
                    "### \N{WASTEBASKET} Delete Your Data and Stop Notifications\n"
                    "In case you don't want to receive notifications anymore "
                    "and you want to erase all your FPC related data - use this button."
                ),
                accessory=DeleteDataButton(
                    self.cog,
                ),
            )
        )

        # the final step
        self.add_item(container)


class SetupPlayersPaginator(pages.Paginator):
    """A Paginator for `/{game} setup players` command.

    This gives:
    * pagination menu
    * list of favorite players button
    * buttons to mark/demark player as favorite
    * button to view all accounts for presented embed
    """

    def __init__(self, interaction: AluInteraction, player_tuples: list[tuple[int, str]], cog: BaseSettingsCog) -> None:
        super().__init__(interaction, entries=player_tuples, per_page=20)
        self.cog: BaseSettingsCog = cog

    @override
    async def on_timeout(self) -> None:  # TODO: do it properly, via combining FPCView and pages.Paginator as a class.
        await super().on_timeout()
        self.cog.setup_messages_cache.pop(self.message.id, None)

    @override
    async def format_page(self, entries: list[tuple[int, str]]) -> discord.Embed:
        """Create a page for `/{game} setup {characters/players}` command.

        This gives
         * Embed with explanation text
         * Buttons to add/remove characters to/from favorite list.

        Parameters
        ----------
        entries:
            List of (player_id, player_display_name) tuples,
            for example: [(1, "gosu"), (2, "Quantum"), ...].

        """
        # unfortunately we have to fetch favorites each format page
        # in case they are bad acting with using both slash commands
        # or several menus

        query = f"SELECT player_id FROM {self.cog.prefix}_favorite_players WHERE guild_id=$1"
        assert self.interaction.guild
        favorite_ids: list[int] = [r for (r,) in await self.bot.pool.fetch(query, self.interaction.guild.id)]

        embed = (
            discord.Embed(
                color=self.cog.color,
                title=f"Your favorite {self.cog.game_display_name} {self.cog.character_plural} list interactive setup",
                description=f"Menu below represents all {self.cog.character_plural} from {self.cog.game_display_name}.",
            )
            .add_field(
                name="\N{LARGE GREEN SQUARE}/\N{BLACK LARGE SQUARE} Buttons",
                value=(
                    f"Press those buttons to mark/demark a a {self.cog.character_plural} as your favorite.\n"
                    "Button's colour shows if it's currently chosen as your favorite. "
                    "(\N{LARGE GREEN SQUARE} - yes, \N{BLACK LARGE SQUARE} - no)\n"
                ),
                inline=False,
            )
            .add_field(
                name=f"{self.favorite_players.emoji} Your favorite {self.cog.character_plural} list Button",
                value="Show your favorite players list.",
                inline=False,
            )
            .add_field(
                name="\N{PENCIL} List of accounts of players shown on the page",
                value="Show list of accounts with links to their profiles and extra information.",
                inline=False,
            )
        )

        self.clear_items()
        self.fill_items()
        for item in [self.favorite_players, self.previous_page, self.index, self.next_page, self.account_list]:
            self.add_item(item)

        for player_id, player_display_name in entries:
            self.add_item(
                AddRemoveButton(
                    player_display_name,
                    player_id,
                    is_favorite=player_id in favorite_ids,
                    table=f"{self.cog.prefix}_favorite_players",
                    column="player_id",
                    menu=self,
                ),
            )

        return embed

    @discord.ui.button(emoji="\N{PAGE WITH CURL}", label="Favorites", style=discord.ButtonStyle.blurple)
    async def favorite_players(self, interaction: AluInteraction, _: discord.ui.Button[Self]) -> None:
        """Show favorite object list."""
        assert interaction.guild
        embed = await self.cog.get_player_list_embed(interaction.guild.id)
        await interaction.response.send_message(embed=embed, ephemeral=True)

    @discord.ui.button(emoji="\N{PENCIL}", label="Accounts", style=discord.ButtonStyle.blurple)
    async def account_list(self, interaction: AluInteraction, _: discord.ui.Button[Self]) -> None:
        """5th Button to Show account list for `/{game} setup players` command's view."""
        assert interaction.guild

        columns = "display_name, twitch_id, " + ", ".join(self.cog.account_columns)

        query = f"""
            SELECT {columns}
            FROM {self.cog.prefix}_players p
            JOIN {self.cog.prefix}_accounts a
            ON p.player_id = a.player_id
            ORDER BY display_name
        """
        rows: list[AccountListButtonQueryRow] = await interaction.client.pool.fetch(query) or []

        player_dict: dict[str, AccountListButtonPlayerSortDict] = {}
        for row in rows:
            if row["display_name"] not in player_dict:
                player_dict[row["display_name"]] = {
                    "name": field_name(row["display_name"], row["twitch_id"]),
                    "accounts": [],
                }

            account_kwargs = {column: row[column] for column in self.cog.account_columns}
            account_temp = self.cog.player_cls.account_cls(**account_kwargs)
            player_dict[row["display_name"]]["accounts"].append(account_temp.display_name)

        embed = discord.Embed(
            color=self.cog.color,
            title="List of accounts for players shown above.",
            description="\n".join(
                f"{player['name']}\n{chr(10).join(player['accounts'])}" for player in player_dict.values()
            ),
        ).set_footer(
            text=f"to request a new account/player to be added - use `/{self.cog.prefix} request player` command",
            icon_url=self.cog.game_icon_url,
        )

        await interaction.response.send_message(embed=embed, ephemeral=True)


class SetupCharactersPaginator(pages.Paginator):
    """A Paginator for `/{game} setup characters` command.

    This gives:
    * pagination menu
    * list of favorite characters button
    * buttons to mark/demark character as favorite
    """

    def __init__(self, interaction: AluInteraction, characters: list[Character], cog: BaseSettingsCog) -> None:
        super().__init__(interaction, entries=characters, per_page=20)
        self.cog: BaseSettingsCog = cog

    @override
    async def on_timeout(self) -> None:  # TODO: do it properly, via combining FPCView and pages.Paginator as a class.
        await super().on_timeout()
        self.cog.setup_messages_cache.pop(self.message.id, None)

    @discord.ui.button(emoji="\N{PAGE WITH CURL}", label="Favorites", style=discord.ButtonStyle.blurple)
    async def favorite_characters(self, interaction: AluInteraction, _: discord.ui.Button[Self]) -> None:
        """Show favorite object list."""
        assert interaction.guild
        embed = await self.cog.get_character_list_embed(interaction.guild.id)
        await interaction.response.send_message(embed=embed, ephemeral=True)

    @override
    async def format_page(self, entries: list[Character]) -> discord.Embed:
        """Create a page for `/{game} setup {characters}` command.

        This gives
        * Embed with explanation text
        * Buttons to add/remove characters to/from favorite list.

        Parameters
        ----------
        entries: list[Character]
            List of characters

        """
        # unfortunately we have to fetch favorites each format page
        # in case they are bad acting with using both slash commands
        # or several menus

        query = f"SELECT character_id FROM {self.cog.prefix}_favorite_characters WHERE guild_id=$1"
        assert self.interaction.guild
        favorite_ids: list[int] = [r for (r,) in await self.bot.pool.fetch(query, self.interaction.guild.id)]

        embed = (
            discord.Embed(
                color=self.cog.color,
                title=f"Your favorite {self.cog.game_display_name} {self.cog.character_plural} list interactive setup",
                description=f"Menu below represents all {self.cog.character_plural} from {self.cog.game_display_name}.",
            )
            .add_field(
                name="\N{LARGE GREEN SQUARE}/\N{BLACK LARGE SQUARE} Buttons",
                value=(
                    f"Press those buttons to mark/demark a a {self.cog.character_singular} as your favorite.\n"
                    "Button's colour shows if it's currently chosen as your favorite. "
                    "(\N{LARGE GREEN SQUARE} - yes, \N{BLACK LARGE SQUARE} - no)\n"
                ),
                inline=False,
            )
            .add_field(
                name=f"{self.favorite_characters.emoji} Your favorite {self.cog.character_plural} list Button",
                value=f"Show your favorite {self.cog.character_plural} list.",
                inline=False,
            )
        )

        self.clear_items()
        for item in [self.favorite_characters, self.previous_page, self.index, self.next_page, self.last_page]:
            self.add_item(item)

        for character in entries:
            self.add_item(
                AddRemoveButton(
                    character.display_name,
                    character.id,
                    is_favorite=character.id in favorite_ids,
                    emoji=character.emote,
                    table=f"{self.cog.prefix}_favorite_characters",
                    column="character_id",
                    menu=self,
                ),
            )

        return embed


class AddRemoveButton(discord.ui.Button[SetupCharactersPaginator | SetupCharactersPaginator]):
    """Green/Black Buttons to Remove from/Add to favorite list.

    Used for `/{game} setup players/{characters}` command's view.
    """

    def __init__(
        self,
        label: str,
        object_id: int,
        *,
        is_favorite: bool,
        table: str,
        column: str,
        menu: SetupCharactersPaginator | SetupPlayersPaginator,
        emoji: str | None = None,
    ) -> None:
        super().__init__(
            emoji=emoji,
            style=discord.ButtonStyle.green if is_favorite else discord.ButtonStyle.gray,
            label=label,
        )
        self.is_favorite: bool = is_favorite
        self.object_id: int = object_id
        self.table: str = table
        self.column: str = column
        self.menu: SetupCharactersPaginator | SetupPlayersPaginator = menu

    @override
    async def callback(self, interaction: AluInteraction) -> None:
        assert interaction.guild

        if self.is_favorite:
            # delete from the favorites list
            query = f"DELETE FROM {self.table} WHERE guild_id=$1 AND {self.column}=$2"
        else:
            # add to the favorites list
            query = f"""
                INSERT INTO {self.table}
                (guild_id, {self.column})
                VALUES ($1, $2)
                ON CONFLICT DO NOTHING
            """
        await interaction.client.pool.execute(query, interaction.guild.id, self.object_id)

        # Edit the message with buttons
        self.is_favorite = not self.is_favorite
        self.style = discord.ButtonStyle.green if self.is_favorite else discord.ButtonStyle.gray
        await interaction.response.edit_message(view=self.menu)


# DATABASE REMOVE VIEWS


class DatabaseRemoveView(AluView, name="Database Remove View"):
    """View for `/database {game} remove` command.

    This shows
    * Remove all accounts for the said player
    * List of buttons to remove each known account for the said player.
    """

    def __init__(
        self,
        author_id: int,
        cog: BaseSettingsCog,
        player_id: int,
        player_name: str,
        account_ids_names: Mapping[AccountIDType, str],
        account_id_column: str,
    ) -> None:
        super().__init__(author_id=author_id)

        self.add_item(RemoveAllAccountsButton(cog, player_id, player_name))

        for counter, (account_id, account_name) in enumerate(account_ids_names.items()):
            percent_counter = (counter + 1) % 10
            self.add_item(
                RemoveAccountButton(const.DIGITS[percent_counter], cog, account_id, account_name, account_id_column),
            )


class RemoveAllAccountsButton(discord.ui.Button[DatabaseRemoveView]):
    """Button to remove all specific player's accounts in  `/database {game} remove` command's view."""

    def __init__(self, cog: BaseSettingsCog, player_id: int, player_name: str) -> None:
        super().__init__(
            style=discord.ButtonStyle.red,
            label=f"Remove all {player_name}'s accounts.",
            emoji="\N{POUTING FACE}",
        )
        self.cog: BaseSettingsCog = cog
        self.player_id: int = player_id
        self.player_name: str = player_name

    @override
    async def callback(self, interaction: AluInteraction) -> None:
        query = f"DELETE FROM {self.cog.prefix}_players WHERE player_id=$1"
        result: str = await interaction.client.pool.execute(query, self.player_id)

        if result != "DELETE 1":
            msg = "Error deleting this player from the database."
            raise errors.BadArgument(msg)

        embed = discord.Embed(color=self.cog.color).add_field(
            name="Successfully removed a player from the database",
            value=self.player_name,
        )
        await interaction.response.send_message(embed=embed)


class RemoveAccountButton(discord.ui.Button[DatabaseRemoveView]):
    """Button to remove a specific player's account in  `/database {game} remove` command's view."""

    def __init__(
        self,
        emoji: str,
        cog: BaseSettingsCog,
        account_id: AccountIDType,
        account_name: str,
        account_id_column: str,
    ) -> None:
        super().__init__(
            style=discord.ButtonStyle.blurple,
            label=account_name,
            emoji=emoji,
        )
        self.cog: BaseSettingsCog = cog
        self.account_id: AccountIDType = account_id
        self.account_id_column: str = account_id_column

    @override
    async def callback(self, interaction: AluInteraction) -> None:
        query = f"DELETE FROM {self.cog.prefix}_accounts WHERE {self.account_id_column} = $1"
        result: str = await interaction.client.pool.execute(query, self.account_id)
        if result != "DELETE 1":
            msg = "Error deleting this account from the database."
            raise errors.BadArgument(msg)

        embed = discord.Embed(color=self.cog.color).add_field(
            name="Successfully removed an account from the database",
            value=self.label,
        )
        await interaction.response.send_message(embed=embed)


class BaseSettingsCog(AluCog):
    """Base class for cogs representing FPC (Favorite Player+Character) feature.

    The following games are currently supported:
    * Dota 2
    * League of Legends
    * and probably more to come.

    Since many base features can be generalized -
    here is the base class containing base methods.

    Attributes
    ----------
    prefix: str
        Code-name for the game, i.e. `lol`, `dota`.
        Important notes.
        1) It's assumed that SQL tables related to FPC are named accordingly to this prefix.
        For example, Game accounts table should be named f'{self.prefix}_accounts'`,
        i.e. `dota_accounts`.
        2) name for slash command is assumed to be starting with `/{self.prefix} as well,
        i.e. `/dota player setup`
    color: discord.Color
        The color that will be used for all embeds related to this game notifications.
    game_display_name: str
        Display name of the game. This is used in response strings mentioning the game for user-end eyes.
    game_icon_url: str
        Display icon for the game. For example, this is used in footnote icons mentioning the game.
    character_singular_word: str
        Gathering word to describe the characters for the game,
        i.e. "hero" for Dota 2, "champion" for League of Legends, "agent" for Valorant.
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

    """  # todo: check these parameters

    def __init__(
        self,
        bot: AluBot,
        *args: Any,
        prefix: str,
        color: int,
        game_display_name: str,
        game_icon_url: str,
        character_singular: str,
        character_plural: str,
        player_cls: type[BasePlayer[BaseAccount]],
        characters: CharacterStorage[Any, Any],  # idk better, why [Character] doesn't work :c
        **kwargs: Any,
    ) -> None:
        super().__init__(bot, *args, **kwargs)

        # game attrs
        self.prefix: str = prefix
        self.color: int = color
        self.game_display_name: str = game_display_name
        self.game_icon_url: str = game_icon_url
        self.character_singular: str = character_singular
        self.character_plural: str = character_plural

        # account attrs
        self.player_cls: type[BasePlayer[BaseAccount]] = player_cls
        self.account_columns: tuple[str, ...] = tuple(player_cls.account_cls.__annotations__.keys())
        self.account_id_column: str = self.account_columns[0]

        # storage
        self.characters: CharacterStorage[Character, Character] = characters

        # setup messages cache
        self.setup_messages_cache: dict[int, AluView | AluLayoutView] = {}

    # fpc database management related functions ########################################################################

    async def check_if_account_already_in_database(self, account_id: AccountIDType) -> None:
        """Check if player queried by commands is already in the database.

        Commands in question are `/{game} request player` or `database-{game}-dev add`
        """
        query = f"""
            SELECT display_name
            FROM {self.prefix}_players
            WHERE player_id = (
                SELECT player_id
                FROM {self.prefix}_accounts
                WHERE {self.account_id_column}=$1
            )
        """
        display_name: str | None = await self.bot.pool.fetchval(query, account_id)
        if display_name:
            msg = (
                "This account is already in the database.\n"
                f"It is marked as {display_name}'s account.\n\n"
                f"You might have wanted to use `/{self.prefix} setup players` and chose this player from here."
            )
            raise errors.BadArgument(msg)

    async def request_player(self, interaction: AluInteraction, arguments: BaseRequestPlayerArguments) -> None:
        """Base function for `/{game} request player` command.

        This allows people to request player accounts to be added into the bot's FPC database.
        """
        await interaction.response.defer()
        player = await self.player_cls.create(self.bot, arguments)
        await self.check_if_account_already_in_database(account_id=getattr(player.account, self.account_id_column))

        confirm_embed = (
            discord.Embed(
                color=self.color,
                title="Confirmation Prompt",
                description=(
                    "Are you sure you want to request this streamer steam account to be added into the database?\n"
                    "This information will be sent to Aluerie. Please, double check before confirming."
                ),
            )
            .set_author(name="Request to add an account into the database")
            .set_thumbnail(url=player.avatar_url)
            .add_field(name=player.field_name(), value=player.account.links())
            .set_footer(text=self.game_display_name, icon_url=self.game_icon_url)
        )

        if not await self.bot.disambiguator.confirm(interaction, embed=confirm_embed):
            return

        response_embed = discord.Embed(
            color=self.color,
            title="Successfully made a request to add the account into the database",
        ).add_field(name=player.field_name, value=player.account.links())
        await interaction.followup.send(embed=response_embed)

        logs_embed = confirm_embed.copy()
        logs_embed.title = ""
        logs_embed.description = ""
        logs_embed.set_author(name=interaction.user, icon_url=interaction.user.display_avatar.url)
        logs_embed.add_field(
            name="Command",
            value=f"/database {self.prefix} add {player.hint_database_add_command_arguments()}",
            inline=False,
        )
        await self.hideout.global_logs.send(embed=logs_embed)

    async def database_add(self, interaction: AluInteraction, arguments: BaseRequestPlayerArguments) -> None:
        """Base function for `/database {game} add` command.

        This allows bot owner to add player accounts into the bot's FPC database.
        """
        await interaction.response.defer()
        player = await self.player_cls.create(self.bot, arguments)
        await self.check_if_account_already_in_database(account_id=getattr(player.account, self.account_id_column))

        query = f"""
            WITH e AS (
                INSERT INTO {self.prefix}_players
                (display_name, twitch_id)
                VALUES ($1, $2)
                ON CONFLICT (twitch_id) DO NOTHING
                RETURNING player_id
            )
            SELECT * FROM e
            UNION
                SELECT player_id FROM {self.prefix}_players WHERE twitch_id=$2;
        """  # https://stackoverflow.com/a/62205017/19217368 # todo: TWITCH DISTINCT NOT NULL ?
        player_id: int = await interaction.client.pool.fetchval(query, player.display_name, player.twitch_id)

        database_dict = player.account.__dict__
        database_dict["player_id"] = player_id
        dollars = ", ".join(f"${i}" for i in range(1, len(database_dict.keys()) + 1))
        columns = ", ".join(database_dict.keys())
        query = f"INSERT INTO {self.prefix}_accounts ({columns}) VALUES ({dollars})"
        await interaction.client.pool.execute(query, *database_dict.values())

        response_embed = (
            discord.Embed(color=self.color, title="Successfully added the account to the database")
            .add_field(name=player.field_name(), value=player.account.links())
            .set_author(name=self.game_display_name, icon_url=self.game_icon_url)
            .set_thumbnail(url=player.avatar_url)
        )
        await interaction.followup.send(embed=response_embed)

        logs_embed = response_embed.copy()
        logs_embed.set_author(
            name=interaction.user,
            icon_url=interaction.user.display_avatar.url,
        ).set_footer(text="Don't forget to add the player to your favorites!")
        await self.hideout.global_logs.send(embed=logs_embed)

    async def database_remove(self, interaction: AluInteraction, player_name: str) -> None:
        """Base function for `/database {game} remove` command.

        This allows bot owner to remove player accounts from the bot's FPC database.
        """  # TODO: docs on actual commands to say that it's a menu not instant death
        await interaction.response.defer()

        player_id, display_name = await self.get_player_id_and_display_name(player_name)

        columns = ", ".join(self.account_columns)
        query = f"SELECT {columns} FROM {self.prefix}_accounts WHERE player_id = $1"
        rows: list[dict[str, Any]] = await self.bot.pool.fetch(query, player_id)
        account_ids_names: Mapping[AccountIDType, str] = {
            row[self.account_id_column]: self.player_cls.account_cls(**row).display_name for row in rows
        }

        view = DatabaseRemoveView(
            interaction.user.id,
            self,
            player_id,
            display_name,
            account_ids_names,
            self.account_id_column,
        )
        await interaction.followup.send(view=view)

    # fpc settings related functions ###################################################################################

    async def setup_channel(self, interaction: AluInteraction) -> None:
        """Base function for `/{game} setup channel` command.

        This gives
        * Embed with current state of channel setup
        * View to select a new channel for FPC notifications
        """
        await interaction.response.defer()
        # Get channel
        query = f"SELECT channel_id FROM {self.prefix}_settings WHERE guild_id=$1"
        channel_id: int | None = await self.bot.pool.fetchval(query, interaction.guild_id)

        if channel_id:
            channel = self.bot.get_channel(channel_id) or await self.bot.fetch_channel(channel_id)
            assert isinstance(channel, discord.TextChannel)  # view select prevents channel from being any other type
            mimic = mimics.Mimic.from_channel(self.bot, channel)
            webhook = await mimic.get_or_create_webhook()
        else:
            channel = None
            webhook = None

        embed = (
            discord.Embed(
                color=self.color,
                title="FPC (Favorite Player+Character) Channel Setup",
                description=(
                    "This embed shows the channel where the bot will send FPC notifications. "
                    "You can choose a new channel, "
                    "the bot will also create a webhook in that channel to send messages with.\n\n"
                    "After choosing the channel, the bot will edit this message to showcase newly selected channel."
                ),
            )
            .add_field(name=f"Channel {fmt.tick(bool(channel))}", value=channel.mention if channel else "Not set")
            .add_field(name=f"Webhook {fmt.tick(bool(webhook))}", value="Properly Set" if webhook else "Not set")
            .set_footer(text=self.game_display_name, icon_url=self.game_icon_url)
        )
        view = SetupChannel(self, author_id=interaction.user.id, embed=embed)
        message = await interaction.followup.send(embed=embed, view=view, wait=True)
        view.message = message
        self.setup_messages_cache[message.id] = view

    async def is_fpc_channel_set(self, interaction: AluInteraction) -> None:
        """Checks if the current guild has fpc channel set.

        It's somewhat needed because without it functions like `setup_characters`, `setup_players`
        will fail with ForeignKeyViolationError since there is nothing in `{self.prefix}_settings` table.
        """
        query = f"SELECT channel_id FROM {self.prefix}_settings WHERE guild_id=$1"
        channel_id: int | None = await interaction.client.pool.fetchval(query, interaction.guild_id)
        if not channel_id:
            cmd_mention = (
                self.bot.tree.find_mention(f"{self.prefix} setup channel") or f"`/{self.prefix} setup channel`"
            )
            msg = (
                "I'm sorry! You cannot use this command without setting up "
                f"{self.game_display_name} FPC (Favorite Player+Character) channel first. "
                f"Please, use {cmd_mention} to assign it."
            )
            raise errors.ErroneousUsage(msg)

    async def setup_misc(self, interaction: AluInteraction) -> None:
        """Base function for `/{game} setup miscellaneous` command.

        This gives
        * Embed with current state of FPC settings
        * Buttons to toggle state of those settings
        * Button to remove the whole data and stop getting FPC notifications
        """
        await interaction.response.defer()
        await self.is_fpc_channel_set(interaction)

        query = f"SELECT enabled, spoil, twitch_live_only FROM {self.prefix}_settings WHERE guild_id=$1"
        row: SetupMiscQueryRow = await interaction.client.pool.fetchrow(query, interaction.guild_id)

        view = SetupMiscView(self, author_id=interaction.user.id, settings=row)
        message = await interaction.followup.send(view=view, wait=True)
        view.message = message
        self.setup_messages_cache[message.id] = view

    # async def get_character_name_by_id_cache(self) -> dict[int, str]:
    #     raise NotImplementedError

    async def setup_characters(self, interaction: AluInteraction) -> None:
        """Base function for `/{game} setup {character_plural}` command.

        This gives
        * View of buttons to add/remove characters to/from person favorite characters
        """
        await interaction.response.defer()
        await self.is_fpc_channel_set(interaction)

        characters: list[Character] = await self.characters.walk_characters()
        characters.sort(key=lambda x: x.display_name)

        paginator = SetupCharactersPaginator(interaction, characters, self)
        message = await paginator.start()
        # paginator.message is already assigned
        self.setup_messages_cache[message.id] = paginator

    async def setup_players(self, interaction: AluInteraction) -> None:
        """Base function for `/{game} setup players` command.

        This gives
        * View of buttons to add/remove players to/from person favorite players
        """
        await interaction.response.defer()
        await self.is_fpc_channel_set(interaction)

        query = f"SELECT player_id, display_name FROM {self.prefix}_players"
        rows: list[SetupPlayerQueryRow] = await interaction.client.pool.fetch(query)

        player_tuples: list[tuple[int, str]] = [(row["player_id"], row["display_name"]) for row in rows]
        player_tuples.sort(key=lambda pt: pt[1].lower())

        paginator = SetupPlayersPaginator(interaction, player_tuples, self)
        message = await paginator.start()
        # paginator.message is already assigned
        self.setup_messages_cache[message.id] = paginator

    # HIDEOUT ONLY RELATED FUNCTIONS ###################################################################################

    # The reason they are hideout-only is because I like using autocomplete for development.
    # But I think it might be confusing for end-user if I have several commands to add/remove players/characters.
    # One simple interactive view is enough for them granted they aren't supposed to change their preferences much.
    # I'm also just hesitant to completely delete all my previous work so let's at least leave one-name version

    async def get_player_id_and_display_name(self, player_name: str) -> tuple[int, str]:
        """Get player_id, display_name by their name from FPC database.

        Parameters
        ----------
        player_name: str
            Player name to search for in the database, received from slash command argument.
        """
        query = f"SELECT player_id, display_name FROM {self.prefix}_players WHERE lower(display_name)=$1"
        player_row: SetupPlayerQueryRow | None = await self.bot.pool.fetchrow(query, player_name.lower())
        if player_row is None:
            msg = f"There is no player named {player_name} in the database. Please, double check everything."
            raise errors.BadArgument(msg)
        return player_row["player_id"], player_row["display_name"]

    async def hideout_player_add(self, interaction: AluInteraction, player_name: str) -> None:
        """Base function for `/{game}-dev player add` Hideout-only command.

        Parameters
        ----------
        player_name: str
            Player name to add to subscriber's favorites, received from a slash command argument.
        """  # TODO: check AluInteraction # TODO: check if all functions have Parameters in their docs
        await interaction.response.defer()
        player_id, player_display_name = await self.get_player_id_and_display_name(player_name)

        query = f"INSERT INTO {self.prefix}_favorite_players (guild_id, player_id) VALUES ($1, $2)"
        try:
            await interaction.client.pool.execute(query, interaction.guild_id, player_id)
        except asyncpg.UniqueViolationError:
            msg = f"Player {player_display_name} was already in your favorite list."
            raise errors.BadArgument(msg) from None

        embed = discord.Embed(color=self.color).add_field(
            name="Successfully added the player to your favorites.",
            value=player_display_name,
        )
        await interaction.followup.send(embed=embed)

    async def hideout_player_remove(self, interaction: AluInteraction, player_name: str) -> None:
        """Base function for `/{game}-dev player remove` Hideout-only command.

        Parameters
        ----------
        player_name: str
            Player name to remove from subscriber's favorites, received from a slash command argument.
        """
        await interaction.response.defer()
        player_id, player_display_name = await self.get_player_id_and_display_name(player_name)

        query = f"DELETE FROM {self.prefix}_favorite_players WHERE guild_id=$1 AND player_id=$2"
        result = await interaction.client.pool.execute(query, interaction.guild_id, player_id)
        if result == "DELETE 1":
            embed = discord.Embed(
                color=self.color,
                title="Successfully removed the player from your favorites.",
                description=player_display_name,
            )
            await interaction.followup.send(embed=embed)
        elif result == "DELETE 0":
            msg = f"Player {player_display_name} is already not in your favorite list."
            raise errors.BadArgument(msg)
        else:
            msg = "Unknown error."
            raise errors.BadArgument(msg)

    async def hideout_character_add(self, interaction: AluInteraction, character: Character) -> None:
        """Base function for `/{game}-dev {character_singular} add` Hideout-only command.

        Adds the character from subscriber's favorites.
        This function supports adding only one character at a time.

        Parameters
        ----------
        character: Character
            Character to add to subscriber's favorites, received from a slash command argument.
        """
        await interaction.response.defer()

        query = f"INSERT INTO {self.prefix}_favorite_characters (guild_id, character_id) VALUES ($1, $2)"
        try:
            await interaction.client.pool.execute(query, interaction.guild_id, character.id)
        except asyncpg.UniqueViolationError:
            msg = f"{self.character_singular.capitalize()} {character.display_name} was already in your favorite list."
            raise errors.BadArgument(msg) from None

        embed = discord.Embed(color=self.color).add_field(
            name=f"Successfully added a {self.character_singular} to your favorites.",
            value=character.display_name,
        )
        await interaction.followup.send(embed=embed)

    async def hideout_character_remove(self, interaction: AluInteraction, character: Character) -> None:
        """Base function for `/{game}-dev {character_singular} remove` Hideout-only command.

        Removes the character from subscriber's favorites.
        This function supports removing only one character at a time.

        Parameters
        ----------
        character: Character
            Character to remove from subscriber's favorites, received from a slash command argument.
        """
        await interaction.response.defer()

        query = f"DELETE FROM {self.prefix}_favorite_characters WHERE guild_id=$1 AND character_id=$2"
        result = await interaction.client.pool.execute(query, interaction.guild_id, character.id)
        if result == "DELETE 1":
            embed = discord.Embed(
                color=self.color,
                title=f"Successfully removed a {self.character_singular} from your favorites.",
                description=character.display_name,
            )
            await interaction.followup.send(embed=embed)
        elif result == "DELETE 0":
            msg = (
                f"{self.character_singular.capitalize()} {character.display_name} is already not "
                "in your favorite list."
            )
            raise errors.BadArgument(msg)
        else:
            msg = "Unknown error."
            raise errors.BadArgument(msg)

    async def get_player_list_embed(self, guild_id: int) -> discord.Embed:
        """Helper function to get an embed with the subscriber's list of favorite players.

        Parameters
        ----------
        guild_id: int
            Guild ID of the subscriber, for which the bot will fetch the favorite players list.
        """
        query = f"""
            SELECT display_name, twitch_id
            FROM {self.prefix}_players
            WHERE player_id=ANY(SELECT player_id FROM {self.prefix}_favorite_players WHERE guild_id=$1)
        """
        rows: list[PlayerListQueryRow] = await self.bot.pool.fetch(query, guild_id)
        favorite_player_names = (
            "\n".join([field_name(row["display_name"], row["twitch_id"]) for row in rows]) or "Empty list"
        )
        return discord.Embed(
            color=self.color,
            title="List of your favorite players",
            description=favorite_player_names,
        ).set_footer(text=self.game_display_name, icon_url=self.game_icon_url)

    async def hideout_player_list(self, interaction: AluInteraction) -> None:
        """Base function for `/{game}-dev player list` Hideout-only command.

        Responds with an embed containing the list of subscriber's favorite players.
        """
        await interaction.response.defer()
        assert interaction.guild
        embed = await self.get_player_list_embed(interaction.guild.id)
        await interaction.followup.send(embed=embed)

    async def get_character_list_embed(self, guild_id: int) -> discord.Embed:
        """Helper function to get an embed with the subscriber's list of favorite characters.

        Parameters
        ----------
        guild_id: int
            Guild ID of the subscriber, for which the bot will fetch the favorite characters list.
        """
        query = f"SELECT character_id FROM {self.prefix}_favorite_characters WHERE guild_id=$1"
        favorite_character_ids: list[int] = [
            character_id for (character_id,) in await self.bot.pool.fetch(query, guild_id)
        ]
        favorite_characters = [await self.characters.by_id(i) for i in favorite_character_ids]
        favorite_character_names = (
            "\n".join([f"{c.emote} {c.display_name}" for c in favorite_characters]) or "Empty list"
        )
        return discord.Embed(
            color=self.color,
            title=f"List of your favorite {self.character_plural}",
            description=favorite_character_names,
        )

    async def hideout_character_list(self, interaction: AluInteraction) -> None:
        """Base function for `/{game}-dev {character} list` Hideout-only command.

        Responds with an embed containing the list of subscriber's favorite characters.
        """
        await interaction.response.defer()
        assert interaction.guild
        embed = await self.get_character_list_embed(interaction.guild.id)
        await interaction.followup.send(embed=embed)

    async def hideout_player_add_remove_autocomplete(
        self, interaction: AluInteraction, current: str, *, mode_add_remove: bool
    ) -> list[app_commands.Choice[str]]:
        """Base function to define autocomplete for `player_name` argument in `/{game}-dev player add/remove`.

        Parameters
        ----------
        mode_add_remove: bool
            Mode=add if `True`, mode=remove if `False`. The respective value should match the slash command, i.e.
            body of autocomplete for `/dota-dev player remove` should have this variable as `False`.
        """
        assert interaction.guild

        query = f"""
            SELECT display_name
            FROM {self.prefix}_players
            WHERE {"NOT" if mode_add_remove else ""} player_id=ANY(
                SELECT player_id FROM {self.prefix}_favorite_players WHERE guild_id=$1
            )
            ORDER BY similarity(display_name, $2) DESC
            LIMIT 6;
        """
        return [
            app_commands.Choice(name=name, value=name)
            for (name,) in await interaction.client.pool.fetch(query, interaction.guild.id, current)
        ]

    async def database_remove_autocomplete(
        self, interaction: AluInteraction, current: str
    ) -> list[app_commands.Choice[str]]:
        """Base function to define autocomplete for `player_name` argument in `/database {game} remove`."""
        query = f"""
            SELECT display_name
            FROM {self.prefix}_players
            ORDER BY similarity(display_name, $1) DESC
            LIMIT 6;
        """
        return [
            app_commands.Choice(name=name, value=name)
            for (name,) in await interaction.client.pool.fetch(query, current)
        ]

    async def tutorial(self, interaction: AluInteraction) -> None:
        """Base function for `/{game} tutorial` command.

        Responds with an embed explaining the whole work-flow for the end user on how to use FPC feature.
        Walks with them through process of
        * Setting up a channel for notifications;
        * Setting up a list of favorite players;
        * Setting up a list of favorite characters;
        * Changing miscellaneous settings for this feature;
        * Requesting developers to add new accounts into the database;
        """
        await interaction.response.defer()

        file = discord.File("assets/images/local/fpc_tutorial.png")
        embed = (
            discord.Embed(
                color=self.color,
                title="FPC Notifications Setup Tutorial",
                description=(
                    "This embed will explain how to set up __F__avourite __P__layers + __C__haracters Notifications "
                    "(or shortly FPC Notifications). Just follow the easy intuitive steps below."
                ),  # cSpell: ignore: avourite, haracters
            )
            .set_footer(text=self.game_display_name, icon_url=self.game_icon_url)
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
                f"setup {self.character_plural}",
                (
                    "Third, you need to choose your __F__avourite __C__haracters from the list of "
                    f"{self.game_display_name} {self.character_plural}."
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
            cmd_mention = await self.bot.tree.find_mention(
                f"{self.prefix} {almost_qualified_name}", guild=interaction.guild
            )
            if cmd_mention:
                embed.add_field(name=f"{const.DIGITS[count]}. Use {cmd_mention}", value=field_value, inline=False)
            else:
                msg = "Somehow FPC related command is None."
                raise RuntimeError(msg)

        await interaction.followup.send(embed=embed, file=file)
