from __future__ import annotations

import itertools
from typing import TYPE_CHECKING, Any, Literal, Self, override

import discord
from discord.ext import commands

from bot import AluCog, AluContext, aluloop
from utils import const, pages

if TYPE_CHECKING:
    from collections.abc import Mapping, Sequence

    from bot import AluBot, AluInteraction


type AluCommand = commands.Command[AluCog, Any, Any]
type AluGroupCommand = commands.Group[AluCog, Any, Any]


class CogPage:
    def __init__(
        self,
        section: Literal["_front_page"] | AluCog | commands.Cog,  # dirty way to handle front page
        category: ExtCategory,
        page_commands: Sequence[AluCommand],
        section_total_commands: int = 0,
        section_page_number: int = 0,
        section_total_pages: int = 1,
        category_page_number: int = 0,
        category_total_pages: int = 1,
    ) -> None:
        self.section: Literal["_front_page"] | AluCog | commands.Cog = section
        self.category: ExtCategory = category
        self.page_commands: Sequence[AluCommand] = page_commands
        self.section_total_commands: int = section_total_commands
        self.section_page_number: int = section_page_number
        self.section_total_pages: int = section_total_pages
        self.category_page_number: int = category_page_number
        self.category_total_pages: int = category_total_pages


class HelpPageSource(menus.ListPageSource):
    def __init__(self, data: dict[ExtCategory, list[CogPage]]) -> None:
        entries = list(itertools.chain.from_iterable(data.values()))
        super().__init__(entries=entries, per_page=1)

    @override
    async def format_page(self, menu: HelpPages, page: CogPage) -> discord.Embed:
        e = discord.Embed(color=const.Color.prpl)

        if page.section == "_front_page":
            bot = menu.ctx_ntr.client
            owner = bot.owner
            e.title = f"{bot.user.name}'s Help Menu"
            e.description = (
                f"\N{HEAVY BLACK HEART}\N{VARIATION SELECTOR-16} "
                f"Hi! {bot.user.name} is an ultimate multi-purpose bot! \N{PURPLE HEART}\n\n"
                f"\N{BLACK CIRCLE} Use {const.Slash.help}` <command>` for more info on a command.\n"
                f"\N{BLACK CIRCLE} Use {const.Slash.help}` <section>` to go to that section page.\n"
                "\N{BLACK CIRCLE} Alternatively to^ you can try searching with \N{RIGHT-POINTING MAGNIFYING GLASS} button.\n"
                "\N{BLACK CIRCLE} For legend used in the help menu press \N{WHITE QUESTION MARK ORNAMENT} button.\n"
                "\N{BLACK CIRCLE} Use the dropdown menu below to select a category \N{UNICORN FACE}."
            )
            e.set_thumbnail(url=bot.user.display_avatar)
            e.set_author(name=f"Made by @{owner.display_name}", icon_url=owner.display_avatar)
            e.set_footer(text=f"With love, {bot.user.display_name}", icon_url=bot.user.display_avatar)

            menu.clear_items()
            menu.fill_items()
            menu.add_item(discord.ui.Button(emoji=const.EmoteLogo.GitHub, label="GitHub", url=bot.repository_url))
            menu.add_item(discord.ui.Button(emoji=const.Emote.FeelsDankMan, label="Invite me", url=bot.invite_link))
            menu.add_item(
                discord.ui.Button(emoji=const.EmoteLogo.AluerieServer, label="Community", url=bot.community_invite_url),
            )

            return e

        emote = getattr(page.section, "emote", None) or ""
        e.title = (
            f"{page.section.qualified_name} {emote} - {page.section_total_commands} commands "
            f"(Section page {page.section_page_number + 1}/{page.section_total_pages})"
        )
        emote_url = discord.PartialEmoji.from_str(page.category.emote)
        author_text = (
            f"Category: {page.category.name} "
            f"(Category page {page.category_page_number + 1}/{page.category_total_pages})"
        )
        e.set_author(name=author_text, icon_url=emote_url.url)
        e.description = page.section.description
        for c in page.page_commands:
            e.add_field(
                name=menu.help_cmd.get_command_signature(c),
                value=menu.help_cmd.get_command_short_help(c),
                inline=False,
            )
        e.set_footer(text=page.category.description, icon_url=menu.ctx_ntr.client.user.display_avatar)
        menu.clear_items()
        menu.fill_items()
        return e


