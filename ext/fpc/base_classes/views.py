from __future__ import annotations

from typing import TYPE_CHECKING, Self, TypedDict, override

import discord
from discord.ext import menus

from bot import AluView
from utils import const, errors, formats, mimics, pages

if TYPE_CHECKING:
    from collections.abc import Mapping

    from bot import AluBot
    from utils.fpc import Character

    from .settings import AccountIDType, BaseSettings

    class AccountListButtonQueryRow(TypedDict):
        display_name: str
        twitch_id: int
        # fake, query row has more keys

    class AccountListButtonPlayerSortDict(TypedDict):
        name: str
        accounts: list[str]


class FPCView(AluView):
    def __init__(self, cog: BaseSettings, *, author_id: int | None) -> None:
        super().__init__(
            author_id=author_id,
            view_name=f"{cog.game_display_name} Favourite Player+Character Setup menu",
        )
        self.cog: BaseSettings = cog

    @override
    async def on_timeout(self) -> None:
        await super().on_timeout()
        self.cog.setup_messages_cache.pop(self.message.id, None)


class SetupChannel(FPCView):
    """View for a command `/{game} setup channel`.

    This gives
    * Dropdown menu to select a new channel for notifications.
    """

    def __init__(self, cog: BaseSettings, *, author_id: int | None, embed: discord.Embed) -> None:
        super().__init__(cog, author_id=author_id)
        self.embed: discord.Embed = embed

    @discord.ui.select(
        cls=discord.ui.ChannelSelect,
        channel_types=[discord.ChannelType.text, discord.ChannelType.news],
        placeholder="\N{BIRD} Select a new FPC notifications Channel",
        row=0,
    )
    async def set_channel(
        self, interaction: discord.Interaction[AluBot], select: discord.ui.ChannelSelect[Self],
    ) -> None:
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
            0, name=f"Channel {formats.tick(bool(channel))}", value=channel.mention if channel else "Not set",
        )
        self.embed.set_field_at(
            1, name=f"Webhook {formats.tick(bool(webhook))}", value="Properly Set" if webhook else "Not set",
        )
        await interaction.response.edit_message(embed=self.embed)


class SetupMisc(FPCView):
    """View for a command `/{game} setup misc`.

    This gives
    * Button to disable/enable notifications for a time being
    * Button to disable/enable spoil-ing post-match results
    * Button to delete user's FPC data from the database
    """

    def __init__(
        self,
        cog: BaseSettings,
        embed: discord.Embed,
        *,
        author_id: int,
    ) -> None:
        super().__init__(cog, author_id=author_id)
        self.embed: discord.Embed = embed

    async def toggle_worker(self, interaction: discord.Interaction[AluBot], setting: str, field_index: int) -> None:
        query = f"""
            UPDATE {self.cog.prefix}_settings
            SET {setting}=not({setting})
            WHERE guild_id = $1
            RETURNING {setting}
        """
        new_value: bool = await interaction.client.pool.fetchval(query, interaction.guild_id)

        old_field_name = self.embed.fields[field_index].name
        assert isinstance(old_field_name, str)
        new_field_name = f'{old_field_name.split(":")[0]}: {"`on`" if new_value else "`off`"} {formats.tick(new_value)}'
        old_field_value = self.embed.fields[field_index].value
        self.embed.set_field_at(field_index, name=new_field_name, value=old_field_value, inline=False)
        await interaction.response.edit_message(embed=self.embed)

    @discord.ui.button(emoji="\N{BLACK SQUARE FOR STOP}", label='Toggle "Receive Notifications Setting"', row=0)
    async def toggle_enable(self, interaction: discord.Interaction[AluBot], _: discord.ui.Button[Self]) -> None:
        await self.toggle_worker(interaction, "enabled", 0)

    @discord.ui.button(emoji="\N{MICROSCOPE}", label='Toggle "Show Post-Match Results Setting"', row=1)
    async def toggle_spoil(self, interaction: discord.Interaction[AluBot], _: discord.ui.Button[Self]) -> None:
        await self.toggle_worker(interaction, "spoil", 1)

    @discord.ui.button(emoji="\N{CLAPPER BOARD}", label='Toggle "Only Twitch Live Players Setting"', row=2)
    async def toggle_twitch_live_only(
        self, interaction: discord.Interaction[AluBot], _: discord.ui.Button[Self],
    ) -> None:
        await self.toggle_worker(interaction, "twitch_live_only", 2)

    @discord.ui.button(
        label="Delete Your Data and Stop Notifications",
        style=discord.ButtonStyle.red,
        emoji="\N{WASTEBASKET}",
        row=3,
    )
    async def delete_data(self, interaction: discord.Interaction[AluBot], _: discord.ui.Button[Self]) -> None:
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
                    f"\N{BLACK CIRCLE} your favourite {self.cog.character_plural} data\n"
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
                item.disabled = True  # type: ignore
            await view.message.edit(view=view)

        # Disable the Channel
        query = f"DELETE FROM {self.cog.prefix}_settings WHERE guild_id=$1"
        await interaction.client.pool.execute(query, interaction.guild_id)

        response_embed = discord.Embed(
            colour=discord.Colour.green(),
            title="FPC (Favourite Player+Character) channel removed.",
            description="Notifications will not be sent anymore. Your data was deleted as well.",
        ).set_author(name=self.cog.game_display_name, icon_url=self.cog.game_icon_url)
        await interaction.followup.send(embed=response_embed)


