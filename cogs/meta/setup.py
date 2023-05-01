from __future__ import annotations

from typing import TYPE_CHECKING, List, Literal, NamedTuple

import discord
from discord.ext import commands, menus

from utils import AluCog, AluContext, Clr
from utils.pagination import Paginator

if TYPE_CHECKING:
    pass


class SetupFormatData(NamedTuple):
    cog: commands.Cog | Literal['front_page', 'back_page']


class SetupSelect(discord.ui.Select):
    def __init__(self, paginator: SetupPages):
        super().__init__(placeholder='Choose setup category')
        self.paginator: SetupPages = paginator
        self.__fill_options()

    def __fill_options(self) -> None:
        self.add_option(
            label='Home Page',
            description='Index Page of the setup menu',
            emoji='\N{HOUSE BUILDING}',
            value=str(0),
        )
        counter = 0
        for entry in self.paginator.source.data:
            cog = entry.cog
            if cog in ['front_page']:
                continue

            cog_name = getattr(cog, "qualified_name", "No Category")
            cog_desc = getattr(cog, "description", "No Description")
            cog_emote = getattr(cog, "setup_emote", None)

            self.add_option(label=cog_name, description=cog_desc, emoji=cog_emote, value=str(counter + 1))
            counter += 1

    async def callback(self, ntr: discord.Interaction):
        await self.paginator.show_page(ntr, int(self.values[0]))


class SetupPageSource(menus.ListPageSource):
    def __init__(self, data: List[SetupFormatData]):
        super().__init__(entries=data, per_page=1)
        self.data: List[SetupFormatData] = data

    async def format_page(self, menu: SetupPages, entries: SetupFormatData):
        cog = entries.cog
        if cog == 'front_page':
            # todo: fill it properly
            e = discord.Embed(colour=Clr.prpl())
            e.description = 'Front page baby'

            menu.clear_items()
            menu.fill_items()
            menu.add_item(SetupSelect(menu))
            return e
        else:
            embeds = []
            setup_info = getattr(cog, 'setup_info', None)  # method cog.setup_info(self)
            if setup_info:
                embeds.append(await setup_info())
            setup_state = getattr(cog, 'setup_state', None)  # method cog.setup_state(self, ctx: Context)
            if setup_state:
                embeds.append(await setup_state(menu.ctx_ntr))

            if v := getattr(cog, 'setup_view', None):  # method cog.setup_view(self, pages: SetupPages)
                view: discord.ui.View = await v(menu)
                menu.clear_items()
                menu.fill_items()
                menu.add_item(SetupSelect(menu))
                for c in view.children:
                    # analogy for @is_manager()
                    if not menu.author.guild_permissions.manage_guild:
                        c.disabled = True  # type: ignore
                    menu.add_item(c)
            return {'embeds': embeds}


class SetupPages(Paginator):
    source: SetupPageSource

    def __init__(self, ctx: AluContext, source: SetupPageSource):
        super().__init__(ctx, source)
        self.show_text_cmds = True
        self.add_item(SetupSelect(self))

    def update_more_labels(self, page_number: int) -> None:
        self.text_cmds.label = '\N{NOTEBOOK}' if self.show_text_cmds else '\N{OPEN BOOK}'

    def fill_items(self):
        if self.source.is_paginating():
            for item in [self.refresh, self.previous_page, self.index, self.next_page, self.text_cmds]:
                self.add_item(item)

    @discord.ui.button(label='\N{NOTEBOOK}', style=discord.ButtonStyle.blurple)
    async def text_cmds(self, ntr: discord.Interaction, _btn: discord.ui.Button):
        """Toggle showing text commands embed in the setup paginator"""
        self.show_text_cmds = not self.show_text_cmds
        await self.show_page(ntr, self.current_page_number)


class SetupCog:
    @property
    def setup_emote(self):
        raise NotImplementedError

    async def setup_info(self) -> discord.Embed:
        raise NotImplementedError

    async def setup_state(self, ctx: AluContext) -> discord.Embed:
        raise NotImplementedError

    async def setup_view(self, pages: SetupPages) -> discord.ui.View:
        raise NotImplementedError


class SetupCommandCog(AluCog):
    @commands.hybrid_command()
    async def setup(self, ctx: AluContext):
        setup_data: List[SetupFormatData] = [SetupFormatData(cog='front_page')]
        for cog_name, cog in self.bot.cogs.items():
            if getattr(cog, 'setup_info', None):
                setup_data.append(SetupFormatData(cog=cog))

        pages = SetupPages(ctx, SetupPageSource(setup_data))
        await pages.start()
