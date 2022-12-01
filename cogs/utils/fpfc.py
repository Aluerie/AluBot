from __future__ import annotations

from typing import (
    TYPE_CHECKING,
    List, Literal, Dict, Tuple, Callable, Coroutine, Optional, Union
)

from discord import Embed, app_commands

from .distools import send_pages_list
from .twitch import twitchid_by_name
from .var import Clr, MP, Ems

if TYPE_CHECKING:
    from .context import Context
    from asyncpg import Pool
    from discord import Colour, TextChannel


class FeedTools:
    def __init__(
            self,
            *,
            display_name: str,
            db_name: str,
            game_name: str,
            clr: Colour,
            pool: Pool,
            db_ch_col,
            db_pl_col
    ) -> None:
        self.display_name = display_name
        self.db_name = db_name
        self.game_name = game_name
        self.clr = clr
        self.pool = pool

        self.db_ch_col = db_ch_col
        self.db_pl_col = db_pl_col

    async def channel_set_base(
            self,
            ctx: Context,
            channel: Optional[TextChannel] = None,
    ):
        ch = channel or ctx.channel
        if not ch.permissions_for(ctx.guild.me).send_messages:
            em = Embed(
                colour=Clr.error,
                description='I do not have permissions to send messages in that channel :('
            )
            return await ctx.reply(embed=em)  # todo: change this to commands.BotMissingPermissions

        query = f'UPDATE guilds SET {self.db_ch_col}=$1 WHERE id=$2'
        await self.pool.execute(query, ch.id, ctx.guild.id)
        em = Embed(
            colour=self.clr,
            description=
            f'Channel {ch.mention} is set to be the {self.display_name} channel for this server'
        )
        await ctx.reply(embed=em)

    async def channel_disable_base(
            self,
            ctx: Context,
    ):
        query = f'SELECT {self.db_ch_col} FROM guilds WHERE id=$1'
        ch_id = await self.pool.fetchval(query, ctx.guild.id)

        ch = ctx.bot.get_channel(ch_id)
        if ch is None:
            em = Embed(
                colour=Clr.error,
                description=f'{self.display_name} channel is not set or already was reset'
            )
            return await ctx.reply(embed=em)
        query = f'UPDATE guilds SET {self.db_ch_col}=NULL WHERE id=$1'
        await self.pool.execute(query, ctx.guild.id)
        em = Embed(
            colour=self.clr,
            description=f'Channel {ch.mention} is no longer the {self.display_name} channel.'
        )
        await ctx.reply(embed=em)

    async def channel_check_base(
            self,
            ctx: Context,
    ):
        query = f'SELECT {self.db_ch_col} FROM guilds WHERE id=$1'
        ch_id = await self.pool.fetchval(query, ctx.guild.id)
        ch = ctx.bot.get_channel(ch_id)
        if ch is None:
            em = Embed(
                colour=self.clr,
                description=f'{self.display_name} channel is not currently set.'
            )
            return await ctx.reply(embed=em)
        else:
            em = Embed(
                colour=self.clr,
                description=f'{self.display_name} channel is currently set to {ch.mention}.'
            )
            return await ctx.reply(embed=em)

    @staticmethod
    def field_player_name(display_name: str, twitch: Union[int, None]) -> str:
        return f"● [{display_name}](https://www.twitch.tv/{display_name})" if twitch else f"● {display_name}"

    @staticmethod
    def field_player_data(**kwargs):
        ...

    async def database_list_base(self, ctx: Context):
        await ctx.typing()

        query = f'SELECT {self.db_pl_col} FROM guilds WHERE id=$1'
        fav_id_list = await self.pool.fetchval(query, ctx.guild.id)
        ss_dict = dict()

        query = f'SELECT * FROM {self.db_name}'
        rows = await self.pool.fetch(query)
        for row in rows:
            followed = f' {Ems.DankLove}' if row.fav_id in fav_id_list else ''
            key = f"{self.field_player_name(row.name, row.twtv_id)}{followed}"
            if key not in ss_dict:
                ss_dict[key] = []
            ss_dict[key].append(self.field_player_data())  # todo: figure it out idk dude

        ans_array = [f"{k}\n {chr(10).join(ss_dict[k])}" for k in ss_dict]
        ans_array = sorted(list(set(ans_array)), key=str.casefold)

        await send_pages_list(
            ctx,
            ans_array,
            split_size=10,
            colour=Clr.prpl,
            title=f"List of {self.game_name} players in Database",
            footer_text=f'With love, {ctx.guild.me.display_name}'
        )

    @staticmethod
    async def get_check_twitch_id(ctx: Context, twitch_name: str):
        twtv_id = twitchid_by_name(twitch_name.lower())
        if twtv_id is None:
            em = Embed(
                colour=Clr.error,
                description=
                f'Error checking stream {twitch_name}.\n '
                f'User either does not exist or is banned.'
            )
            await ctx.reply(embed=em, ephemeral=True)
            return None

        return twtv_id

    @staticmethod
    async def sort_out_names(
            names: str,
            initial_list: List[int],
            mode: Literal['add', 'remov'],
            data_dict: Dict[str, str],
            get_proper_name_and_id: Callable[[str], Coroutine[str, str]]
    ) -> Tuple[List, List[Embed]]:
        initial_list = set(initial_list)
        res_dict = {
            i: {
                'names': [],
                'embed': None
            }
            for i in ['success', 'already', 'fail']
        }

        for name in [x.strip() for x in names.split(',')]:
            proper_name, named_id = await get_proper_name_and_id(name)
            if named_id is None:
                res_dict['fail']['names'].append(f'`{proper_name}`')
            else:
                if mode == 'add':
                    if named_id in initial_list:
                        res_dict['already']['names'].append(f'`{proper_name}`')
                    else:
                        initial_list.add(named_id)
                        res_dict['success']['names'].append(f'`{proper_name}`')
                elif mode == 'remov':
                    if named_id not in initial_list:
                        res_dict['already']['names'].append(f'`{proper_name}`')
                    else:
                        initial_list.remove(named_id)
                        res_dict['success']['names'].append(f'`{proper_name}`')

        res_dict['success']['colour'] = MP.green()
        res_dict['already']['colour'] = MP.orange()
        res_dict['fail']['colour'] = Clr.error

        for k, v in res_dict.items():
            if len(v['names']):
                v['embed'] = Embed(
                    colour=v['colour']
                ).add_field(
                    name=data_dict[k],
                    value=", ".join(v['names'])
                )
                if k == 'fail':
                    v['embed'].set_footer(
                        text=data_dict['fail_footer']
                    )
        embed_list = [v['embed'] for v in res_dict.values() if v['embed'] is not None]
        return list(initial_list), embed_list

    @staticmethod
    async def x_eq_x(x):
        return x

    @staticmethod
    async def add_remove_autocomplete_work(
            current: str,
            mode: Literal['add', 'remov'],
            *,
            all_items: List[str],
            fav_items: List[str],
            func: Callable = x_eq_x,
            reverse_func: Callable = x_eq_x
    ) -> List[app_commands.Choice[str]]:

        input_strs = [x.strip() for x in current.split(',')]
        try:
            input_items = [await reverse_func(i) for i in input_strs[:-1]]
        except Exception:
            x = 'ERROR: It looks like you already typed something wrong'
            return [app_commands.Choice(name=x, value=x)]

        if mode == 'add':
            fav_items = fav_items + input_items
        if mode == 'remov':
            fav_items = [x for x in fav_items if x not in input_items]

        old_input = [await func(y) for y in input_items]
        answer = [
            ", ".join(old_input + [await func(x)]) for x in all_items
            if (mode == 'add' and x not in fav_items) or (mode == 'remov' and x in fav_items)
        ]
        answer.sort()
        return [
            app_commands.Choice(name=x, value=x)
            for x in answer if current.lower() in x.lower()
        ][:25]
