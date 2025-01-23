from __future__ import annotations

import asyncio
import contextlib
import importlib
import re
import subprocess
import sys
from pathlib import Path
from typing import TYPE_CHECKING, Annotated, override

import discord
from discord.ext import commands

from ext import get_extensions
from utils import const, formats

from ._base import DevBaseCog

if TYPE_CHECKING:
    from collections.abc import Awaitable, Callable

    from bot import AluBot, AluContext


class ExtensionConverter(commands.Converter[str]):
    """Just so I don't type `$reload extensions.fpc.dota` but `$reload fpc.dota`.

    Yes. Lazy.
    """

    # currently does not handle base extensions
    @override
    async def convert(self, _: AluContext, argument: str) -> str:
        m = argument.lower()
        return f"ext.{m}"


class ReloadCog(DevBaseCog):
    @commands.command(name="extensions", hidden=True)
    async def extensions(self, ctx: AluContext) -> None:
        """Shows available extensions to load/reload/unload."""
        extensions = [f"\N{BLACK CIRCLE} {ext}" for ext in sorted(self.bot.extensions, key=str.lower)]
        embed = discord.Embed(
            colour=const.Colour.blueviolet,
            title="Loaded Extensions",
            description="\n".join(extensions),
        )
        await ctx.reply(embed=embed)

    # SINGULAR LOAD UNLOAD RELOAD

    async def load_unload_reload_job(
        self,
        ctx: AluContext,
        extension: str,
        *,
        job_func: Callable[[str], Awaitable[None]],
    ) -> None:
        """Load/Unload/Reload a single extension."""
        try:
            await job_func(extension)
            tick = True
        except Exception as exc:
            embed = discord.Embed(
                colour=0x663322,
                description=f"Job `{job_func.__name__}` for extension `{extension}` failed.",
            ).set_footer(text=f"load_unload_reload_job: {extension}")
            await self.bot.exc_manager.register_error(exc, embed)
            tick = False

        await ctx.tick_reaction(tick)

    @commands.command(name="load", hidden=True)
    async def load(self, ctx: AluContext, extension: Annotated[str, ExtensionConverter]) -> None:
        """Loads a module."""
        await self.load_unload_reload_job(ctx, extension, job_func=self.bot.load_extension)

    @commands.command(name="unload", hidden=True)
    async def unload(self, ctx: AluContext, extension: Annotated[str, ExtensionConverter]) -> None:
        """Unloads a module."""
        await self.load_unload_reload_job(ctx, extension, job_func=self.bot.unload_extension)

    async def reload_or_load_extension(self, extension: str) -> None:
        try:
            await self.bot.reload_extension(extension)
        except commands.ExtensionNotLoaded:
            await self.bot.load_extension(extension)

    @commands.group(name="reload", hidden=True, invoke_without_command=True)
    async def reload(self, ctx: AluContext, extension: Annotated[str, ExtensionConverter]) -> None:
        """Reloads a module."""
        await self.load_unload_reload_job(ctx, extension, job_func=self.reload_or_load_extension)

    # RELOAD ALL

    async def reload_all_worker(self, ctx: AluContext) -> None:
        extensions_to_reload = get_extensions(ctx.bot.test, reload=True)
        extensions_to_unload = [e for e in self.bot.extensions if e not in extensions_to_reload]

        statuses: list[tuple[bool, str, str]] = []
        errors: list[tuple[str, str]] = []

        async def do_the_job(ext: str, emote: str, method: Callable[[str], Awaitable[None]]) -> None:
            try:
                await method(ext)
                statuses.append((True, emote, ext))
            except* commands.ExtensionError as eg:
                statuses.append((False, emote, ext))
                for exc in eg.exceptions:
                    embed = discord.Embed(
                        colour=0x663322,
                        description=f"Job `{method.__name__}` for extension `{ext}` failed.",
                    ).set_footer(text=f"reload_all_worker.do_the_job: {ext}")
                    await self.bot.exc_manager.register_error(exc, embed)
                    # name, value
                    errors.append((f"{formats.tick(False)} `{exc.__class__.__name__}`", f"{exc}"))

        for ext in extensions_to_reload:
            emoji = "\N{ANTICLOCKWISE DOWNWARDS AND UPWARDS OPEN CIRCLE ARROWS}"
            await do_the_job(ext, emoji, self.reload_or_load_extension)
        for ext in extensions_to_unload:
            emoji = "\N{OCTAGONAL SIGN}"
            await do_the_job(ext, emoji, self.bot.unload_extension)

        if errors:
            content = "\n".join(
                f'{formats.tick(status)} - {emoji} `{ext if not ext.startswith("ext.") else ext[5:]}`'
                for status, emoji, ext in statuses
            )

            # let's format errors into embeds. It might backfire because of 25 fields restrictions.
            embed = discord.Embed(colour=const.Colour.maroon)
            for name, value in errors:
                embed.add_field(name=name, value=value, inline=False)

            await ctx.reply(content=content, embed=embed)
        else:
            # no errors thus let's not clutter my spam channel with output^
            try:
                await ctx.message.add_reaction(formats.tick(True))
            except discord.HTTPException:
                with contextlib.suppress(discord.HTTPException):
                    await ctx.send(formats.tick(True))

    @reload.command(name="all", hidden=True)
    async def reload_all(self, ctx: AluContext) -> None:
        """Reloads all modules."""
        await self.reload_all_worker(ctx)

    @commands.command(name="t", hidden=True)
    async def reload_all_shortcut(self, ctx: AluContext) -> None:
        """Extreme one-letter shortcut to `reload all` due to a high usage rate."""
        await self.reload_all_worker(ctx)

    # RELOAD PULL

    async def run_process(self, command: str) -> list[str]:
        try:
            process = await asyncio.create_subprocess_shell(command, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
            result = await process.communicate()
        except NotImplementedError:
            process = subprocess.Popen(command, shell=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
            result = await self.bot.loop.run_in_executor(None, process.communicate)

        return [output.decode() for output in result]

    _GIT_PULL_REGEX = re.compile(r"\s*(?P<filename>.+?)\s*\|\s*[0-9]+\s*[+-]+")

    def find_modules_from_git(self, ctx: AluContext, output: str) -> list[tuple[int, str]]:
        files = self._GIT_PULL_REGEX.findall(output)
        ret: list[tuple[int, str]] = []

        # since I'm using nested rather complex categorized folder structure
        # I'm afraid I need to fetch list of extensions.
        extensions = get_extensions(ctx.bot.test, reload=True)
        for file in files:
            path = Path(file)
            root = str(path.parent / path.stem)
            ext = path.suffix
            if ext != ".py":
                continue

            if root.startswith("ext/"):
                ext_name = root.replace("/", ".")
                is_submodule = ext_name not in extensions
                ret.append((is_submodule, ext_name))

        # For reload order, the submodules should be reloaded first
        ret.sort(reverse=True)
        return ret

    async def reload_pull_worker(self, ctx: AluContext) -> None:
        async with ctx.typing():
            stdout, _stderr = await self.run_process("git pull")

        # progress and stuff is redirected to stderr in git pull
        # however, things like "fast forward" and files
        # along with the text "Already up to date" are in stdout

        if stdout.startswith("Already up to date."):
            await ctx.reply(stdout)
            return

        modules = self.find_modules_from_git(ctx, stdout)

        mods_text = "\n".join(f"{index}. `{module}`" for index, (_, module) in enumerate(modules, start=1))
        embed = discord.Embed(
            colour=const.Colour.blueviolet,
            description=f"This will update the following modules, are you sure?\n{mods_text}",
        )
        if not await ctx.bot.disambiguator.confirm(ctx, embed=embed):
            return

        statuses = []
        for is_submodule, module in modules:
            if is_submodule:
                try:
                    actual_module = sys.modules[module]
                except KeyError:
                    statuses.append((None, module))
                else:
                    try:
                        importlib.reload(actual_module)
                    except Exception:
                        statuses.append((False, module))
                    else:
                        statuses.append((True, module))
            else:
                try:
                    await self.reload_or_load_extension(module)
                except commands.ExtensionError:
                    statuses.append((False, module))
                else:
                    statuses.append((True, module))

        await ctx.send("\n".join(f"{formats.tick(status)}: `{module}`" for status, module in statuses))

    @reload.command(name="pull", hidden=True)
    async def reload_pull(self, ctx: AluContext) -> None:
        """Reloads all modules, while pulling from git."""
        await self.reload_pull_worker(ctx)

    @commands.command(name="p", hidden=True)
    async def reload_pull_shortcut(self, ctx: AluContext) -> None:
        """Extreme one-letter shortcut to `reload pull`."""
        await self.reload_pull_worker(ctx)


async def setup(bot: AluBot) -> None:
    """Load AluBot extension. Framework of discord.py."""
    await bot.add_cog(ReloadCog(bot))