class PlayersPageSource(menus.ListPageSource):
    """Page source for both commands `/{game} setup players`."""

    def __init__(self, data: list[tuple[int, str]]) -> None:
        super().__init__(entries=data, per_page=20)

    @override
    async def format_page(self, menu: SetupPlayersPaginator, entries: list[tuple[int, str]]) -> discord.Embed:
        """Create a page for `/{game} setup {characters/players}` command.

        This gives
         * Embed with explanation text
         * Buttons to add/remove characters to/from favourite list.

        Parameters
        ----------
        entries:
            List of (id, name) tuples,
            for example: [(1, "gosu"), (2, "Quantum"), ...].

        """
        # unfortunately we have to fetch favourites each format page
        # in case they are bad acting with using both slash commands
        # or several menus
        cog = menu.cog

        query = f"SELECT player_id FROM {cog.prefix}_favourite_players WHERE guild_id=$1"
        assert menu.ctx_ntr.guild
        favourite_ids: list[int] = [r for (r,) in await menu.ctx_ntr.client.pool.fetch(query, menu.ctx_ntr.guild.id)]

        menu.clear_items()

        embed = (
            discord.Embed(
                colour=menu.cog.colour,
                title=f"Your favourite {menu.cog.game_display_name} {cog.character_plural} list interactive setup",
                description=f"Menu below represents all {cog.character_plural} from {cog.game_display_name}.",
            )
            .add_field(
                name="\N{LARGE GREEN SQUARE}/\N{BLACK LARGE SQUARE} Buttons",
                value=(
                    f"Press those buttons to mark/demark a a {cog.character_plural} as your favourite.\n"
                    "Button's colour shows if it's currently chosen as your favourite. "
                    "(\N{LARGE GREEN SQUARE} - yes, \N{BLACK LARGE SQUARE} - no)\n"
                ),
                inline=False,
            )
            .add_field(
                name=f"{menu.favourite_players.label} Your favourite {cog.character_plural} list Button",
                value="Show your favourite players list.",
                inline=False,
            )
            .add_field(
                name="\N{PENCIL} List of accounts of players shown on the page",
                value="Show list of accounts with links to their profiles and extra information.",
                inline=False,
            )
        )

        for item in [menu.favourite_players, menu.previous_page, menu.index, menu.next_page, menu.account_list]:
            menu.add_item(item)

        for entry in entries:
            id_, name = entry
            is_favourite = id_ in favourite_ids
            menu.add_item(
                AddRemoveButton(
                    name, is_favourite, id_, table=f"{cog.prefix}_favourite_players", column="player_id", menu=menu,
                ),
            )

        return embed


class SetupPlayersPaginator(pages.Paginator):
    """A Paginator for `/{game} setup players` command.

    This gives:
    * pagination menu
    * list of favourite players button
    * buttons to mark/demark player as favourite
    * button to view all accounts for presented embed
    """

    def __init__(
        self,
        interaction: discord.Interaction[AluBot],
        player_tuples: list[tuple[int, str]],
        cog: BaseSettings,
    ) -> None:
        super().__init__(interaction, source=PlayersPageSource(player_tuples))
        self.cog: BaseSettings = cog

    @override
    async def on_timeout(self) -> None:  # TODO: do it properly, via combining FPCView and pages.Paginator as a class.
        await super().on_timeout()
        self.cog.setup_messages_cache.pop(self.message.id, None)

    @discord.ui.button(label="\N{PAGE WITH CURL}", style=discord.ButtonStyle.blurple)
    async def favourite_players(self, interaction: discord.Interaction, _: discord.ui.Button[Self]) -> None:
        """Show favourite object list."""
        assert interaction.guild
        embed = await self.cog.get_player_list_embed(interaction.guild.id)
        await interaction.response.send_message(embed=embed, ephemeral=True)

    @discord.ui.button(label="\N{PENCIL}", style=discord.ButtonStyle.blurple)
    async def account_list(self, interaction: discord.Interaction[AluBot], _: discord.ui.Button[Self]) -> None:
        """5th Button to Show account list for `/{game} setup players` command's view."""
        assert interaction.guild

        # TODO??? we need to add entries to this menu and keep them via page source?

        columns = "display_name, twitch_id, " + ", ".join(self.cog.account_table_columns)

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
                    "name": self.cog.account_cls.static_player_embed_name(row["display_name"], bool(row["twitch_id"])),
                    "accounts": [],
                }

            account_kwargs = {column: row[column] for column in self.cog.account_table_columns}
            player_dict[row["display_name"]]["accounts"].append(
                self.cog.account_cls.static_account_name_with_links(**account_kwargs),
            )

        embed = discord.Embed(
            colour=self.cog.colour,
            title="List of accounts for players shown above.",
            description="\n".join(
                f"{player['name']}\n{chr(10).join(player['accounts'])}" for player in player_dict.values()
            ),
        ).set_footer(
            text=f"to request a new account/player to be added - use `/{self.cog.prefix} request player` command",
            icon_url=self.cog.game_icon_url,
        )

        await interaction.response.send_message(embed=embed, ephemeral=True)


