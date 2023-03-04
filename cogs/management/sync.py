from __future__ import annotations

from typing import TYPE_CHECKING, Literal, Optional

import discord
from discord.ext import commands

from utils.checks import is_owner
from utils.context import Context
from utils.var import Clr

from ._base import ManagementBase

if TYPE_CHECKING:
    pass


class SyncCommandCog(ManagementBase):

    # **The** famous Umbra\'s sync command holy moly. `?tag usc`. Or `?tag umbra sync command`
    @is_owner()
    @commands.command()
    async def sync(
        self, ctx: Context, guilds: commands.Greedy[discord.Object], spec: Optional[Literal["~", "*", "^"]] = None
    ) -> None:
        """Sync command. Usage examples:
        * `$sync` -> global sync
        * `$sync ~` -> sync current guild
        * `$sync *` -> copies all global app commands to current guild and syncs
        * `$sync ^` -> clears all commands from the current guild target and syncs (removes guild commands)
        * `$sync id_1 id_2` -> syncs guilds with id 1 and 2
        """

        # todo: remove this from help for plebs
        if not guilds:
            match spec:
                case "~":
                    synced = await ctx.bot.tree.sync(guild=ctx.guild)
                case "*":
                    ctx.bot.tree.copy_global_to(guild=ctx.guild)
                    synced = await ctx.bot.tree.sync(guild=ctx.guild)
                case "^":
                    ctx.bot.tree.clear_commands(guild=ctx.guild)
                    await ctx.bot.tree.sync(guild=ctx.guild)
                    synced = []
                case _:
                    synced = await ctx.bot.tree.sync()

            e = discord.Embed(colour=Clr.prpl)
            e.description = f"Synced `{len(synced)}` commands {'globally' if spec is None else 'to the current guild.'}"
            await ctx.reply(embed=e)
            return

        fmt = 0
        cmds = []
        for guild in guilds:
            try:
                cmds += await ctx.bot.tree.sync(guild=guild)
            except discord.HTTPException:
                pass
            else:
                fmt += 1
        e = discord.Embed(colour=Clr.prpl)
        e.description = f"Synced the tree to `{fmt}/{len(guilds)}` guilds."
        await ctx.reply(embed=e)


async def setup(bot):
    await bot.add_cog(SyncCommandCog(bot))
