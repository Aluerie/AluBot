"""
The pagination was quite a struggle.

Sources I used to create this file and files that are dependent on it:

* pagination walk gist from InterStella0
    - https://gist.github.com/InterStella0/454cc51e05e60e63b81ea2e8490ef140
* help walk gist from InterStella0
    - https://gist.github.com/InterStella0/b78488fb28cadf279dfd3164b9f0cf96$syn
* past fork of it that still has View section
    - https://gist.github.com/Shashank3736/44c124dcaa5c4fdddc0300bec575dc08
* RoboDanny's meta/pagination files (license MPL v2 from Rapptz/RoboDanny)
    - https://github.com/Rapptz/RoboDanny/blob/rewrite/cogs/utils/paginator.py
* In past, before implementing `discord.ext.menus` version - my code was
    based of @krittick's `ext.pages` from `pycord` library (The MIT License (MIT))
    (Yes-yes-yes-yes, don't bully me - I was using `pycord` while
    `discord.py` was taking "an indefinite break" - let's call it like that).
    Unfortunately, @krittick had to leave py-cord team and nobody maintained `ext.pages` since.
    By that time `discord.py` library came back to life and quickly became
    arguably the best python library for discord API wrapping (again).
    Thus, I decided to switch back to `discord.py` and so to bring pagination code
    from `py-cord's .ext.pages` here as well.
    But you can still see elements from there in my code. So mentioning the source for posterity:

    - https://github.com/Pycord-Development/pycord/blob/master/discord/ext/pages/pagination.py
"""

from __future__ import annotations

from typing import TYPE_CHECKING, Any, Dict, List, Optional, Union

import discord
from discord.ext import menus

from .var import Clr, Ems

if TYPE_CHECKING:
    from .context import Context


class IndexModal(discord.ui.Modal, title="Go to page"):
    goto = discord.ui.TextInput(label="Page Number", min_length=1, required=True)

    def __init__(self, paginator: Paginator):
        super().__init__()
        self.paginator: Paginator = paginator

        self.max_pages_as_str = m = str(paginator.source.get_max_pages())
        self.goto.max_length = len(m)
        self.goto.placeholder = f"Enter a number between 1 and {m}"

    async def on_submit(self, ntr: discord.Interaction):
        if self.paginator.is_finished():
            e = discord.Embed(colour=Clr.error, description="Took too long")
            await ntr.response.send_message(embed=e, ephemeral=True)
            return

        value = str(self.goto.value)
        if not value.isdigit():
            e = discord.Embed(colour=Clr.error)
            e.description = f"Expected a page number between 1 and {self.max_pages_as_str}, not {value!r}"
            await ntr.response.send_message(embed=e, ephemeral=True)
            return

        new_page_number = int(self.goto.value) - 1
        await self.paginator.show_page(ntr, new_page_number)


class SearchModal(discord.ui.Modal, title="Search Page by query"):
    search = discord.ui.TextInput(label="Search Query", required=True)

    def __init__(self, paginator):
        super().__init__()
        self.paginator: Paginator = paginator

    # async def on_submit(self, ntr: discord.Interaction):
    #     a = self.search.value
    #
    #     for idx, page in enumerate(self.paginator.pages):
    #         page_content = self.paginator.get_page_content(page)
    #
    #         b = '\n'.join(
    #             [str(e.to_dict().values()) for e in page_content.embeds],
    #         )
    #
    #         if a in b:
    #             found_page = idx
    #     if found_page is None:
    #         return await ntr.response.send_message(
    #             content=f"I found nothing with your search query {Ems.PepoBeliever}",
    #             ephemeral=True
    #         )
    #     await self.paginator.goto_page(page_number=found_page, ntr=ntr)


