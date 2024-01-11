from __future__ import annotations

from typing import TYPE_CHECKING, Awaitable, Callable, Optional, TypedDict

import discord
from discord.ext import menus

from utils import AluView, const, errors, formats, pages

if TYPE_CHECKING:
    from bot import AluBot
    from utils import AluGuildContext

    from .base_settings import FPCSettingsBase, GameData

    class AccountListButtonQueryRow(TypedDict):
        display_name: str
        twitch_id: int
        # fake, query row has more keys

    class PlayerDict(TypedDict):
        name: str
        accounts: list[str]


class FPCChannelSetupView(AluView):
    def __init__(self, game: GameData, author_id: int):
        super().__init__(author_id=author_id)
        self.game: GameData = game

    @discord.ui.select(
        cls=discord.ui.ChannelSelect,
        channel_types=[discord.ChannelType.text],
        placeholder="\N{BIRD} Select a new FPC notifications Channel",
        row=0,
    )
    async def set_channel(self, ntr: discord.Interaction[AluBot], select: discord.ui.ChannelSelect):
        chosen_channel = select.values[0]  # doesn't have all data thus we need to resolve
        channel = chosen_channel.resolve() or await chosen_channel.fetch()

        # probably not needed but who knows what type of channels Discord will make one day
        if not isinstance(channel, discord.TextChannel):
            raise errors.ErroneousUsage(
                f"You can't select a channel of this type for {self.game.display_name} FPC channel."
                "Please, select normal text channel."
            )

        if not channel.permissions_for(channel.guild.me).send_messages:
            raise errors.ErroneousUsage(
                "I do not have permission to `send_messages` in that channel. "
                "Please, select a channel where I can do that so I'm able to send notifications in future."
            )

        query = f"""INSERT INTO {self.game.prefix}_settings (guild_id, guild_name, channel_id)
                    VALUES ($1, $2, $3)
                    ON CONFLICT (guild_id) DO UPDATE
                        SET channel_id=$3;
                """
        await ntr.client.pool.execute(query, channel.guild.id, channel.guild.name, channel.id)

        embed = discord.Embed(
            colour=self.game.colour,
            title=f"{self.game.display_name} FPC (Favourite Player+Character) channel was set",
            description=f"From now on I will send FPC Notifications to {channel.mention}.",
        ).set_author(name=self.game.display_name, icon_url=self.game.icon_url)
        return await ntr.response.send_message(embed=embed)