class CharactersPageSource(menus.ListPageSource):
    """Page source for both commands `/{game} setup {characters}`."""

    def __init__(self, data: list[Character]) -> None:
        super().__init__(entries=data, per_page=20)

    @override
    async def format_page(self, menu: SetupCharactersPaginator, entries: list[Character]) -> discord.Embed:
        """Create a page for `/{game} setup {characters}` command.

        This gives
        * Embed with explanation text
        * Buttons to add/remove characters to/from favourite list.

        Parameters
        ----------
        entries:
            List of characters

        """
        # unfortunately we have to fetch favourites each format page
        # in case they are bad acting with using both slash commands
        # or several menus
        cog = menu.cog

        query = f"SELECT character_id FROM {cog.prefix}_favourite_characters WHERE guild_id=$1"
        assert menu.ctx_ntr.guild
        favourite_ids: list[int] = [r for (r,) in await menu.ctx_ntr.client.pool.fetch(query, menu.ctx_ntr.guild.id)]

        menu.clear_items()

        embed = (
            discord.Embed(
                colour=cog.colour,
                title=f"Your favourite {cog.game_display_name} {cog.character_plural} list interactive setup",
                description=f"Menu below represents all {cog.character_plural} from {cog.game_display_name}.",
            )
            .add_field(
                name="\N{LARGE GREEN SQUARE}/\N{BLACK LARGE SQUARE} Buttons",
                value=(
                    f"Press those buttons to mark/demark a a {cog.character_singular} as your favourite.\n"
                    "Button's colour shows if it's currently chosen as your favourite. "
                    "(\N{LARGE GREEN SQUARE} - yes, \N{BLACK LARGE SQUARE} - no)\n"
                ),
                inline=False,
            )
            .add_field(
                name=f"{menu.favourite_characters.label} Your favourite {cog.character_plural} list Button",
                value=f"Show your favourite {cog.character_plural} list.",
                inline=False,
            )
        )

        for item in [menu.favourite_characters, menu.previous_page, menu.index, menu.next_page, menu.search]:
            menu.add_item(item)

        for character in entries:
            is_favourite = character.id in favourite_ids
            menu.add_item(
                AddRemoveButton(
                    character.display_name,
                    is_favourite,
                    character.id,
                    emoji=character.emote,
                    table=f"{cog.prefix}_favourite_characters",
                    column="character_id",
                    menu=menu,
                ),
            )

        return embed


class SetupCharactersPaginator(pages.Paginator):
    """A Paginator for `/{game} setup characters` command.

    This gives:
    * pagination menu
    * list of favourite characters button
    * buttons to mark/demark character as favourite
    """

    def __init__(
        self,
        interaction: discord.Interaction[AluBot],
        characters: list[Character],
        cog: BaseSettings,
    ) -> None:
        super().__init__(interaction, source=CharactersPageSource(characters))
        self.cog: BaseSettings = cog

    @override
    async def on_timeout(self) -> None:  # TODO: do it properly, via combining FPCView and pages.Paginator as a class.
        await super().on_timeout()
        self.cog.setup_messages_cache.pop(self.message.id, None)

    @discord.ui.button(label="\N{PAGE WITH CURL}", style=discord.ButtonStyle.blurple)
    async def favourite_characters(self, interaction: discord.Interaction, _: discord.ui.Button[Self]) -> None:
        """Show favourite object list."""
        assert interaction.guild
        embed = await self.cog.get_character_list_embed(interaction.guild.id)
        await interaction.response.send_message(embed=embed, ephemeral=True)