class Paginator(discord.ui.View):

    # Currently only accept Context class, so
    # it's only usable in text or hybrid commands
    # (but looks like it's enough)
    # ToDO: Implement `self.ntr: Optional[Interaction] = ntr` and all
    def __init__(self, ctx: Context, source: menus.PageSource):
        super().__init__()
        self.ctx: Context = ctx
        self.source: menus.PageSource = source
        self.message: Optional[discord.Message] = None
        self.current_page_number: int = 0
        self.clear_items()
        self.fill_items()

    def fill_items(self):
        if self.source.is_paginating():
            for item in [self.home_page, self.previous_page, self.index, self.next_page, self.search]:
                self.add_item(item)

    async def _get_kwargs_from_page(self, page: int) -> Dict[str, Any]:
        value = await discord.utils.maybe_coroutine(self.source.format_page, self, page)
        if isinstance(value, dict):
            return value
        elif isinstance(value, str):
            return {"content": value, "embed": None}
        elif isinstance(value, discord.Embed):
            return {"embed": value, "content": None}
        else:
            return {}

    async def show_page(self, ntr: discord.Interaction, page_number: int) -> None:
        page = await self.source.get_page(page_number)
        self.current_page_number = page_number
        kwargs = await self._get_kwargs_from_page(page)
        self._update_nav_labels(page_number)
        if kwargs:
            if ntr.response.is_done():
                if self.message:
                    await self.message.edit(**kwargs, view=self)
            else:
                # print(kwargs)
                await ntr.response.edit_message(**kwargs, view=self)

    async def show_checked_page(self, ntr: discord.Interaction, page_number: int) -> None:
        """Just so next/prev don't IndexError me and loop correctly"""
        max_pages = self.source.get_max_pages()
        try:
            if max_pages is None:
                # if there is no max_pages - we can't check.
                await self.show_page(ntr, page_number)
            else:
                await self.show_page(ntr, page_number % max_pages)
        except IndexError:
            # we can handle it
            pass

    def update_more_labels(self, page_number: int) -> None:
        ...

    def _update_nav_labels(self, page_number: int) -> None:
        max_pages = self.source.get_max_pages()
        self.index.label = f"{page_number + 1}/{max_pages}"

        if page_number == 0:
            self.previous_page.label = "\N{RIGHTWARDS ARROW WITH HOOK}"
            self.next_page.label = ">"
        elif max_pages and page_number == max_pages - 1:
            self.previous_page.label = "<"
            self.next_page.label = "\N{LEFTWARDS ARROW WITH HOOK}"
        else:
            self.previous_page.label = "<"
            self.next_page.label = ">"
        self.update_more_labels(page_number)

    async def start(self, *, ephemeral: bool = False) -> None:
        await self.source._prepare_once()
        page = await self.source.get_page(0)
        kwargs = await self._get_kwargs_from_page(page)
        self._update_nav_labels(0)
        self.message = await self.ctx.send(**kwargs, view=self, ephemeral=ephemeral)

    async def interaction_check(self, ntr: discord.Interaction) -> bool:
        if ntr.user and ntr.user.id in (self.ctx.bot.owner_id, self.ctx.author.id):
            return True
        else:
            e = discord.Embed(colour=Clr.error)
            e.description = "This pagination menu cannot be controlled by you ! {0} {0} {0}".format(Ems.peepoWTF)
            await ntr.response.send_message(embed=e, ephemeral=True)
            return False

    async def on_timeout(self) -> None:
        if self.message:
            for item in self.children:
                # item in self.childen is Select/Button which have ``.disable`` but typehinted as Item
                item.disabled = True  # type: ignore
            await self.message.edit(view=self)

    # todo: change those for debugging reasons pepega
    async def on_error(self, ntr: discord.Interaction, error: Exception, item: discord.ui.Item) -> None:
        if ntr.response.is_done():
            await ntr.followup.send(f"Some error occurred, sorry", ephemeral=True)
        else:
            await ntr.response.send_message(f"Some error occurred, sorry", ephemeral=True)
        await ntr.client.send_traceback(error, where="Paginator")  # type: ignore

    @discord.ui.button(label="\N{HOUSE BUILDING}", style=discord.ButtonStyle.blurple)
    async def home_page(self, ntr: discord.Interaction, _btn: discord.ui.Button):
        """Show the very first page, kinda standard"""
        await self.show_page(ntr, 0)

    @discord.ui.button(label="<", style=discord.ButtonStyle.red)
    async def previous_page(self, ntr: discord.Interaction, _btn: discord.ui.Button):
        """Go to previous page"""
        await self.show_checked_page(ntr, self.current_page_number - 1)

    @discord.ui.button(label="/", style=discord.ButtonStyle.gray)
    async def index(self, ntr: discord.Interaction, _btn: discord.ui.Button):
        """Choose page using modal; this button also has label to show current_page/maximum"""
        await ntr.response.send_modal(IndexModal(self))

    @discord.ui.button(label=">", style=discord.ButtonStyle.green)
    async def next_page(self, ntr: discord.Interaction, _btn: discord.ui.Button):
        """Go to next page"""
        await self.show_checked_page(ntr, self.current_page_number + 1)

    @discord.ui.button(label="\N{RIGHT-POINTING MAGNIFYING GLASS}", style=discord.ButtonStyle.blurple)
    async def search(self, ntr: discord.Interaction, _btn: discord.ui.Button):
        """Fuzzy search in all pages and go the page with most likely similarity"""
        # todo: implement PaginatorSearchModal
        await ntr.response.send_message("sorry, the search feature is disabled for now", ephemeral=True)

    @discord.ui.button(
        label="\N{ANTICLOCKWISE DOWNWARDS AND UPWARDS OPEN CIRCLE ARROWS}", style=discord.ButtonStyle.blurple
    )
    async def refresh(self, ntr: discord.Interaction, _btn: discord.ui.Button):
        """Refresh current page.

        Useful for dynamic things like SetupView where people can change
        stuff using other tools than view buttons,
        i.e. text/slash commands or just delete/change role in guild settings
        """
        await self.show_page(ntr, self.current_page_number)


