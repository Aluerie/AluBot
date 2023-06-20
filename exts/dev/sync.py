from __future__ import annotations

from typing import TYPE_CHECKING, List, Literal, Optional

import discord
from discord.ext import commands

from utils import const

from ._base import DevBaseCog

if TYPE_CHECKING:
    from utils import AluContext


class UmbraSyncCommandCog(DevBaseCog):
    """A SPECIAL ONE-COMMAND COG FOR ONE AND ONLY, THE FAMOUS UMBRA SYNC COMMAND. HOLY MOLY!
    (A BIT MODIFIED THO, SORRY UMBRA)

    `?tag usc` which abbreviates to `?tag umbra sync command`.

    This command is used to sync app_commands so people don't use
    their very precious `?tag ass` on me in discord.py server.
    """

    @commands.command()
    async def sync(
        self,
        ctx: AluContext,
        guilds: commands.Greedy[discord.Guild],
        spec: Optional[Literal["~", "*", "^", "trust"]] = None,
    ) -> None:
        """Sync command. Usage examples:
        * `$sync` -> global sync
        * `$sync ~` -> sync current guild
        * `$sync *` -> copies all global app commands to current guild and syncs
        * `$sync ^` -> clears all commands from the current guild target and syncs (removes guild commands)
        * `$sync id_1 id_2` -> syncs guilds with id 1 and 2
        * `$sync trust` -> sync trusted guilds
        """

        e = discord.Embed(colour=const.Colour.prpl())

        async def sync_to_guild_list(guilds: commands.Greedy[discord.Guild] | List[discord.Guild]):
            fmt = 0
            cmds = []
            for guild in guilds:
                try:
                    cmds += await ctx.bot.tree.sync(guild=guild)
                except discord.HTTPException:
                    pass
                else:
                    fmt += 1
            return f"Synced the tree to `{fmt}/{len(guilds)}` guilds."

        if spec == "trust":
            guild_list = [
                y for y in (ctx.bot.get_guild(guild_id) for guild_id in const.TRUSTED_GUILDS) if y is not None
            ]
            e.description = await sync_to_guild_list(guild_list)
        elif guilds:
            e.description = await sync_to_guild_list(guilds)
        elif spec:
            if ctx.guild:
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
                e.description = f"Synced `{len(synced)}` commands to the current guild."
            else:
                # todo: maybe raise different error
                raise commands.BadArgument("You used `$sync` command with a spec outside of guild")
        else:
            synced = await ctx.bot.tree.sync()
            e.description = f"Synced `{len(synced)}` commands globally."
        await ctx.reply(embed=e)


async def setup(bot):
    await bot.add_cog(UmbraSyncCommandCog(bot))
