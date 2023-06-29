from __future__ import annotations

import asyncio
import contextlib
import importlib
import os
import re
import subprocess
import sys
from typing import TYPE_CHECKING, Annotated, Awaitable, Callable

import discord
from discord.ext import commands

from exts import EXTERNAL_EXTENSIONS, get_extensions
from utils import AluContext, const

from ._category import DevBaseCog

if TYPE_CHECKING:
    pass


class ExtensionConverter(commands.Converter):
    """Just so I don't type `$reload exts.fpc.dota` but `$reload fpc.dota`

    Yes. Lazy."""

    async def convert(self, _ctx: AluContext, argument: str):
        m = argument.lower()
        argument = f"exts.{m}" if m not in EXTERNAL_EXTENSIONS else m
        return argument


class ReloadCog(DevBaseCog):
    @commands.command(name="extensions", hidden=True)
    async def extensions(self, ctx: AluContext):
        """Shows available extensions to load/reload/unload."""
        exts = [f"\N{BLACK CIRCLE} {ext}" for ext in self.bot.extensions.keys()]
        e = discord.Embed(title="Loaded Extensions", description="\n".join(exts), colour=const.Colour.prpl())
        await ctx.reply(embed=e)

    # SINGULAR LOAD UNLOAD RELOAD

    async def load_unload_reload_job(
        self,
        ctx: AluContext,
        extension: str,
        *,
        job_func: Callable[[str], Awaitable[None]],
    ):
        """Load/Unload/Reload a single extension."""
        try:
            await job_func(extension)
            tick = True
        except Exception as exc:
            txt = f'Job `{job_func.__name__}` for extension `{extension}` failed.'
            await self.bot.exc_manager.register_error(exc, txt, where=txt)
            tick = False

        await ctx.tick_reaction(tick)

    @commands.command(name="load", hidden=True)
    async def load(self, ctx: AluContext, extension: Annotated[str, ExtensionConverter]):
        """Loads a module."""
        await self.load_unload_reload_job(ctx, extension, job_func=self.bot.load_extension)

    @commands.command(name="unload", hidden=True)
    async def unload(self, ctx: AluContext, extension: Annotated[str, ExtensionConverter]):
        """Unloads a module."""
        await self.load_unload_reload_job(ctx, extension, job_func=self.bot.unload_extension)

    async def reload_or_load_extension(self, extension: str) -> None:
        try:
            await self.bot.reload_extension(extension)
        except commands.ExtensionNotLoaded:
            await self.bot.load_extension(extension)

    @commands.group(name="reload", hidden=True, invoke_without_command=True)
    async def reload(self, ctx: AluContext, extension: Annotated[str, ExtensionConverter]):
        """Reloads a module."""
        await self.load_unload_reload_job(ctx, extension, job_func=self.reload_or_load_extension)

    # RELOAD ALL

    async def reload_all_worker(self, ctx: AluContext):
        exts_to_reload = get_extensions(ctx.bot.test, reload=True)
        exts_to_unload = [e for e in self.bot.extensions if e not in exts_to_reload]

        statuses: list[tuple[bool, str, str]] = []
        errors: list[tuple[str, str]] = []

        async def do_the_job(ext: str, emote: str, method: Callable[[str], Awaitable[None]]):
            try:
                await method(ext)
                statuses.append((True, emote, ext))
            except* commands.ExtensionError as eg:
                statuses.append((False, emote, ext))
                for exc in eg.exceptions:
                    txt = f'Job `{method.__name__}` for extension `{ext}` failed.'
                    await self.bot.exc_manager.register_error(exc, txt, where=txt)
                    # name, value
                    errors.append((f'{ctx.tick(False)} `{exc.__class__.__name__}`', f"{exc}"))

        for ext in exts_to_reload:
            emoji = '\N{ANTICLOCKWISE DOWNWARDS AND UPWARDS OPEN CIRCLE ARROWS}'
            await do_the_job(ext, emoji, self.reload_or_load_extension)
        for ext in exts_to_unload:
            emoji = '\N{OCTAGONAL SIGN}'
            await do_the_job(ext, emoji, self.bot.unload_extension)

        if errors:
            content = '\n'.join(
                f'{ctx.tick(status)} - {emoji} `{ext if not ext.startswith("exts.") else ext[5:]}`'
                for status, emoji, ext in statuses
            )

            # let's format errors into embeds. It might backfire because of 25 fields restrictions.
            embed = discord.Embed(colour=const.Colour.error())
            for name, value in errors:
                embed.add_field(name=name, value=value, inline=False)

            await ctx.reply(content=content, embed=embed)
        else:
            # no errors thus let's not clutter my spam channel with output^
            with contextlib.suppress(discord.HTTPException):
                await ctx.message.add_reaction(ctx.tick(True))

    @reload.command(name="all", hidden=True)
    async def reload_all(self, ctx: AluContext):
        """Reloads all modules"""
        await self.reload_all_worker(ctx)

    @commands.command(name='t', hidden=True)
    async def reload_all_shortcut(self, ctx: AluContext):
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

    _GIT_PULL_REGEX = re.compile(r'\s*(?P<filename>.+?)\s*\|\s*[0-9]+\s*[+-]+')

    def find_modules_from_git(self, ctx: AluContext, output: str) -> list[tuple[int, str]]:
        files = self._GIT_PULL_REGEX.findall(output)
        ret: list[tuple[int, str]] = []

        # since I'm using nested rather complex categorized folder structure
        # I'm afraid I need to fetch list of extensions.
        exts = get_extensions(ctx.bot.test, reload=True)
        for file in files:
            root, ext = os.path.splitext(file)
            if ext != '.py':
                continue

            if root.startswith('exts/'):
                ext_name = root.replace('/', '.')
                is_submodule = ext_name not in exts
                ret.append((is_submodule, ext_name))

        # For reload order, the submodules should be reloaded first
        ret.sort(reverse=True)
        return ret

    async def reload_pull_worker(self, ctx: AluContext):
        async with ctx.typing():
            stdout, _stderr = await self.run_process('git pull')

        # progress and stuff is redirected to stderr in git pull
        # however, things like "fast forward" and files
        # along with the text "Already up to date" are in stdout

        if stdout.startswith('Already up to date.'):
            return await ctx.reply(stdout)

        modules = self.find_modules_from_git(ctx, stdout)

        mods_text = '\n'.join(f'{index}. `{module}`' for index, (_, module) in enumerate(modules, start=1))
        prompt_text = f'This will update the following modules, are you sure?\n{mods_text}'
        confirm = await ctx.prompt(content=prompt_text)
        if not confirm:
            return await ctx.send('Aborting.')

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
                    except Exception as e:
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

        await ctx.send('\n'.join(f'{ctx.tick(status)}: `{module}`' for status, module in statuses))

    @reload.command(name="pull", hidden=True)
    async def reload_pull(self, ctx: AluContext):
        """Reloads all modules, while pulling from git."""
        await self.reload_pull_worker(ctx)

    @commands.command(name='p', hidden=True)
    async def reload_pull_shortcut(self, ctx: AluContext):
        """Extreme one-letter shortcut to `reload pull`."""
        await self.reload_pull_worker(ctx)


async def setup(bot):
    await bot.add_cog(ReloadCog(bot))