class HelpPages(pages.Paginator):
    source: HelpPageSource

    def __init__(
        self,
        ctx: AluContext | AluInteraction,
        help_cmd: AluHelp,
        help_data: dict[ExtCategory, list[CogPage]],
    ) -> None:
        self.help_cmd: AluHelp = help_cmd
        self.help_data: dict[ExtCategory, list[CogPage]] = help_data
        super().__init__(ctx, HelpPageSource(help_data))

    @override
    def fill_items(self) -> None:
        if self.source.is_paginating():  # Copied a bit from super().fill_items
            for item in [self.legend_page, self.previous_page, self.index, self.next_page, self.search]:
                self.add_item(item)
            self.add_item(HelpSelect(self))

    @discord.ui.button(label="\N{WHITE QUESTION MARK ORNAMENT}", style=discord.ButtonStyle.blurple)
    async def legend_page(self, interaction: AluInteraction, _button: discord.ui.Button[Self]) -> None:
        """Show legend page."""
        e = discord.Embed(
            title="Legend used in the Help menu.",
            description=(
                "If you have troubles figuring out how to use some of text commands "
                "then you should try using slash commands because everything there has a small explanation text. "
                "Nevertheless, this help menu also shows signatures for text, a.k.a. prefix commands."
                "Reading those is pretty simple."
            ),
        )

        fields = (
            (
                "[...]",
                "This means that the command has more documentation to it, "
                f"which you can see by using {const.Slash.help}` command: <command>`",
            ),
            ("<argument>", "This means the argument is __**required**__."),
            ("[argument]", "This means the argument is __**optional**__."),
            ("`[argument='default']`", "Means that this argument is __**optional**__ and has a default value"),
            ("[A|B|C]", "This means that it can be __**either A, B or C**__."),
            ("[argument...]", "This means you can have multiple arguments.\n"),
            (
                "Note",
                "Now that you know the basics, it should be noted that...\n__**You do not type in the brackets!**__",
            ),
        )
        for name, value in fields:
            e.add_field(name=name, value=value, inline=False)
        e.set_footer(text=f"With love, {interaction.client.user.display_name}")
        await interaction.response.send_message(embed=e, ephemeral=True)

    # @discord.ui.button(label="\N{WHITE QUESTION MARK ORNAMENT}", style=discord.ButtonStyle.blurple)
    # async def find_command_or_section_page(self, interaction: discord.Interaction, _button: discord.ui.Button):
    #     """Show modal which leads to basically invoking /help <command>/<section>"""
    #     await self.show_page(ntr, 0)


class HelpSelect(discord.ui.Select[HelpPages]):
    def __init__(self, paginator: HelpPages) -> None:
        super().__init__(placeholder="\N{UNICORN FACE} Choose help category")
        self.paginator: HelpPages = paginator

        self.__fill_options()

    def __fill_options(self) -> None:
        pages_per_category: Mapping[ExtCategory, tuple[int, int]] = {}
        total = 1
        for category, cog_pages in self.paginator.help_data.items():
            starting = total
            total += len(cog_pages)
            pages_per_category[category] = starting, total - 1

        for category, (start, end) in pages_per_category.items():
            pages_string = f"(page {start})" if start == end else f"(pages {start}-{end})"
            self.add_option(
                label=f"{category.name} {pages_string}",
                emoji=category.emote,
                description=category.description,
                value=str(start - 1),  # we added 1 in total=1
            )

    @override
    async def callback(self, interaction: AluInteraction) -> None:
        page_to_open = int(self.values[0])
        await self.paginator.show_page(interaction, page_to_open)


