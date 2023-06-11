from __future__ import annotations

import io
import textwrap
import traceback
from contextlib import redirect_stdout
from typing import TYPE_CHECKING, Any, Dict, Optional, Union

import discord
from discord.ext import commands

from utils.converters import Codeblock

from ._base import DevBaseCog

if TYPE_CHECKING:
    from utils import AluBot, AluContext


class CodeRun(DevBaseCog):
    def __init__(self, bot: AluBot):
        super().__init__(bot)
        self._last_result: Optional[Any] = None
        self.sessions: set[int] = set()

    def get_var_dict_from_ctx(
        self,
        ctx: AluContext,
        mentions: commands.Greedy[Union[discord.Member, discord.User, discord.abc.GuildChannel, discord.Role]],
    ) -> Dict[str, Any]:
        """Returns the dict to be used in eval/REPL."""
        env = {
            "author": ctx.author,
            "bot": self.bot,
            "channel": ctx.channel,
            "ctx": ctx,
            "find": discord.utils.find,
            "get": discord.utils.get,
            "guild": ctx.guild,
            "me": ctx.me,
            "message": ctx.message,
            "msg": ctx.message,
        }

        # Now let's add convertible mentions into the env
        # they will be possible to call as mention_0, user_3, role_20
        # note that number is just order in our initial message so if @John is "mention_4" then he is also "user_4"
        lookup = {
            discord.User: ["user", "mention"],
            # note: our Greedy makes member obj whenever possible on the "closest" guild
            discord.Member: ["user", "member", "mention"],
            discord.abc.GuildChannel: ["channel", "mention"],  # I hope it covers all mentionable cases fine
            discord.Role: ["role", "mention"],
        }
        if mentions:
            for idx, obj in enumerate(mentions):
                found_type: bool = False
                for discord_type in lookup:
                    if isinstance(obj, discord_type):
                        found_type = True
                        for item in lookup[discord_type]:
                            key = f"{item}_{idx}"
                            env[key] = obj
                if not found_type:
                    raise commands.BadArgument(  # should not in theory happen but let's watch out
                        f"We could not assign `mention_{idx}` to {obj} from Greedy mentions. " "Check eval cmd code."
                    )

        return env

    @commands.command(hidden=True, name="py", aliases=["eval", "python"])
    async def python(
        self,
        ctx: AluContext,
        mentions: commands.Greedy[Union[discord.Member, discord.User, discord.abc.GuildChannel, discord.Role]],
        *,
        codeblock: Optional[Codeblock] = None,
    ):
        """Direct evaluation of Python code.
        It just puts your codeblock into `async def func():`, so
        remember to end the code with `return result` if you want only `result`
        """
        if codeblock is None:
            # codeblock is optional, just bcs I want Greedy to be optional with None and preserve the order.
            # so in the end we are free to have some "testing code" like below :D
            codeblock = Codeblock(code="print('Hello World!')", language="py")

        env = self.get_var_dict_from_ctx(ctx, mentions)
        env["_"] = (self._last_result,)
        env.update(globals())

        stdout = io.StringIO()

        # why does discord use only two spaces for tab indent
        to_compile = f'async def func():\n{textwrap.indent(codeblock.code, "  ")}'

        try:
            exec(to_compile, env)
        except Exception as error:
            await ctx.try_tick_reaction(False)
            return await ctx.send(f"```py\n{traceback.format_exc()}```")

        func = env["func"]  # <class 'function'>

        try:
            with redirect_stdout(stdout):
                ret = await func()
        except Exception as error:
            value = stdout.getvalue()
            await ctx.try_tick_reaction(False)
            await ctx.send(f"```py\n{value}{traceback.format_exc()}\n```")
        else:
            value = stdout.getvalue()
            await ctx.try_tick_reaction(True)

            if ret is None:
                if value:
                    await ctx.send(f"```py\n{value.__repr__}\n```")  # TODO: should it be repr ?
            else:
                self._last_result = ret
                await ctx.send(f"```py\n{value}{ret}\n```")


async def setup(bot: AluBot):
    await bot.add_cog(CodeRun(bot))
