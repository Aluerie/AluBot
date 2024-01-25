from __future__ import annotations

from typing import TYPE_CHECKING, Awaitable, Callable, Mapping, Optional, TypedDict

import discord
from discord.ext import menus

from utils import AluView, const, errors, formats, pages

if TYPE_CHECKING:
    from bot import AluBot
    from utils import AluGuildContext

    from .settings import AccountIDType, FPCSettingsBase

    class AccountListButtonQueryRow(TypedDict):
        display_name: str
        twitch_id: int
        # fake, query row has more keys

    class AccountListButtonPlayerSortDict(TypedDict):
        name: str
        accounts: list[str]


class FPCSetupChannelView(AluView):
    """View for a command `/{game} setup channel`.

    This gives
    * Dropdown menu to select a new channel for notifications.
    """

    def __init__(self, cog: FPCSettingsBase, author_id: int):
        super().__init__(author_id=author_id)
        self.cog: FPCSettingsBase = cog

    @discord.ui.select(
        cls=discord.ui.ChannelSelect,
        channel_types=[discord.ChannelType.text, discord.ChannelType.news],
        placeholder="\N{BIRD} Select a new FPC notifications Channel",
        row=0,
    )
    async def set_channel(self, interaction: discord.Interaction[AluBot], select: discord.ui.ChannelSelect):
        chosen_channel = select.values[0]  # doesn't have all data thus we need to resolve
        channel = chosen_channel.resolve() or await chosen_channel.fetch()

        # probably not needed but who knows what type of channels Discord will make one day
        if not isinstance(channel, discord.TextChannel):
            raise errors.ErroneousUsage(
                f"You can't select a channel of this type for {self.cog.game_display_name} FPC channel."
                "Please, select normal text channel."
            )

        if not channel.permissions_for(channel.guild.me).send_messages:
            raise errors.ErroneousUsage(
                "I do not have permission to `send_messages` in that channel. "
                "Please, select a channel where I can do that so I'm able to send notifications in future."
            )

        query = f"""
            INSERT INTO {self.cog.prefix}_settings (guild_id, guild_name, channel_id)
            VALUES ($1, $2, $3)
            ON CONFLICT (guild_id) DO UPDATE
                SET channel_id=$3;
        """
        await interaction.client.pool.execute(query, channel.guild.id, channel.guild.name, channel.id)

        embed = discord.Embed(
            colour=self.cog.colour,
            description=f"From now on I will send {self.cog.game_display_name} FPC Notifications to {channel.mention}.",
        )
        return await interaction.response.send_message(embed=embed)


class FPCSetupMiscView(AluView):
    """View for a command `/{game} setup misc`.

    This gives
    * Button to disable/enable notifications for a time being
    * Button to disable/enable spoil-ing post-match results
    * Button to delete user's FPC data from the database
    """

    def __init__(
        self,
        cog: FPCSettingsBase,
        embed: discord.Embed,
        *,
        author_id: int,
    ):
        super().__init__(author_id=author_id)
        self.cog: FPCSettingsBase = cog
        self.embed: discord.Embed = embed

    async def toggle_worker(self, interaction: discord.Interaction[AluBot], setting: str, field_index: int):
        query = f"""
            UPDATE {self.cog.prefix}_settings 
            SET {setting}=not({setting}) 
            WHERE guild_id = $1
            RETURNING {setting}
        """
        new_value: bool = await interaction.client.pool.fetchval(query, interaction.guild_id)

        old_field_name = self.embed.fields[field_index].name
        assert isinstance(old_field_name, str)
        new_field_name = f'{old_field_name.split(":")[0]} {"`on`" if new_value else "`off`"} {formats.tick(new_value)}'
        old_field_value = self.embed.fields[field_index].value
        self.embed.set_field_at(field_index, name=new_field_name, value=old_field_value, inline=False)
        await interaction.response.edit_message(embed=self.embed)

    @discord.ui.button(emoji="\N{BLACK SQUARE FOR STOP}", label='Toggle "Receive Notifications Setting"', row=0)
    async def toggle_enable(self, interaction: discord.Interaction[AluBot], _: discord.ui.Button):
        await self.toggle_worker(interaction, "enabled", 0)

    @discord.ui.button(emoji="\N{MICROSCOPE}", label='Toggle "Show Post-Match Results Setting"', row=1)
    async def toggle_spoil(self, interaction: discord.Interaction[AluBot], _: discord.ui.Button):
        await self.toggle_worker(interaction, "spoil", 1)

    @discord.ui.button(emoji="\N{CLAPPER BOARD}", label='Toggle "Only Twitch Live Players Setting"', row=2)
    async def toggle_twitch_live_only(self, interaction: discord.Interaction[AluBot], _: discord.ui.Button):
        await self.toggle_worker(interaction, "twitch_live_only", 2)

    @discord.ui.button(
        label="Delete Your Data and Stop Notifications",
        style=discord.ButtonStyle.red,
        emoji="\N{WASTEBASKET}",
        row=3,
    )
    async def delete_data(self, interaction: discord.Interaction[AluBot], _: discord.ui.Button):
        # Confirmation
        confirm_embed = (
            discord.Embed(
                colour=self.cog.colour,
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
                    f"\N{BLACK CIRCLE} your favourite players data\n"
                    f"\N{BLACK CIRCLE} your favourite {self.cog.character_plural_word} data\n"
                    f"\N{BLACK CIRCLE} your {self.cog.character_plural_word} FPC Notifications channel data."
                ),
            )
        )

        if not interaction.client.disambiguator.confirm(interaction, confirm_embed):
            return

        # Disable the Channel
        query = f"DELETE FROM {self.cog.prefix}_settings WHERE guild_id=$1"
        await interaction.client.pool.execute(query, interaction.guild_id)

        response_embed = discord.Embed(
            colour=discord.Colour.green(),
            title="FPC (Favourite Player+Character) channel removed.",
            description=f"Notifications will not be sent anymore. Your data was deleted as well.",
        ).set_author(name=self.cog.game_display_name, icon_url=self.cog.game_icon_url)
        await interaction.followup.send(embed=response_embed)


