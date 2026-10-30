# Copyright (C) 2020-present, Irene Adler ❤ (@Aluerie).
# Licensed under MPL-2.0, see the LICENSE file for details.
"""Pagination Menus View Classes.

Unlike popular implementations for paginators, these classes do not use `discord.ext.menus`
and instead mirror some of their methods under `Paginator` class' namespace.
The principle is the same though: We need to subclass `Paginator` and implement `format_page` that
uses slice of `self.entries` returns kwargs to be send with `.send` methods, i.e. Embed or dict.

Sources
-------
* Gist by Soheab
    https://gist.github.com/Soheab/f226fc06a3468af01ea3168c95b30af8
* help walk gist from InterStella0
    - https://gist.github.com/InterStella0/b78488fb28cadf279dfd3164b9f0cf96
* past fork of it^ that still has View section
    - https://gist.github.com/Shashank3736/44c124dcaa5c4fdddc0300bec575dc08
* Rapptz/RoboDanny  (license MPL v2), meta/pagination files
    - https://github.com/Rapptz/RoboDanny/blob/rewrite/cogs/utils/paginator.py
"""

from __future__ import annotations

from typing import TYPE_CHECKING, Any, NotRequired, Self, TypedDict, override

import discord
from discord.utils import MISSING

from core import Modal, View

if TYPE_CHECKING:
    from collections.abc import Sequence

    from core import Bot, Interaction
    from shared.typings.dpy import SendKwargs


__all__ = (
    "EmbedDescriptionPaginator",
    "Paginator",
)


class IndexModal(Modal, title="Go to page"):
    """Modal for the default button "index" which allows to navigate to a custom page in the Paginator."""

    goto = discord.ui.TextInput(label="Page Number", min_length=1, required=True)

    def __init__(self, paginator: Paginator) -> None:
        super().__init__()
        self.paginator: Paginator = paginator
        self.goto.max_length = len(str(paginator.max_pages))
        self.goto.placeholder = f"Enter a number between 1 and {paginator.max_pages}"

    @override
    async def on_submit(self, interaction: Interaction) -> None:
        if self.paginator.is_finished():
            await interaction.response.send_message("Took too long", ephemeral=True)
            return

        value = str(self.goto.value)
        if not value.isdigit():
            await interaction.response.send_message(
                f"Expected a page number between 1 and {self.paginator.max_pages}, not `{value!r}`", ephemeral=True
            )
            return

        new_page_number = int(self.goto.value) - 1
        await self.paginator.show_page(interaction, new_page_number)