class AluHelp(commands.HelpCommand):
    context: AluContext

    # todo: idk
    def __init__(self, show_hidden: bool = False) -> None:
        super().__init__(
            show_hidden=show_hidden,
            verify_checks=False,
            command_attrs={
                "hidden": False,
                "help": "Show `help` menu for the bot.",
                "usage": "[command/section/category]",
            },
        )

    async def unpack_commands(
        self,
        command: AluCommand,
        answer: list[AluCommand] | None = None,
        deep: int = 0,
    ) -> list[AluCommand]:
        """If a command is a group then unpack those until their very-last children.

        Examples
        --------
        /help -> [/help]
        /tag (create delete owner etc) -> [/tag create, /tag delete, /tag delete, /tag etc]
        same for 3depth children.

        """
        if answer is None:
            answer = []  # so the array only exists inside the command.
        if getattr(command, "commands", None) is not None:  # maybe we should isinstance(commands.Group)
            for x in await self.filter_commands(command.commands):  # , sort=True): # type: ignore
                await self.unpack_commands(x, answer=answer, deep=deep + 1)
        else:
            answer.append(command)
        return answer

    @override
    def get_command_signature(self, command: AluCommand) -> str:
        def signature() -> str:
            app_command = self.context.bot.tree.get_app_command(command.qualified_name)
            if app_command:
                cmd_mention = app_command.mention
            else:
                prefix = getattr(self.context, "clean_prefix", "$")
                cmd_mention = f"`{prefix}{command.qualified_name}`"

            sign = f" `{command.signature}`" if command.signature else ""
            return f"{cmd_mention}{sign}"

        def aliases() -> str:
            if len(command.aliases):
                return " | aliases: " + "; ".join([f"`{ali}`" for ali in command.aliases])
            return ""

        # def cd():
        #     if command.cooldown is not None:
        #         return f' | cd: {command.cooldown.rate} per {human_timedelta(command.cooldown.per, strip=True, suffix=False)}'
        #     return ''

        def check() -> str:
            if command.checks:
                res = {i.__doc__ or "mods only" for i in command.checks}
                res = [f"*{i}*" for i in res]
                return f"**!** {', '.join(res)}\n"
            return ""

        return f"\N{BLACK CIRCLE} {signature()}{aliases()}\n{check()}"

    def get_command_short_help(self, command: AluCommand) -> str:
        # help string
        help_str = command.help or "No documentation"
        split = help_str.split("\n", 1)
        extra_info = " [...]" if len(split) > 1 else ""
        return split[0] + extra_info

    @override
    def get_bot_mapping(self) -> dict[ExtCategory, dict[AluCog, list[AluCommand]]]:
        """Retrieves the bot mapping passed to `send_bot_help`."""
        # TODO: include solo slash commands and Context Menu commands.
        categories = self.context.bot.help_categories

        return {category: {cog: cog.get_commands() for cog in cog_list} for category, cog_list in categories.items()}
        # todo: think how to sort front page to front

    async def send_help_menu(
        self,
        mapping: dict[ExtCategory, dict[AluCog, list[AluCommand]]],
        *,
        requested_cog: AluCog | None = None,
    ) -> None:
        await self.context.typing()

        help_data: dict[ExtCategory, list[CogPage]] = {}

        starting_page, page_counter = 0, 0  # used to get to the section page we might need from the cog command.
        for category, cog_cmd_dict in mapping.items():
            for cog, cmds in cog_cmd_dict.items():
                if requested_cog == cog:
                    starting_page = page_counter + 1

                filtered = await self.filter_commands(cmds)  # , sort=True)
                if filtered:
                    cmds_unpacked = list(
                        itertools.chain.from_iterable([await self.unpack_commands(c) for c in filtered]),
                    )
                    amount_of_cmds = len(cmds_unpacked)
                    chunk_size = 7
                    cmds10 = [cmds_unpacked[i : i + chunk_size] for i in range(0, amount_of_cmds, chunk_size)]
                    page_len = len(cmds10)
                    for counter, page_cmds in enumerate(cmds10):
                        page = CogPage(
                            section=cog,
                            page_commands=page_cmds,
                            section_total_commands=amount_of_cmds,
                            section_page_number=counter,
                            section_total_pages=page_len,
                            category=category,
                        )
                        help_data.setdefault(category, []).append(page)
                        page_counter += 1

        for category, cog_pages in help_data.items():
            cog_len = len(cog_pages)
            for counter, page in enumerate(cog_pages):
                page.category_total_pages = cog_len
                page.category_page_number = counter

        help_data = dict(sorted(help_data.items(), key=lambda x: (int(x[0].sort_back), x[0].name)))

        index_category = ExtCategory(name="Index page", emote="\N{SWAN}", description="Index page")
        index_pages = [CogPage(section="_front_page", page_commands=[], section_page_number=0, category=index_category)]

        help_data = {index_category: index_pages} | help_data

        pages = HelpPages(self.context, self, help_data)
        await pages.start(page_number=starting_page)

    @override
    async def send_bot_help(
        self,
        mapping: dict[ExtCategory, dict[AluCog, list[AluCommand]]],
    ) -> None:
        await self.send_help_menu(mapping)

    @override
    async def send_cog_help(self, cog: AluCog) -> None:
        mapping = self.get_bot_mapping()
        await self.send_help_menu(mapping, requested_cog=cog)

    @override
    async def send_command_help(self, command: AluCommand) -> None:
        return await super().send_command_help(command)

    @override
    async def send_group_help(self, group: AluGroupCommand) -> None:
        return await super().send_group_help(group)

    @override
    async def send_error_message(self, error: str) -> None:
        return await super().send_error_message(error)


class BaseHelpCog(AluCog):
    """Base cog for help command."""

    def __init__(self, bot: AluBot, *args: Any, **kwargs: Any) -> None:
        super().__init__(bot, *args, **kwargs)
        bot.help_command = AluHelp()
        bot.help_command.cog = self
        # note^ that when `meta` is loaded .cog = self will be overwritten

        self._original_help_command: commands.HelpCommand | None = bot.help_command

    @override
    async def cog_load(self) -> None:
        self.load_help_info.start()

    @override
    async def cog_unload(self) -> None:
        self.load_help_info.cancel()
        self.bot.help_command = self._original_help_command

    @aluloop(count=1)
    async def load_help_info(self) -> None:
        # auto-syncing is bad, but is auto-fetching commands bad to fill the cache?
        # If I ever get rate-limited here then we will think :thinking:
        await self.bot.tree.fetch_commands()

        if not self.bot.test:
            # announce to community/hideout that we logged in
            # from testing purposes it means we can use help with [proper slash mentions (if synced).
            embed = discord.Embed(
                color=const.Color.prpl,
                description=f"Logged in as {self.bot.user.name}",
            ).set_footer(text="Finished updating/rebooting")
            await self.community.bot_spam.send(embed=embed)


async def setup(bot: AluBot) -> None:
    """Load AluBot extension. Framework of discord.py."""