class AddRemoveButton(discord.ui.Button):
    """Green/Black Buttons to Remove from/Add to favourite list
    for `/{game} setup players/{characters}` command's view.
    """

    def __init__(self, label: str, is_favourite: bool, object_id: int, menu: FPCSetupPlayersCharactersPaginator):
        super().__init__(
            style=discord.ButtonStyle.green if is_favourite else discord.ButtonStyle.gray,
            label=label,
        )
        self.is_favourite: bool = is_favourite
        self.object_id: int = object_id
        self.menu: FPCSetupPlayersCharactersPaginator = menu

    async def callback(self, interaction: discord.Interaction[AluBot]):
        assert interaction.guild

        if self.is_favourite:
            # delete from the favourites list
            query = f"DELETE FROM {self.menu.table_name} WHERE guild_id=$1 AND {self.menu.id_column_name}=$2"
        else:
            # add to the favourites list
            query = f"""
                INSERT INTO {self.menu.table_name}
                (guild_id, {self.menu.id_column_name}) 
                VALUES ($1, $2)
                ON CONFLICT DO NOTHING
            """
        await interaction.client.pool.execute(query, interaction.guild.id, self.object_id)

        # Edit the message with buttons
        self.is_favourite = not self.is_favourite
        self.style = discord.ButtonStyle.green if self.is_favourite else discord.ButtonStyle.gray
        await interaction.response.edit_message(view=self.menu)


class AccountListButton(discord.ui.Button):
    """5th Button to Show account list for `/{game} setup players` command's view."""

    def __init__(self, entries: list[tuple[int, str]], menu: FPCSetupPlayersCharactersPaginator):
        super().__init__(
            style=discord.ButtonStyle.blurple,
            label="\N{PENCIL}",
        )
        self.entries: list[tuple[int, str]] = entries
        self.menu: FPCSetupPlayersCharactersPaginator = menu
        self.field_name: str = "\N{PENCIL} List of accounts of players shown on the page"
        self.field_value: str = "Show list of accounts with links to their profiles and extra information."

    async def callback(self, interaction: discord.Interaction[AluBot]):
        assert interaction.guild

        columns = "display_name, twitch_id, " + ", ".join(self.menu.cog.account_table_columns)

        query = f"""
            SELECT {columns}
            FROM {self.menu.cog.prefix}_players p
            JOIN {self.menu.cog.prefix}_accounts a
            ON p.player_id = a.player_id
            ORDER BY display_name
        """
        rows: list[AccountListButtonQueryRow] = await interaction.client.pool.fetch(query) or []

        player_dict: dict[str, AccountListButtonPlayerSortDict] = {}
        for row in rows:
            if row["display_name"] not in player_dict:
                player_dict[row["display_name"]] = {
                    "name": self.menu.cog.account_cls.embed_player_name_static(
                        row["display_name"], bool(row["twitch_id"])
                    ),
                    "accounts": [],
                }

            account_kwargs = {column: row[column] for column in self.menu.cog.account_table_columns}
            player_dict[row["display_name"]]["accounts"].append(
                self.menu.cog.account_cls.embed_account_str_static(**account_kwargs)
            )

        embed = discord.Embed(
            colour=self.menu.cog.colour,
            title="List of accounts for players shown above.",
            description="\n".join(
                f"{player['name']}\n{chr(10).join(player['accounts'])}" for player in player_dict.values()
            ),
        ).set_footer(
            text=f"to request a new account/player to be added - use `/{self.menu.cog.prefix} request player` command",
            icon_url=self.menu.cog.game_icon_url,
        )

        await interaction.response.send_message(embed=embed, ephemeral=True)