class FPCSetupMiscView(AluView):
    def __init__(
        self,
        game: GameData,
        embed: discord.Embed,
        *,
        author_id: int,
    ):
        super().__init__(author_id=author_id)
        self.game: GameData = game
        self.embed: discord.Embed = embed

    async def toggle_worker(self, interaction: discord.Interaction[AluBot], setting: str, field_index: int):
        query = f"""
            UPDATE {self.game.prefix}_settings 
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

    @discord.ui.button(emoji="\N{BLACK SQUARE FOR STOP}", label='Toggle "Receive Notifications Setting"')
    async def toggle_enable(self, interaction: discord.Interaction[AluBot], _: discord.ui.Button):
        await self.toggle_worker(interaction, "enabled", 0)

    @discord.ui.button(emoji="\N{MICROSCOPE}", label='Toggle "Show Post-Match Results Setting"')
    async def toggle_spoil(self, interaction: discord.Interaction[AluBot], _: discord.ui.Button):
        await self.toggle_worker(interaction, "spoil", 1)

    @discord.ui.button(
        label="Delete Your Data and Stop Notifications",
        style=discord.ButtonStyle.red,
        emoji="\N{WASTEBASKET}",
    )
    async def delete_data(self, interaction: discord.Interaction[AluBot], _: discord.ui.Button):
        # Confirmation
        confirm_embed = (
            discord.Embed(
                colour=self.game.colour,
                title="Confirmation Prompt",
                description=(
                    f"Are you sure you want to stop {self.game.display_name} FPC Notifications and delete your data?"
                ),
            )
            .set_author(name=self.game.display_name, icon_url=self.game.icon_url)
            .add_field(
                name="The data that will be deleted",
                value=(
                    f"\N{BLACK CIRCLE} your favourite players data\n"
                    f"\N{BLACK CIRCLE} your favourite {self.game.character_plural_word} data\n"
                    f"\N{BLACK CIRCLE} your {self.game.character_plural_word} FPC Notifications channel data."
                ),
            )
        )

        if not interaction.client.disambiguator.confirm(interaction, confirm_embed):
            return

        # Disable the Channel
        query = f"DELETE FROM {self.game.prefix}_settings WHERE guild_id=$1"
        await interaction.client.pool.execute(query, interaction.guild_id)

        response_embed = discord.Embed(
            colour=discord.Colour.green(),
            title="FPC (Favourite Player+Character) channel removed.",
            description=f"Notifications will not be sent anymore. Your data was deleted as well.",
        ).set_author(name=self.game.display_name, icon_url=self.game.icon_url)
        await interaction.followup.send(embed=response_embed)


class AddRemoveButton(discord.ui.Button):
    def __init__(self, label: str, is_favourite: bool, object_id: int, menu: FPCSetupPaginator):
        super().__init__(
            style=discord.ButtonStyle.green if is_favourite else discord.ButtonStyle.gray,
            label=label,
        )
        self.is_favourite: bool = is_favourite
        self.object_id: int = object_id
        self.menu: FPCSetupPaginator = menu

    async def callback(self, ntr: discord.Interaction[AluBot]):
        assert ntr.guild

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
        await ntr.client.pool.execute(query, ntr.guild.id, self.object_id)

        # Edit the message with buttons
        self.is_favourite = not self.is_favourite
        self.style = discord.ButtonStyle.green if self.is_favourite else discord.ButtonStyle.gray
        await ntr.response.edit_message(view=self.menu)


class AccountListButton(discord.ui.Button):
    def __init__(self, entries: list[tuple[int, str]], menu: FPCSetupPaginator):
        super().__init__(
            style=discord.ButtonStyle.blurple,
            label="\N{PENCIL}",
        )
        self.entries: list[tuple[int, str]] = entries
        self.menu: FPCSetupPaginator = menu

    async def callback(self, ntr: discord.Interaction[AluBot]):
        assert ntr.guild

        columns = "display_name, twitch_id, " + ", ".join(self.menu.cog.account_table_columns)

        query = f"""
            SELECT {columns}
            FROM {self.menu.game.prefix}_players p
            JOIN {self.menu.game.prefix}_accounts a
            ON p.player_id = a.player_id
            ORDER BY display_name
        """
        rows: list[AccountListButtonQueryRow] = await ntr.client.pool.fetch(query) or []

        player_dict: dict[str, PlayerDict] = {}
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
            colour=self.menu.game.colour,
            title="List of accounts for players shown above.",
            description="\n".join(
                f"{player['name']}\n{chr(10).join(player['accounts'])}" for player in player_dict.values()
            ),
        ).set_footer(text=self.menu.game.display_name, icon_url=self.menu.game.icon_url)

        await ntr.response.send_message(embed=embed, ephemeral=True)


class FPCSetupPageSource(menus.ListPageSource):
    def __init__(self, data: list[tuple[int, str]]):
        super().__init__(entries=data, per_page=20)

    async def format_page(self, menu: FPCSetupPaginator, entries: list[tuple[int, str]]):
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

        if menu.special_button_cls is None:
            special_item = menu.search
        else:
            special_item = menu.special_button_cls(entries, menu)
        for item in [menu.object_list, menu.previous_page, menu.index, menu.next_page, special_item]:
            menu.add_item(item)

        for entry in entries:
            id, name = entry
            is_favourite = id in favourite_ids
            menu.add_item(AddRemoveButton(name, is_favourite, id, menu))

        description = (
            f"Pagination menu below represents all {menu.plural} from {menu.game.display_name}.\n"
            "\N{BLACK CIRCLE} Button's colour shows if it's chosen as your favourite. "
            "(\N{LARGE GREEN SQUARE} - yes, \N{BLACK LARGE SQUARE} - no)\n"
            "\N{BLACK CIRCLE} Press the \N{LARGE GREEN SQUARE}/\N{BLACK LARGE SQUARE} "
            f"buttons to mark/demark a {menu.singular} as your favourite.\n"
            f"\N{BLACK CIRCLE} Press {menu.object_list.label} to show your favourite {menu.plural} list.\n"
        )
        return discord.Embed(
            colour=menu.game.colour,
            title=f"Your favourite {menu.game.display_name} {menu.plural} list interactive setup",
            description=description,
        )


class FPCSetupPaginator(pages.Paginator):
    def __init__(
        self,
        ctx: AluGuildContext,
        object_id_name_tuples: list[tuple[int, str]],
        game: GameData,
        table_object_name: str,
        singular: str,
        plural: str,
        cog: FPCSettingsBase,
        get_object_list_embed: Callable[[int], Awaitable[discord.Embed]],
        special_button_cls: Optional[type[AccountListButton]] = None,
    ):
        super().__init__(
            ctx,
            source=FPCSetupPageSource(object_id_name_tuples),
        )
        self.game: GameData = game
        self.singular: str = singular
        self.plural: str = plural  # "heroes" #todo: docs
        self.cog: FPCSettingsBase = cog
        self.get_object_list_embed: Callable[[int], Awaitable[discord.Embed]] = get_object_list_embed

        self.table_name: str = f"{game.prefix}_favourite_{table_object_name}s "
        self.id_column_name: str = f"{table_object_name}_id"
        self.special_button_cls = special_button_cls

    @discord.ui.button(label="\N{PAGE WITH CURL}", style=discord.ButtonStyle.blurple)
    async def object_list(self, ntr: discord.Interaction, _: discord.ui.Button):
        """Show favourite object list."""
        assert ntr.guild
        embed = await self.get_object_list_embed(ntr.guild.id)
        await ntr.response.send_message(embed=embed, ephemeral=True)


class FPCSetupPlayersPaginator(FPCSetupPaginator):
    def __init__(
        self,
        ctx: AluGuildContext,
        player_tuples: list[tuple[int, str]],
        cog: FPCSettingsBase,
    ):
        super().__init__(
            ctx,
            player_tuples,
            cog.game,
            "player",
            "player",
            "players",
            cog,
            cog.get_player_list_embed,
            AccountListButton,
        )


class FPCSetupCharactersPaginator(FPCSetupPaginator):
    def __init__(
        self,
        ctx: AluGuildContext,
        character_tuples: list[tuple[int, str]],
        cog: FPCSettingsBase,
    ):
        super().__init__(
            ctx,
            character_tuples,
            cog.game,
            "character",
            cog.game.character_singular_word,
            cog.game.character_plural_word,
            cog,
            cog.get_character_list_embed,
        )


### DATABASE REMOVE VIEWS


class RemoveAllAccountsButton(discord.ui.Button):
    def __init__(self, game: GameData, player_id: int, player_name: str):
        super().__init__(
            style=discord.ButtonStyle.red,
            label=f"Remove all {player_name}'s accounts.",
            emoji="\N{POUTING FACE}",
        )
        self.game: GameData = game
        self.player_id: int = player_id
        self.player_name: str = player_name

    async def callback(self, ntr: discord.Interaction[AluBot]):
        query = f"DELETE FROM {self.game.prefix}_players WHERE player_id=$1"
        result: str = await ntr.client.pool.execute(query, self.player_id)

        if result != "DELETE 1":
            raise errors.BadArgument("Error deleting this player from the database.")

        embed = discord.Embed(colour=self.game.colour).add_field(
            name="Succesfully removed a player from the database",
            value=self.player_name,
        )
        await ntr.response.send_message(embed=embed)


class RemoveAccountButton(discord.ui.Button):
    def __init__(self, emoji: str, game: GameData, account_id: str | int, account_name: str, account_id_column: str):
        super().__init__(
            style=discord.ButtonStyle.blurple,
            label=account_name,
            emoji=emoji,
        )
        self.game: GameData = game
        self.account_id: str | int = account_id
        self.account_id_column: str = account_id_column

    async def callback(self, interaction: discord.Interaction[AluBot]):
        query = f"DELETE FROM {self.game.prefix}_accounts WHERE {self.account_id_column} = $1"
        result: str = await interaction.client.pool.execute(query, self.account_id)
        if result != "DELETE 1":
            raise errors.BadArgument("Error deleting this account from the database.")

        embed = discord.Embed(colour=self.game.colour).add_field(
            name="Succesfully removed an account from the database",
            value=self.label,
        )
        await interaction.response.send_message(embed=embed)


class DatabaseRemoveView(AluView):
    def __init__(
        self,
        author_id: int,
        game: GameData,
        player_id: int,
        player_name: str,
        account_ids_names: dict[int | str, str],
        account_id_column: str,
    ):
        super().__init__(
            author_id=author_id,
            view_name="Database Remove View",
        )

        self.add_item(RemoveAllAccountsButton(game, player_id, player_name))

        for counter, (account_id, account_name) in enumerate(account_ids_names.items()):
            percent_counter = (counter + 1) % 10
            self.add_item(
                RemoveAccountButton(const.DIGITS[percent_counter], game, account_id, account_name, account_id_column)
            )