class AddRemoveButton(discord.ui.Button[SetupCharactersPaginator | SetupCharactersPaginator]):
    """Green/Black Buttons to Remove from/Add to favourite list.

    Used for `/{game} setup players/{characters}` command's view.
    """

    def __init__(
        self,
        label: str,
        is_favourite: bool,
        object_id: int,
        *,
        table: str,
        column: str,
        menu: SetupCharactersPaginator | SetupPlayersPaginator,
        emoji: str | None = None,
    ) -> None:
        super().__init__(
            emoji=emoji,
            style=discord.ButtonStyle.green if is_favourite else discord.ButtonStyle.gray,
            label=label,
        )
        self.is_favourite: bool = is_favourite
        self.object_id: int = object_id
        self.table: str = table
        self.column: str = column
        self.menu: SetupCharactersPaginator | SetupPlayersPaginator = menu

    @override
    async def callback(self, interaction: discord.Interaction[AluBot]) -> None:
        assert interaction.guild

        if self.is_favourite:
            # delete from the favourites list
            query = f"DELETE FROM {self.table} WHERE guild_id=$1 AND {self.column}=$2"
        else:
            # add to the favourites list
            query = f"""
                INSERT INTO {self.table}
                (guild_id, {self.column})
                VALUES ($1, $2)
                ON CONFLICT DO NOTHING
            """
        await interaction.client.pool.execute(query, interaction.guild.id, self.object_id)

        # Edit the message with buttons
        self.is_favourite = not self.is_favourite
        self.style = discord.ButtonStyle.green if self.is_favourite else discord.ButtonStyle.gray
        await interaction.response.edit_message(view=self.menu)


# DATABASE REMOVE VIEWS


class DatabaseRemoveView(AluView):
    """View for `/database {game} remove` command.

    This shows
    * Remove all accounts for the said player
    * List of buttons to remove each known account for the said player.
    """

    def __init__(
        self,
        author_id: int,
        cog: BaseSettings,
        player_id: int,
        player_name: str,
        account_ids_names: Mapping[AccountIDType, str],
        account_id_column: str,
    ) -> None:
        super().__init__(
            author_id=author_id,
            view_name="Database Remove View",
        )

        self.add_item(RemoveAllAccountsButton(cog, player_id, player_name))

        for counter, (account_id, account_name) in enumerate(account_ids_names.items()):
            percent_counter = (counter + 1) % 10
            self.add_item(
                RemoveAccountButton(const.DIGITS[percent_counter], cog, account_id, account_name, account_id_column),
            )


class RemoveAllAccountsButton(discord.ui.Button[DatabaseRemoveView]):
    """Button to remove all specific player's accounts in  `/database {game} remove` command's view."""

    def __init__(self, cog: BaseSettings, player_id: int, player_name: str) -> None:
        super().__init__(
            style=discord.ButtonStyle.red,
            label=f"Remove all {player_name}'s accounts.",
            emoji="\N{POUTING FACE}",
        )
        self.cog: BaseSettings = cog
        self.player_id: int = player_id
        self.player_name: str = player_name

    @override
    async def callback(self, interaction: discord.Interaction[AluBot]) -> None:
        query = f"DELETE FROM {self.cog.prefix}_players WHERE player_id=$1"
        result: str = await interaction.client.pool.execute(query, self.player_id)

        if result != "DELETE 1":
            msg = "Error deleting this player from the database."
            raise errors.BadArgument(msg)

        embed = discord.Embed(colour=self.cog.colour).add_field(
            name="Successfully removed a player from the database",
            value=self.player_name,
        )
        await interaction.response.send_message(embed=embed)


class RemoveAccountButton(discord.ui.Button[DatabaseRemoveView]):
    """Button to remove a specific player's account in  `/database {game} remove` command's view."""

    def __init__(
        self,
        emoji: str,
        cog: BaseSettings,
        account_id: AccountIDType,
        account_name: str,
        account_id_column: str,
    ) -> None:
        super().__init__(
            style=discord.ButtonStyle.blurple,
            label=account_name,
            emoji=emoji,
        )
        self.cog: BaseSettings = cog
        self.account_id: AccountIDType = account_id
        self.account_id_column: str = account_id_column

    @override
    async def callback(self, interaction: discord.Interaction[AluBot]) -> None:
        query = f"DELETE FROM {self.cog.prefix}_accounts WHERE {self.account_id_column} = $1"
        result: str = await interaction.client.pool.execute(query, self.account_id)
        if result != "DELETE 1":
            msg = "Error deleting this account from the database."
            raise errors.BadArgument(msg)

        embed = discord.Embed(colour=self.cog.colour).add_field(
            name="Successfully removed an account from the database",
            value=self.label,
        )
        await interaction.response.send_message(embed=embed)
