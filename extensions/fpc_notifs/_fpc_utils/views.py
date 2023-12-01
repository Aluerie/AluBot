from __future__ import annotations

from typing import TYPE_CHECKING

import discord
from discord.ext import menus

from utils.pages import Paginator

if TYPE_CHECKING:
    from bot import AluBot
    from utils import AluGuildContext


class CharacterButton(discord.ui.Button):
    def __init__(self, label: str, is_fav: bool, character_id: int, menu):
        super().__init__(
            style=discord.ButtonStyle.green if is_fav else discord.ButtonStyle.gray,
            label=label,
        )
        self.is_fav: bool = is_fav
        self.character_id: int = character_id
        self.menu: CharacterPages = menu
        self.game: str = menu.game

    async def callback(self, ntr: discord.Interaction[AluBot]):
        assert ntr.guild

        if self.is_fav:
            # delete from the favourites list
            query = f"""DELETE FROM {self.game}_favourite_characters WHERE guild_id=$1 AND character_id=$2"""
        else:
            # add to the favourites list
            query = f"""INSERT INTO {self.game}_favourite_characters (guild_id, character_id) 
                        VALUES ($1, $2)
                        ON CONFLICT DO NOTHING
                    """

        await ntr.client.pool.execute(query, ntr.guild.id, self.character_id)
        self.is_fav = not self.is_fav
        self.style = discord.ButtonStyle.green if self.is_fav else discord.ButtonStyle.gray
        await ntr.response.edit_message(view=self.menu)


class CharacterPageSource(menus.ListPageSource):
    def __init__(self, data):
        super().__init__(entries=data, per_page=20)
        # self.data: List[Tuple[int, str]] = data

    def character_page_embed(self, menu: CharacterPages) -> discord.Embed:
        e = discord.Embed(colour=menu.colour)
        e.title = f"Your favourite {menu.gather_word} list interactive setup"

        e.description = (
            f"Below there is a pagination menu representing each character from {menu.game}. "
            "Button's colour shows if it's chosen as your favourite. "
            "Press the buttons to mark/demark as favourites."
        )
        e.add_field(name="Green Buttons\N{LARGE GREEN SQUARE}", value=f"Your favourite {menu.gather_word}.")
        e.add_field(name="Gray Buttons\N{BLACK LARGE SQUARE}", value=f"Your non-favourite {menu.gather_word}.")
        return e

    async def format_page(self, menu: CharacterPages, entries: list[tuple[int, str]]):
        """

        ----
        Entries in this case are [(1, "Anti-Mage), (2, Axe), ...] kind of tuples.
        """

        # unfortunately we have to fetch fav characters each format page
        # in case they are bad acting with using both slash commands
        # or several menus
        query = f"SELECT character_id FROM {menu.game}_favourite_characters WHERE guild_id=$1"
        assert menu.ctx_ntr.guild
        fav_ids: list[int] = [r for r, in await menu.ctx_ntr.client.pool.fetch(query, menu.ctx_ntr.guild.id)]

        menu.clear_items()
        menu.fill_items()

        for entry in entries:
            id_, name = entry
            is_fav = id_ in fav_ids
            menu.add_item(CharacterButton(name, is_fav, id_, menu))

        e = self.character_page_embed(menu)
        return e


class CharacterPages(Paginator):
    source: CharacterPageSource

    def __init__(
        self,
        ctx: AluGuildContext,
        source: CharacterPageSource,
        game: str,
        colour: discord.Colour,
        gather_word: str,
    ):
        super().__init__(ctx, source)
        self.game: str = game
        self.colour: discord.Colour = colour
        self.gather_word: str = gather_word