def label_indent(label: str | int, number: int, split_size: int = 10) -> str:
    """Pad a table label to the width of the widest row number on its page.

    Leaderboards are split into pages of `split_size` rows, so labels (row numbers and the "N" header)
    only have to be as wide as the biggest number of their page: ``9`` and ``10`` live on different pages
    but ``1`` and ``10`` don't, i.e. the first page is padded to 2 characters and the 11-20 page to 2 as well,
    while a 91-100 page is padded to 3.

    Parameters
    ----------
    label
        The label to pad.
    number
        Any row number (0-based) that belongs to the page. Use ``counter - 1`` for the row with number `counter`
        and ``offset + 1`` for the header of a page that starts after `offset` rows.
    split_size
        How many rows there are in one page.

    Returns
    -------
    str
        The label padded with spaces on the right.
    """
    last_number_on_page = (number // split_size + 1) * split_size
    return str(label).ljust(len(str(last_number_on_page)))


class Paginator(View):
    """Pagination Menu.

    Subclassing
    -----------
    Paginator by default does not handle any sort of formatting.
    For that reason, subclasses must implement the `format_page` method.

    Parameters
    ----------
    author_id: int | None = None
        Author ID for the purposes of interaction checks in View.
        If `None`, which is default, `interaction.user.id` will be passed to View constructor.

    Attributes
    ----------
    interaction: Interaction
        Interaction, with which paginator is getting invoked. It can be used in `format_page` method.
    entries: Sequence[Any]
        The sequence of items to paginate. This is used by `format_page` method as a data source.
    per_page: int = 1
        How many elements are in a page. `format_page` takes `per_page` amount of entries.
    max_pages: int
        Total amount of pages in the paginator.
    current_page_number: int = 0
        Number of current page that we are in. Zero-indexed between [0, `self.max_pages`).

    Notes
    -----
    In future, we might expand `interaction` attribute to be a general context attribute, meaning to include
    `Interaction | Context | discord.abc.Messageable` prefix commands and sending in channels without a context,
    i.e. from tasks. But, at the moment, I have no plans to invoker paginators from non-interactions.
    """

    def __init__(
        self,
        interaction: Interaction,
        entries: Sequence[Any],
        *,
        per_page: int = 1,
        author_id: int | None = None,
        timeout: float | None = 300.0,
    ) -> None:
        super().__init__(author_id=author_id or interaction.user.id, timeout=timeout)
        self.interaction: Interaction = interaction
        self.bot: Bot = interaction.client  # just a shortcut
        self.entries: Sequence[Any] = entries
        self.per_page: int = per_page
        self.max_pages: int = -(len(entries) // -per_page)  # https://stackoverflow.com/a/54585138/19217368
        self.current_page_number: int = 0

        self.clear_items()
        self.fill_items()

    def fill_items(self) -> None:
        """Default behavior for which buttons to show when starting the paginator."""
        if self.is_paginating():
            for item in [self.home_page, self.previous_page, self.index, self.next_page, self.last_page]:
                self.add_item(item)

    def is_paginating(self) -> bool:
        """Whether pagination is required."""
        return len(self.entries) > self.per_page

    async def start(
        self,
        *,
        ephemeral: bool = False,
        edit_response: bool = False,
        page_number: int = 0,
    ) -> discord.InteractionMessage | discord.WebhookMessage:
        """Start the Interactive Paginator Session.

        Parameters
        ----------
        ephemeral
            Whether the message should be ephemeral.
        edit_response
            Whether to use `.response.edit_message` instead of `.response.send_message` for interaction-based contexts.
        page_number
            Page number to start with.
        """
        page_entries = await self.get_page_entries(page_number)
        send_kwargs = await self._get_page_send_kwargs(page_entries)
        self._update_navigation_labels(page_number)

        # The arguments are spelled out instead of `**send_kwargs` on purpose: `Webhook.send` and
        # `InteractionResponse.send_message` are overloaded and type checkers can't choose an overload when
        # the keywords come from an unpacked `TypedDict`. The `.edit` methods don't even accept `file`.
        if self.interaction.response.is_done():
            message = await self.interaction.followup.send(
                content=send_kwargs.get("content", MISSING),
                embed=send_kwargs.get("embed", MISSING),
                file=send_kwargs.get("file", MISSING),
                allowed_mentions=send_kwargs.get("allowed_mentions", MISSING),
                view=self,
                ephemeral=ephemeral,
                wait=True,
            )
        elif edit_response:
            await self._edit_via_response(self.interaction, send_kwargs)
            message = await self.interaction.original_response()
        else:
            await self.interaction.response.send_message(
                content=send_kwargs.get("content", MISSING),
                embed=send_kwargs.get("embed", MISSING),
                file=send_kwargs.get("file", MISSING),
                allowed_mentions=send_kwargs.get("allowed_mentions", MISSING),
                view=self,
                ephemeral=ephemeral,
            )
            message = await self.interaction.original_response()

        self.message = message
        return message

    async def _edit_via_response(self, interaction: Interaction, send_kwargs: SendKwargs) -> None:
        """Edit the message of the component/command interaction with the page.

        Unlike the sending methods, the editing ones have no `file` parameter: new files are `attachments`
        (which replace the old ones; no `file` means the attachments stay as they are).
        """
        file = send_kwargs.get("file")
        await interaction.response.edit_message(
            content=send_kwargs.get("content", MISSING),
            embed=send_kwargs.get("embed", MISSING),
            attachments=[file] if file else MISSING,
            allowed_mentions=send_kwargs.get("allowed_mentions", MISSING),
            view=self,
        )

    async def get_page_entries(self, page_number: int) -> Any | Sequence[Any]:
        """Return either a single element of the sequence or a slice of the sequence.

        If `self.per_page` is set to `1` then this returns a single element.
        Otherwise it returns at most `self.per_page` elements.

        Parameters
        ----------
        page_number: int
            The page number to access.

        Returns
        -------
        Any | List[Any]
            The data returned. This is passed into `self.format_page`.
        """
        if self.per_page == 1:
            return self.entries[page_number]
        base = page_number * self.per_page
        return self.entries[base : base + self.per_page]

    async def _get_page_send_kwargs(self, page_entries: Any | Sequence[Any]) -> SendKwargs:
        """Get send page kwargs.

        This is passed later to discord.py `.send` and `.edit` methods. The paginator's own view is always
        included, so the callers must not pass `view` separately (a duplicated keyword is an error).
        Returns an empty dictionary if `format_page` returned something unsupported.
        """
        formatted = await discord.utils.maybe_coroutine(self.format_page, page_entries)
        send_kwargs: SendKwargs
        if isinstance(formatted, dict):
            send_kwargs = formatted.copy()  # `format_page` may return a dictionary that it reuses
        elif isinstance(formatted, str):
            send_kwargs = {"content": formatted, "embed": MISSING}
        elif isinstance(formatted, discord.Embed):
            send_kwargs = {"embed": formatted, "content": MISSING}
        else:
            return {}

        send_kwargs["view"] = self
        return send_kwargs

    def format_page(self, entries: Any | Sequence[Any]) -> str | discord.Embed | SendKwargs:
        """Abstract method to format the page.

        We can also change view inside this method, for example, by adding buttons via `.add_item` methods.

        Returns
        -------
        str | discord.Embed | SendKwargs
            * If this method returns `str` then it is interpreted as
                returning `content` for discord.py's `.send` and `.edit` methods.
            * If this method returns `discord.Embed` then it is interpreted as
                returning `embed` for discord.py's `.send` and `.edit` methods.
            * If this method returns `dict` (more specifically `SendKwargs` typed dictionary) then it is interpreted as
                returning keyword arguments that are used in discord.py's `.send` and `.edit` methods.
                The `view` key is not needed: the paginator always uses itself as the view.
        """
        raise NotImplementedError

    def _update_navigation_labels(self, page_number: int) -> None:
        """Update labels for navigation buttons while paginating.

        Navigation Buttons include the following default paginator buttons:
        * previous_page;
        * next_page;
        * index;

        Parameters
        ----------
        page_number: int = 0
            Page number to update navigation labels for.
        """
        self.index.label = f"{page_number + 1}/{self.max_pages}"

        if page_number == 0:
            self.previous_page.label = "\N{RIGHTWARDS ARROW WITH HOOK}"
            self.next_page.label = ">"
        elif self.max_pages and page_number == self.max_pages - 1:
            self.previous_page.label = "<"
            self.next_page.label = "\N{LEFTWARDS ARROW WITH HOOK}"
        else:
            self.previous_page.label = "<"
            self.next_page.label = ">"

    # DEFAULT BUTTONS

    @discord.ui.button(label="\N{HOUSE BUILDING}", style=discord.ButtonStyle.blurple)
    async def home_page(self, interaction: Interaction, _: discord.ui.Button[Self]) -> None:
        """Show the very first page."""
        await self.show_page(interaction, 0)

    @discord.ui.button(label="<", style=discord.ButtonStyle.red)
    async def previous_page(self, interaction: Interaction, _: discord.ui.Button[Self]) -> None:
        """Go to the previous page."""
        await self.show_page(interaction, self.current_page_number - 1)

    @discord.ui.button(label="/", style=discord.ButtonStyle.gray)
    async def index(self, interaction: Interaction, _: discord.ui.Button[Self]) -> None:
        """Choose page using modal. This button also has label to show current_page/maximum."""
        await interaction.response.send_modal(IndexModal(self))

    @discord.ui.button(label=">", style=discord.ButtonStyle.green)
    async def next_page(self, interaction: Interaction, _: discord.ui.Button[Self]) -> None:
        """Go to the next page."""
        await self.show_page(interaction, self.current_page_number + 1)

    @discord.ui.button(label="\N{BLACK RIGHT-POINTING DOUBLE TRIANGLE}", style=discord.ButtonStyle.blurple)
    async def last_page(self, interaction: Interaction, _: discord.ui.Button[Self]) -> None:
        """Show the very last page."""
        await self.show_page(interaction, -1)

    async def show_page(self, interaction: Interaction, page_number: int) -> None:
        """Show page. Edits the paginator's message with a new page and updates navigation labels.

        Parameters
        ----------
        interaction:
            Interaction
        page_number: int
            Page number to show.
        """
        real_page_number = page_number % self.max_pages  # includes offset, i.e. page_number = -1 means last page.

        page_entries = await self.get_page_entries(real_page_number)
        send_kwargs = await self._get_page_send_kwargs(page_entries)
        self.current_page_number = real_page_number

        self._update_navigation_labels(real_page_number)
        if send_kwargs:
            if interaction.response.is_done():
                if self.message is not None:
                    file = send_kwargs.get("file")
                    await self.message.edit(
                        content=send_kwargs.get("content", MISSING),
                        embed=send_kwargs.get("embed", MISSING),
                        attachments=[file] if file else MISSING,
                        allowed_mentions=send_kwargs.get("allowed_mentions", MISSING),
                        view=self,
                    )
            else:
                await self._edit_via_response(interaction, send_kwargs)

    # EXTRA STOCK BUTTONS

    @discord.ui.button(
        label="\N{ANTICLOCKWISE DOWNWARDS AND UPWARDS OPEN CIRCLE ARROWS}",
        style=discord.ButtonStyle.blurple,
    )
    async def refresh(self, interaction: Interaction, _: discord.ui.Button[Self]) -> None:
        """Refresh current page.

        Useful for dynamic things like SetupView where people can change
        stuff using other tools than view buttons,
        i.e. text/slash commands or just delete/change role in guild settings.
        """
        await self.show_page(interaction, self.current_page_number)

    @discord.ui.button(label="\N{NO ENTRY SIGN}", style=discord.ButtonStyle.red)
    async def stop_pages(self, interaction: Interaction, _: discord.ui.Button[Self]) -> None:
        """Stop the pagination session."""
        await interaction.response.defer()
        await interaction.delete_original_response()
        self.stop()


if TYPE_CHECKING:

    class EmbedAuthorTemplate(TypedDict):
        name: str
        url: NotRequired[str]
        icon_url: NotRequired[str]

    class EmbedFooterTemplate(TypedDict):
        text: str
        icon_url: NotRequired[str]

    class EmbedTemplate(TypedDict, total=False):
        """Embed template with keys that I use the most in paginators (so it's quite incomplete).

        I mainly use this class for IDE-autocomplete purposes.

        You can find out about this format in the discord API docs:
        https://discord.com/developers/docs/resources/message#embed-object
        """

        title: str
        url: str
        color: int
        author: EmbedAuthorTemplate
        footer: EmbedFooterTemplate


class EmbedDescriptionPaginator(Paginator):
    """Paginator using `Embed.description` as showcase for string entries but with same Embed template for all pages.

    Entries are joined via line break.

    Parameters
    ----------
    empty_description
        Description to show if there are no entries at all (a paginator can't have zero pages).

    Attributes
    ----------
    template
        Embed template. This will be passed to `Embed.from_dict` classmethod to create said base embed.
        Note that description will still be built from `self.entries` and `self.description_prefix`.
    description_prefix
        Text string to be put before `entries` in each page.
    enumeration
        Whether entries should also be enumerated by `format_page`.
        Note, that if `per_page == 1` then there won't be any enumeration since that's just a singular description.
    """

    def __init__(
        self,
        interaction: Interaction,
        entries: list[str],
        *,
        template: EmbedTemplate,
        description_prefix: str = "",
        enumeration: bool = False,
        empty_description: str = "Nothing to show.",
        per_page: int = 1,
        author_id: int | None = None,
        timeout: float = 300.0,
    ) -> None:
        super().__init__(
            interaction,
            entries=entries or [empty_description],
            per_page=per_page,
            author_id=author_id,
            timeout=timeout,
        )
        self.template: EmbedTemplate = template
        self.description_prefix: str = description_prefix
        self.enumeration: bool = enumeration

    @override
    async def format_page(self, entries: str | list[str]) -> discord.Embed:  # ty: ignore[invalid-method-override]
        embed = discord.Embed.from_dict(self.template)
        if isinstance(entries, str):
            # this happens when `per_page == 1`
            embed.description = self.description_prefix + entries
        elif self.enumeration:
            start = self.current_page_number * self.per_page
            to_join = [f"{i + 1}. {entry}" for i, entry in enumerate(entries, start=start)]
            embed.description = self.description_prefix + "\n".join(to_join)
        else:
            embed.description = self.description_prefix + "\n".join(entries)
        return embed