class FPCSetupPlayersCharactersPageSource(menus.ListPageSource):
    """Page source for both commands `/{game} setup players/champions`."""

    def __init__(self, data: list[tuple[int, str]]):
        super().__init__(entries=data, per_page=20)

    async def format_page(self, menu: FPCSetupPlayersCharactersPaginator, entries: list[tuple[int, str]]):
        """
        Create a page for `/{game} setup {characters/players}` command.

        This gives
         * Embed with explanation text
         * Buttons to add/remove characters to/from favourite list.

        Parameters
        ----------
        entries:
            List of (id, name) tuples,
            for example: [(1, "Anti-Mage"), (2, "Axe"), ...] or [(1, "gosu"), (2, "Quantum"), ...].
        """

        # unfortunately we have to fetch favourites each format page
        # in case they are bad acting with using both slash commands
        # or several menus
        query = f"SELECT {menu.id_column_name} FROM {menu.table_name} WHERE guild_id=$1"
        assert menu.ctx_ntr.guild
        favourite_ids: list[int] = [r for r, in await menu.ctx_ntr.client.pool.fetch(query, menu.ctx_ntr.guild.id)]

        menu.clear_items()

        embed = (
            discord.Embed(
                colour=menu.cog.colour,
                title=f"Your favourite {menu.cog.game_display_name} {menu.plural} list interactive setup",
                description=f"Pagination menu below represents all {menu.plural} from {menu.cog.game_display_name}.",
            )
            .add_field(
                name="\N{LARGE GREEN SQUARE}/\N{BLACK LARGE SQUARE} Buttons",
                value=(
                    f"Press those buttons to mark/demark a a {menu.singular} as your favourite.\n"
                    "Button's colour shows if it's currently chosen as your favourite. "
                    "(\N{LARGE GREEN SQUARE} - yes, \N{BLACK LARGE SQUARE} - no)\n"
                ),
                inline=False,
            )
            .add_field(
                name=f"{menu.object_list.label} Your favourite {menu.plural} list Button",
                value=f"Show your favourite {menu.plural} list.",
                inline=False,
            )
        )

        if menu.special_button_cls is None:
            special_item = menu.search
        else:
            special_item = menu.special_button_cls(entries, menu)
            embed.add_field(name=special_item.field_name, value=special_item.field_value)
        for item in [menu.object_list, menu.previous_page, menu.index, menu.next_page, special_item]:
            menu.add_item(item)

        for entry in entries:
            id, name = entry
            is_favourite = id in favourite_ids
            menu.add_item(AddRemoveButton(name, is_favourite, id, menu))

        return embed


class FPCSetupPlayersCharactersPaginator(pages.Paginator):
    """A Parent Paginator class for both commands `/{game} setup players/champions`."""

    def __init__(
        self,
        ctx: AluGuildContext,
        object_id_name_tuples: list[tuple[int, str]],
        table_object_name: str,
        singular: str,
        plural: str,
        cog: FPCSettingsBase,
        get_object_list_embed: Callable[[int], Awaitable[discord.Embed]],
        special_button_cls: Optional[type[AccountListButton]] = None,
    ):
        """__init__

        Parameters
        ----------
        ctx : AluGuildContext
            Context
        object_id_name_tuples : list[tuple[int, str]]
            list of tuples to pass to source. Something like list of (hero_id, hero_name) tuples.
        table_object_name : str
            object's name in our SQL tables, i.e. "player", "character".
        singular : str
            object's display name in singular form, i.e. "player", "hero", "champion"
        plural : str
            object's display name in plural form, i.e. "players", "heroes", "champions"
        cog : FPCSettingsBase
            the cog
        get_object_list_embed : Callable[[int], Awaitable[discord.Embed]]
            this has to go separately because the cog has all the functions.
        special_button_cls : Optional[type[AccountListButton]], optional
            button to replace the 5th button in pagination menu.
            i.e. we want account list for /setup players command.
        """
        super().__init__(
            ctx,
            source=FPCSetupPlayersCharactersPageSource(object_id_name_tuples),
        )
        self.singular: str = singular
        self.plural: str = plural
        self.cog: FPCSettingsBase = cog
        self.get_object_list_embed: Callable[[int], Awaitable[discord.Embed]] = get_object_list_embed

        self.table_name: str = f"{cog.prefix}_favourite_{table_object_name}s "
        self.id_column_name: str = f"{table_object_name}_id"
        self.special_button_cls: Optional[type[AccountListButton]] = special_button_cls

    @discord.ui.button(label="\N{PAGE WITH CURL}", style=discord.ButtonStyle.blurple)
    async def object_list(self, interaction: discord.Interaction, _: discord.ui.Button):
        """Show favourite object list."""
        assert interaction.guild
        embed = await self.get_object_list_embed(interaction.guild.id)
        await interaction.response.send_message(embed=embed, ephemeral=True)


