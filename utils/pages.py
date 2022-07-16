"""
Inspired by @krittick's `ext.pages` from `py-cord` library.
Unfortunately I had to switch to `discord.py` so we need to bring pagination here as well
"""
from __future__ import annotations
from typing import TYPE_CHECKING, Dict, List, Optional, Union
from collections import defaultdict

from discord import ButtonStyle, Embed, File, Interaction, Message, WebhookMessage
from discord.ext.commands import Bot, BadArgument
from discord.ui import Button, Modal, View, TextInput

from utils.context import Context
from utils.var import Ems

from io import BytesIO

if TYPE_CHECKING:
    from discord import Emoji, PartialEmoji


class PaginatorSearchModal(Modal):
    def __init__(self, paginator, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.paginator: Paginator = paginator
        self.title = "Search Page by query"

    search = TextInput(label="Search Query", required=True)

    async def on_submit(self, ntr: Interaction):
        a = self.search.value

        found_page = None
        for idx, page in enumerate(self.paginator.pages):
            page_content = self.paginator.get_page_content(page)

            b = '\n'.join(
                [str(e.to_dict().values()) for e in page_content.embeds],
            )

            if a in b:
                found_page = idx
        if found_page is None:
            return await ntr.response.send_message(
                content=f"I found nothing with your search query {Ems.PepoBeliever}",
                ephemeral=True
            )
        await self.paginator.goto_page(page_number=found_page, ntr=ntr)


class PaginatorGotoModal(Modal):
    def __init__(self, paginator, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.paginator: Paginator = paginator
        self.title = "Goto Page"

    goto = TextInput(label="Page Number", required=True)

    async def on_submit(self, interaction: Interaction):
        new_page = int(self.goto.value) - 1
        if new_page > self.paginator.page_count:
            new_page = self.paginator.page_count
        elif new_page < 0:
            new_page = 0
        await self.paginator.goto_page(page_number=new_page, ntr=interaction)


class PaginatorButton(Button):
    def __init__(
        self,
        button_type: str,
        label: str = None,
        emoji: Union[str, Emoji, PartialEmoji] = None,
        style: ButtonStyle = ButtonStyle.green,
        loop_label: str = None,
    ):
        super().__init__(
            label=label if label or emoji else button_type.capitalize(),
            emoji=emoji,
            style=style,
        )
        self.button_type = button_type
        self.label = label if label or emoji else button_type.capitalize()
        self.emoji: Union[str, Emoji, PartialEmoji] = emoji
        self.style = style
        self.loop_label = self.label if not loop_label else loop_label
        self.paginator = None

    async def callback(self, ntr: Interaction):
        if self.button_type == "index":
            modal = PaginatorGotoModal(self.paginator, title="Goto Page")
            return await ntr.response.send_modal(modal)
        elif self.button_type == "search":
            modal = PaginatorSearchModal(self.paginator, title="Search Page by query")
            return await ntr.response.send_modal(modal)

        if self.button_type == "home":
            self.paginator.current_page = 0
        elif self.button_type == "prev":
            if self.paginator.loop_pages and self.paginator.current_page == 0:
                self.paginator.current_page = self.paginator.page_count
            else:
                self.paginator.current_page -= 1
        elif self.button_type == "next":
            if self.paginator.loop_pages and self.paginator.current_page == self.paginator.page_count:
                self.paginator.current_page = 0
            else:
                self.paginator.current_page += 1
        await self.paginator.goto_page(page_number=self.paginator.current_page, ntr=ntr)


class Page:
    def __init__(
        self,
        content: Optional[str] = None,
        embeds: Optional[List[Union[List[Embed], Embed]]] = None,
        custom_view: Optional[View] = None,
        files: Optional[List[File]] = None,
        title: Optional[str] = None
    ):
        if content is None and embeds is None:
            raise BadArgument("A page cannot have both content and embeds equal to None.")
        self._content = content
        self._embeds = embeds or []
        self._custom_view = custom_view
        self._files = files or []
        self._title = title

    async def callback(self, interaction: Optional[Interaction] = None):
        pass

    def update_files(self) -> Optional[List[File]]:
        """Updates the files associated with the page by re-uploading them.
        Typically used when the page is changed."""
        for file in self._files:
            if isinstance(file.fp, BytesIO):  # BytesIO
                fp = file.fp
                fp.seek(0)
                self._files[self._files.index(file)] = File(
                    fp,
                    filename=file.filename,
                    description=file.description,
                    spoiler=file.spoiler,
                )
            else:  # local upload with `file.fp.name` str, bytes or os.PathLike object
                with open(file.fp.name, "rb") as fp:  # type: ignore
                    self._files[self._files.index(file)] = File(
                        fp,  # type: ignore
                        filename=file.filename,
                        description=file.description,
                        spoiler=file.spoiler,
                    )
        return self._files

    @property
    def content(self) -> Optional[str]:
        return self._content

    @content.setter
    def content(self, value: Optional[str]):
        self._content = value

    @property
    def embeds(self) -> Optional[List[Union[List[Embed], Embed]]]:
        return self._embeds

    @embeds.setter
    def embeds(self, value: Optional[List[Union[List[Embed], Embed]]]):
        self._embeds = value

    @property
    def custom_view(self) -> Optional[View]:
        return self._custom_view

    @custom_view.setter
    def custom_view(self, value: Optional[View]):
        self._custom_view = value

    @property
    def files(self) -> Optional[List[File]]:
        return self._files

    @files.setter
    def files(self, value: Optional[List[File]]):
        self._files = value

    @property
    def title(self) -> Optional[str]:
        return self._title

    @title.setter
    def title(self, value: Optional[str]):
        self._title = value


class Paginator(View):
    def __init__(
        self,
        pages: Union[List[Page], List[str], List[Union[List[Embed], Embed]]],
        author_check=True,
        disable_on_timeout=True,
        loop_pages=True,
        custom_view: Optional[View] = None,
        timeout: Optional[float] = 180.0,
        bot: Optional[Bot] = None,
    ) -> None:
        super().__init__(timeout=timeout)
        self.timeout: float = timeout
        self.pages: Union[List[str], List[Page], List[Union[List[Embed], Embed]]] = pages
        self.current_page = 0
        self._page_number = self.current_page + 1

        self.page_count = max(len(self.pages) - 1, 0)
        self.nav_buttons = {}
        self.disable_on_timeout = disable_on_timeout
        self.loop_pages = loop_pages
        self.custom_view: View = custom_view
        self.bot = bot
        self.message: Union[Message, WebhookMessage, None] = None

        self.add_default_nav_buttons()

        self.usercheck = author_check
        self.user = None

    @property
    def page_number(self) -> int:
        return self._page_number

    async def on_timeout(self) -> None:
        if self.disable_on_timeout:
            for item in self.children:
                item.disabled = True
            page = self.pages[self.current_page]
            page = self.get_page_content(page)
            files = page.update_files()
            await self.message.edit(view=self, attachments=files or [])

    async def goto_page(self, page_number: int = 0, *, ntr: Optional[Interaction] = None) -> None:
        self.current_page = page_number

        self.update_nav_buttons()

        if self.custom_view:
            self.update_custom_view(self.custom_view)

        self.nav_buttons["index"]["object"].label = f"{self.current_page + 1}/{self.page_count + 1}"

        page = self.pages[page_number]
        page = self.get_page_content(page)

        if page.custom_view:
            self.update_custom_view(page.custom_view)

        files = page.update_files() or []

        if ntr:
            await ntr.response.edit_message(content=page.content, embeds=page.embeds, attachments=files, view=self)
        else:
            await self.message.edit(content=page.content, embeds=page.embeds, attachments=files, view=self)

    async def interaction_check(self, ntr: Interaction) -> bool:
        if self.usercheck:
            if self.user == ntr.user:
                return True
            else:
                await ntr.response.send_message(
                    f'This pagination menu cannot be controlled by you ! {Ems.peepoWTF}',
                    ephemeral=True
                )
                return False
        return True

    def add_default_nav_buttons(self):
        default_nav_buttons = [
            PaginatorButton("home", emoji="🏠", style=ButtonStyle.blurple),
            PaginatorButton("prev", label="<", style=ButtonStyle.red, loop_label="↪"),
            PaginatorButton("index", style=ButtonStyle.gray),
            PaginatorButton("next", label=">", style=ButtonStyle.green, loop_label="↩"),
            PaginatorButton("search", emoji="🔎", style=ButtonStyle.blurple),
        ]
        for button in default_nav_buttons:
            self.add_nav_button(button)

    def add_nav_button(self, button: PaginatorButton):
        self.nav_buttons[button.button_type] = {
            "object": Button(
                style=button.style,
                label=button.label
                if button.label or button.emoji
                else button.button_type.capitalize()
                if button.button_type != "index"
                else f"{self.current_page + 1}/{self.page_count + 1}",
                emoji=button.emoji,
            ),
            "label": button.label,
            "loop_label": button.loop_label
        }
        self.nav_buttons[button.button_type]["object"].callback = button.callback
        button.paginator = self

    def update_nav_buttons(self) -> Dict[str, Union[PaginatorButton, bool]]:
        for key, button in self.nav_buttons.items():
            if key == "next":
                if self.current_page == self.page_count:
                    if not self.loop_pages:
                        button["object"].label = button["label"]
                    else:
                        button["object"].label = button["loop_label"]
                elif self.current_page < self.page_count:
                    button["object"].label = button["label"]
            elif key == "prev":
                if self.current_page <= 0:
                    if not self.loop_pages:
                        button["object"].label = button["label"]
                    else:
                        button["object"].label = button["loop_label"]
                elif self.current_page >= 0:
                    button["object"].label = button["label"]
        self.clear_items()
        self.nav_buttons["index"]["object"].label = f"{self.current_page + 1}/{self.page_count + 1}"
        for key, button in self.nav_buttons.items():
            self.add_item(button["object"])

        return self.nav_buttons

    def update_custom_view(self, custom_view: View):
        if isinstance(self.custom_view, View):
            for item in self.custom_view.children:
                self.remove_item(item)
        for item in custom_view.children:
            self.add_item(item)

    @staticmethod
    def get_page_content(page: Union[Page, str, Embed, List[Embed]]) -> Page:
        if isinstance(page, Page):
            return page
        elif isinstance(page, str):
            return Page(content=page, embeds=[], files=[])
        elif isinstance(page, Embed):
            return Page(content=None, embeds=[page], files=[])
        elif isinstance(page, File):
            return Page(content=None, embeds=[], files=[page])
        elif isinstance(page, List):
            if all(isinstance(x, Embed) for x in page):
                return Page(content=None, embeds=page, files=[])
            if all(isinstance(x, File) for x in page):
                return Page(content=None, embeds=[], files=page)
            else:
                raise TypeError("All list items must be embeds or files.")
        else:
            raise TypeError(
                "Page content must be a Page object, string, an embed, a list of embeds, a file, or a list of files."
            )

    async def send(
        self,
        ctx: Union[Interaction, Context],
        ephemeral: bool = False,
    ) -> Union[Message, WebhookMessage]:
        if not isinstance(ctx, (Context, Interaction)):
            raise TypeError(f"expected Interaction, Context not {ctx.__class__!r}")

        if ephemeral and (self.timeout >= 900 or self.timeout is None):
            raise ValueError(
                "paginator responses cannot be ephemeral if the paginator timeout is 15 minutes or greater"
            )

        self.update_nav_buttons()

        if self.custom_view:
            self.update_custom_view(self.custom_view)

        page = self.pages[self.current_page]
        page_content = self.get_page_content(page)

        if page_content.custom_view:
            self.update_custom_view(page_content.custom_view)

        if isinstance(ctx, Interaction):
            self.user = ctx.user

            if ctx.response.is_done():
                msg = await ctx.followup.send(
                    content=page_content.content,
                    embeds=page_content.embeds,
                    files=page_content.files,
                    view=self,
                    ephemeral=ephemeral,
                )
                # convert from WebhookMessage to Message reference to bypass 15min webhook token timeout
                # (non-ephemeral messages only)
                if not ephemeral:
                    msg = await msg.channel.fetch_message(msg.id)
            else:
                msg = await ctx.response.send_message(
                    content=page_content.content,
                    embeds=page_content.embeds,
                    files=page_content.files,
                    view=self,
                    ephemeral=ephemeral,
                )
        else:  # if isinstance(ctx, Context):
            self.user = ctx.author

            msg = await ctx.reply(
                content=page_content.content,
                embeds=page_content.embeds,
                files=page_content.files,
                view=self
            )

        if isinstance(msg, (Message, WebhookMessage)):
            self.message = msg
        elif isinstance(msg, Interaction):
            self.message = await msg.original_message()

        return self.message