class EnumeratedPageSource(menus.ListPageSource):
    def __init__(self, entries, *, per_page: int, no_enumeration: Optional[bool] = False, description_prefix: str = ""):
        super().__init__(entries, per_page=per_page)
        self.description_prefix = description_prefix
        self.no_enumeration = no_enumeration

    async def format_page(self, menu: EnumeratedPages, entries: List[str]):

        if not self.no_enumeration:
            pages = []
            for idx, entry in enumerate(entries, start=menu.current_page_number * self.per_page):
                pages.append(f"`{idx + 1}` {entry}")
        else:
            pages = entries  # [f'{x}' for x in entries]  # :)

        menu.embed.description = self.description_prefix + "\n".join(pages)
        return menu.embed


class EnumeratedPages(Paginator):
    """Replacement for my old `ctx.send_pages()` function.

    This serves to organise pagination for hit-parade kind of deal,
    so we have enumerated top-list across paginated embed
    """

    def __init__(
        self,
        ctx: Context,
        entries: List[str],
        *,
        per_page: int,
        no_enumeration: Optional[bool] = False,
        title: Optional[str] = None,
        description_prefix: str = "",
        colour: Optional[Union[int, discord.Colour]] = None,
        footer_text: Optional[str] = None,
        author_name: Optional[str] = None,
        author_icon: Optional[str] = None,
    ):
        # todo: if we stumble into a problem where we have description limit
        # then we can rearrange entities with
        # paginator = commands.Paginator(prefix='', suffix='', max_size=Lmt.Embed.description)
        # for page in paginator.pages
        # you can look your old ctx.send_pages command
        super().__init__(
            ctx,
            EnumeratedPageSource(
                entries, per_page=per_page, no_enumeration=no_enumeration, description_prefix=description_prefix
            ),
        )
        e = discord.Embed(title=title, colour=colour)
        if footer_text:
            e.set_footer(text=footer_text)
        if author_name:
            e.set_author(name=author_name, icon_url=author_icon)

        self.embed = e