class FPCSetupPlayersPaginator(FPCSetupPlayersCharactersPaginator):
    """A Paginator for `/{game} setup players` command.

    This gives:
    * pagination menu
    * list of favourite players button
    * buttons to mark/demark player as favourite
    * button to view all accounts for presented embed
    """

    def __init__(
        self,
        ctx: AluGuildContext,
        player_tuples: list[tuple[int, str]],
        cog: FPCSettingsBase,
    ):
        super().__init__(
            ctx,
            player_tuples,
            "player",
            "player",
            "players",
            cog,
            cog.get_player_list_embed,
            AccountListButton,
        )


class FPCSetupCharactersPaginator(FPCSetupPlayersCharactersPaginator):
    """A Paginator for `/{game} setup characters` command.

    This gives:
    * pagination menu
    * list of favourite characters button
    * buttons to mark/demark character as favourite
    """

    def __init__(
        self,
        ctx: AluGuildContext,
        character_tuples: list[tuple[int, str]],
        cog: FPCSettingsBase,
    ):
        super().__init__(
            ctx,
            character_tuples,
            "character",
            cog.character_singular_word,
            cog.character_plural_word,
            cog,
            cog.get_character_list_embed,
        )


### DATABASE REMOVE VIEWS


class RemoveAllAccountsButton(discord.ui.Button):
    """Button to remove all specific player's accounts in  `/database {game} remove` command's view."""

    def __init__(self, cog: FPCSettingsBase, player_id: int, player_name: str):
        super().__init__(
            style=discord.ButtonStyle.red,
            label=f"Remove all {player_name}'s accounts.",
            emoji="\N{POUTING FACE}",
        )
        self.cog: FPCSettingsBase = cog
        self.player_id: int = player_id
        self.player_name: str = player_name

    async def callback(self, interaction: discord.Interaction[AluBot]):
        query = f"DELETE FROM {self.cog.prefix}_players WHERE player_id=$1"
        result: str = await interaction.client.pool.execute(query, self.player_id)

        if result != "DELETE 1":
            raise errors.BadArgument("Error deleting this player from the database.")

        embed = discord.Embed(colour=self.cog.colour).add_field(
            name="Succesfully removed a player from the database",
            value=self.player_name,
        )
        await interaction.response.send_message(embed=embed)


class RemoveAccountButton(discord.ui.Button):
    """Button to remove a specific player's account in  `/database {game} remove` command's view."""

    def __init__(
        self,
        emoji: str,
        cog: FPCSettingsBase,
        account_id: AccountIDType,
        account_name: str,
        account_id_column: str,
    ):
        super().__init__(
            style=discord.ButtonStyle.blurple,
            label=account_name,
            emoji=emoji,
        )
        self.cog: FPCSettingsBase = cog
        self.account_id: AccountIDType = account_id
        self.account_id_column: str = account_id_column

    async def callback(self, interaction: discord.Interaction[AluBot]):
        query = f"DELETE FROM {self.cog.prefix}_accounts WHERE {self.account_id_column} = $1"
        result: str = await interaction.client.pool.execute(query, self.account_id)
        if result != "DELETE 1":
            raise errors.BadArgument("Error deleting this account from the database.")

        embed = discord.Embed(colour=self.cog.colour).add_field(
            name="Succesfully removed an account from the database",
            value=self.label,
        )
        await interaction.response.send_message(embed=embed)


class DatabaseRemoveView(AluView):
    """View for `/database {game} remove` command.

    This shows
    * Remove all accounts for the said player
    * List of buttons to remove each known account for the said player.
    """

    def __init__(
        self,
        author_id: int,
        cog: FPCSettingsBase,
        player_id: int,
        player_name: str,
        account_ids_names: Mapping[AccountIDType, str],
        account_id_column: str,
    ):
        super().__init__(
            author_id=author_id,
            view_name="Database Remove View",
        )

        self.add_item(RemoveAllAccountsButton(cog, player_id, player_name))

        for counter, (account_id, account_name) in enumerate(account_ids_names.items()):
            percent_counter = (counter + 1) % 10
            self.add_item(
                RemoveAccountButton(const.DIGITS[percent_counter], cog, account_id, account_name, account_id_column)
            )
