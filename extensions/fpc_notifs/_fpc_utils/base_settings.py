from __future__ import annotations

from difflib import get_close_matches
from typing import TYPE_CHECKING, Any, Awaitable, Callable, Optional, Union

import discord
from discord import app_commands
from discord.ext import commands

from utils import AluGuildContext, const
from utils.pages import EnumeratedPages

from .._base import FPCCog
from .views import CharacterPages, CharacterPageSource

if TYPE_CHECKING:
    from bot import AluBot

__all__ = ('FPCSettingsBase',)


class FPCSettingsBase(FPCCog):
    """Base class for cogs representing FPC (Favourite Player+Character) feature
    for different games:

    * Dota 2
    * League of Legends
    * and probably more to come.

    Since many base features can be generalized -
    here is the base class containing base methods.

    Attributes
    -----------
    colour: discord.Colour
        The colour that will be used for all embeds related to this game.
    game: str
        Name of the game. This is used for `game` column in `fpc` SQL table.
        Important!!!
        1) It's assumed that SQL tables created for FPC are named accordingly.
        Meaning, f'{self.game}_accounts' should be a table of accounts for the game.
        2) name for slash command is assumed to be /{self.game}, i.e. /dota player add
    display_game: str
        Display name of the game. This is used in response strings mentioning the game.
    display_icon: str
        Display icon for the game. This is used in footnote icons mentioning the game.
    extra_account_info_columns: List[str]
        Extra column-names for columns in "{self.game}_accounts" table.
        For example, you need `platform` as region name in League of Legends in order to find the account.
    character_name_by_id: Callable[[int], Awaitable[str]]
        Function that gets character name by its id, i.e. 1 -> 'Anti-Mage'.
    character_id_by_name: Callable[[str], Awaitable[int]]
        Function that gets character id by its name, i.e. 'Anti-Mage' -> 1.
    all_character_names: Callable[[], Awaitable[List[str]]]
        Function that fetches a list of all characters from the game.
    character_word_plural: str
        Just a word to describe the characters for the game,
        i.e. "heroes" for Dota 2, "champions" for LoL, "agents" for Valorant.
    """

    def __init__(
        self,
        bot: AluBot,
        *args,
        colour: discord.Colour,
        game: str,
        game_mention: str,
        game_icon: str,
        extra_account_info_columns: list[str],
        character_name_by_id: Callable[[int], Awaitable[str]],
        character_id_by_name: Callable[[str], Awaitable[int]],
        all_character_names: Callable[[], Awaitable[list[str]]],
        character_word_plural: str,
        **kwargs,
    ) -> None:
        super().__init__(bot, *args, **kwargs)
        self.colour: discord.Colour = colour
        self.game: str = game
        self.game_mention: str = game_mention
        self.game_icon: str = game_icon
        self.extra_account_info_columns: list[str] = extra_account_info_columns
        self.character_name_by_id: Callable[[int], Awaitable[str]] = character_name_by_id
        self.character_id_by_name: Callable[[str], Awaitable[int]] = character_id_by_name
        self.all_character_names: Callable[[], Awaitable[list[str]]] = all_character_names
        self.character_gather_word: str = character_word_plural

    async def get_ctx(self, ctx_ntr: AluGuildContext | discord.Interaction[AluBot]) -> AluGuildContext:
        """Since we have quirks about"""
        return await AluGuildContext.from_interaction(ctx_ntr) if isinstance(ctx_ntr, discord.Interaction) else ctx_ntr

    async def channel_set(
        self,
        ctx_ntr: AluGuildContext | discord.Interaction[AluBot],
        channel: Optional[discord.TextChannel],
    ) -> None:
        """Base function for setting channel for FPC Feed feature"""
        ctx = await self.get_ctx(ctx_ntr)

        ch = channel or ctx.channel

        # it's probably not needed
        if not isinstance(ch, discord.TextChannel):
            raise TypeError('You can\'t select a channel of this type for FPC channel.')

        if not ch.permissions_for(ctx.guild.me).send_messages:
            # TODO: There is probably a better error type for this or like BotMissingPerms(send_messages)
            msg = 'I do not have permission to `send_messages` in that channel'
            raise app_commands.BotMissingPermissions([msg])

        query = f'''INSERT INTO {self.game}_settings (guild_id, guild_name, channel_id)
                    VALUES ($1, $2, $3)
                    ON CONFLICT (guild_id) DO UPDATE
                        SET channel_id=$3;
                '''
        await ctx.pool.execute(query, ctx.guild.id, ctx.guild.name, ch.id)

        e = discord.Embed(colour=self.colour, title='FPC (Favourite Player+Character) channel set')
        e.description = f'Notifications will be sent to {ch.mention}.'
        e.set_author(name=self.game_mention, icon_url=self.game_icon)
        await ctx.reply(embed=e)

    async def is_fpc_channel_set(self, ctx: AluGuildContext, raise_: bool = False):
        query = f'SELECT channel_id FROM {self.game}_settings WHERE guild_id=$1'
        ch_id = await ctx.pool.fetchval(query, ctx.guild.id)
        if ch_id:
            return ch_id
        elif raise_:
            # TODO: better error, maybe its own embed ?
            msg = (
                'I\'m sorry, but you cannot use this command without setting up FPC (Favourite Player+Character) channel'
                f' first. Please, use `/{self.game} channel set` to assign it.'
            )
            raise commands.BadArgument(msg)
        else:
            return False

    async def get_fpc_channel(self, ctx: AluGuildContext) -> discord.TextChannel:
        ch_id = await self.is_fpc_channel_set(ctx)

        if not ch_id:
            # TODO: better error, maybe its own embed ?
            msg = (
                f'FPC (Favourite Player+Character) notifications channel for {self.game_mention} '
                'is not set or already was reset.'
            )
            raise commands.BadArgument(msg)

        ch = ctx.client.get_channel(ch_id)
        assert isinstance(ch, discord.TextChannel)
        return ch

    async def channel_disable(self, ctx_ntr: AluGuildContext | discord.Interaction[AluBot]) -> None:
        """Base function for disabling channel for FPC Feed feature"""
        ctx = await self.get_ctx(ctx_ntr)

        ch = await self.get_fpc_channel(ctx)

        warn_embed = discord.Embed(colour=self.colour, title='Confirmation Prompt')
        warn_embed.description = f'Are you sure you want to disable FPC notifications in {ch.mention}?\n\n'
        warn_embed.add_field(
            name='!!!', value='This will also reset/delete players/characters data in the bot database.'
        )
        warn_embed.set_author(name=self.game_mention, icon_url=self.game_icon)
        if not await ctx.prompt(embed=warn_embed):
            cancel_embed = discord.Embed(colour=discord.Colour.red())
            cancel_embed.description = 'You pressed "Cancel"'
            await ctx.reply(embed=cancel_embed)
            return

        query = f'''DELETE FROM {self.game}_settings WHERE guild_id=$1'''
        await ctx.pool.execute(query, ctx.guild.id)
        e = discord.Embed(colour=discord.Colour.green(), title='FPC (Favourite Player+Character) channel disabled')
        e.description = f'Notifications will not be sent to {ch.mention} anymore. Your data was deleted.'
        e.set_author(name=self.game_mention, icon_url=self.game_icon)
        await ctx.reply(embed=e)

    async def channel_check(self, ctx_ntr: AluGuildContext | discord.Interaction[AluBot]) -> None:
        """Base function for checking if channel is set for FPC Feed feature"""
        ctx = await self.get_ctx(ctx_ntr)

        ch = await self.get_fpc_channel(ctx)

        e = discord.Embed(colour=self.colour, title='FPC (Favourite Player+Character) channel check')
        e.description = f'Notifications are set to be sent to {ch.mention}.'
        e.set_author(name=self.game_mention, icon_url=self.game_icon)
        await ctx.reply(embed=e)

    @staticmethod
    def player_name_string(display_name: str, twitch: Union[int, None]) -> str:
        if twitch:
            return f"\N{BLACK CIRCLE} [{display_name}](https://www.twitch.tv/{display_name})"
        else:
            return f"\N{BLACK CIRCLE} {display_name}"

    @staticmethod
    def cmd_usage_str(**kwargs):
        raise NotImplementedError

    @staticmethod
    def player_acc_string(**kwargs) -> str:
        raise NotImplementedError

    def player_name_acc_string(self, display_name: str, twitch_id: Union[int, None], **kwargs) -> str:
        return f'{self.player_name_string(display_name, twitch_id)}\n' f'{self.player_acc_string(**kwargs)}'

    async def database_list(self, ctx_ntr: AluGuildContext | discord.Interaction[AluBot]) -> None:
        """Base function for sending database list embed"""
        ctx = await self.get_ctx(ctx_ntr)
        await ctx.typing()
        query = f'SELECT player_name FROM {self.game}_favourite_players WHERE guild_id=$1'
        favourite_player_list = [r for r, in await ctx.client.pool.fetch(query, ctx.guild.id)]

        columns = ', '.join(
            ['a.id', 'p.name_lower', 'display_name', 'twitch_id', 'a.name_lower'] + self.extra_account_info_columns
        )
        query = f"""SELECT {columns}
                    FROM {self.game}_players p
                    JOIN {self.game}_accounts a
                    ON p.name_lower = a.name_lower
                    ORDER BY {'display_name'} 
                """
        rows = await ctx.client.pool.fetch(query) or []

        player_dict = dict()

        for row in rows:
            if row.name_lower not in player_dict:
                followed = (
                    ' {0} {0} {0}'.format(const.Emote.DankLove) if row.name_lower in favourite_player_list else ''
                )
                player_dict[row.name_lower] = {
                    'name': f"{self.player_name_string(row.display_name, row.twitch_id)}{followed}",
                    'info': [],
                }
            kwargs = {col: row[col] for col in ['id'] + self.extra_account_info_columns}
            player_dict[row.name_lower]['info'].append(self.player_acc_string(**kwargs))

        ans_array = [f"{v['name']}\n{chr(10).join(v['info'])}" for v in player_dict.values()]

        pgs = EnumeratedPages(
            ctx,
            ans_array,
            per_page=10,
            no_enumeration=True,
            colour=self.colour,
            title=f"List of {self.game_mention} players in Database",
            footer_text=f'With love, {ctx.guild.me.display_name}',
            author_name=self.game_mention,
            author_icon=self.game_icon,
        )
        await pgs.start()

    async def get_player_dict(self, *, name_flag: str, twitch_flag: bool) -> dict:
        name_lower = name_flag.lower()
        if twitch_flag:
            twitch_id, display_name, profile_image = await self.bot.twitch.fpc_data_by_login(name_lower)
        else:
            twitch_id, display_name, profile_image = None, name_flag, discord.utils.MISSING

        return {
            'name_lower': name_lower,
            'display_name': display_name,
            'twitch_id': twitch_id,
            'profile_image': profile_image,
        }

    async def get_account_dict(self, **kwargs) -> dict:
        ...

    async def check_if_already_in_database(self, account_dict: dict):
        query = f""" SELECT display_name, name_lower
                    FROM {self.game}_players 
                    WHERE name_lower =(
                        SELECT name_lower
                        FROM {self.game}_accounts
                        WHERE id=$1
                    )
                """
        user = await self.bot.pool.fetchrow(query, account_dict['id'])
        if user is not None:
            # TODO: better error
            raise commands.BadArgument(
                'This account is already in the database.\n'
                f'It is marked as {user.display_name}\'s account.\n\n'
                f'Did you mean to use `/{self.game} player add name1: {user.name_lower}` to add the player into your fav list?'
            )

    async def database_add(
        self, ctx_ntr: AluGuildContext | discord.Interaction[AluBot], player_dict: dict, account_dict: dict
    ):
        """Base function for adding accounts into the database"""
        ctx = await self.get_ctx(ctx_ntr)
        await ctx.typing()
        await self.check_if_already_in_database(account_dict)

        query = f"""INSERT INTO {self.game}_players
                        (name_lower, display_name, twitch_id)
                            VALUES ($1, $2, $3)
                        ON CONFLICT (name_lower) DO NOTHING
                """
        await ctx.client.pool.execute(
            query, player_dict['name_lower'], player_dict['display_name'], player_dict['twitch_id']
        )

        dollars = [f'${i}' for i in range(1, len(self.extra_account_info_columns) + 3)]  # [$1, $2, ... ]
        query = f"""INSERT INTO {self.game}_accounts
                    (name_lower, id, {', '.join(self.extra_account_info_columns)})
                    VALUES {'('}{', '.join(dollars)}{')'}
                """
        await ctx.client.pool.execute(query, player_dict['name_lower'], *account_dict.values())
        e = discord.Embed(colour=self.colour)
        e.add_field(
            name=f'Successfully added the account to the database',
            value=self.player_name_acc_string(player_dict['display_name'], player_dict['twitch_id'], **account_dict),
        )
        e.set_author(name=self.game_mention, icon_url=self.game_icon)
        e.set_thumbnail(url=player_dict['profile_image'])
        await ctx.reply(embed=e)
        e.colour = const.MaterialPalette.green(shade=200)
        e.set_author(name=ctx.user, icon_url=ctx.user.display_avatar.url)
        await self.bot.hideout.global_logs.send(embed=e)

    async def database_request(
        self,
        ctx_ntr: AluGuildContext | discord.Interaction[AluBot],
        player_dict: dict,
        account_dict: dict,
    ) -> None:
        """Base function for requesting to add accounts into the database"""
        ctx = await self.get_ctx(ctx_ntr)
        await ctx.typing()
        await self.check_if_already_in_database(account_dict)

        player_string = self.player_name_acc_string(
            player_dict['display_name'], player_dict['twitch_id'], **account_dict
        )
        warn_e = discord.Embed(colour=self.colour, title='Confirmation Prompt')
        warn_e.description = (
            'Are you sure you want to request this streamer steam account to be added into the database?\n'
            'This information will be sent to Aluerie. Please, double check before confirming.'
        )
        warn_e.add_field(name='Request to add an account into the database', value=player_string)
        warn_e.set_author(name=self.game_mention, icon_url=self.game_icon)
        warn_e.set_thumbnail(url=player_dict['profile_image'])

        if not await ctx.client.prompt(ctx, embed=warn_e):
            cancel_embed = discord.Embed(colour=discord.Colour.red())
            cancel_embed.description = 'You pressed "Cancel"'
            await ctx.reply(embed=cancel_embed)
            return

        e = discord.Embed(colour=self.colour)
        e.add_field(name='Successfully made a request to add the account into the database', value=player_string)
        await ctx.reply(embed=e)

        warn_e.colour = const.MaterialPalette.orange(shade=200)
        warn_e.title = ''
        warn_e.description = ''
        warn_e.set_author(name=ctx.user, icon_url=ctx.user.display_avatar.url)
        # cmd_str = ' '.join(f'{k}: {v}' for k, v in flags.__dict__.items())
        # warn_em.add_field(name='Command', value=f'`$dota stream add {cmd_str}`', inline=False)
        cmd_usage_str = f"name: {player_dict['display_name']} {self.cmd_usage_str(**account_dict|player_dict)}"
        warn_e.add_field(name='Command', value=f'/database {self.game} add {cmd_usage_str}')
        await self.hideout.global_logs.send(embed=warn_e)

    async def database_remove(
        self,
        ctx_ntr: AluGuildContext | discord.Interaction[AluBot],
        name_lower: Optional[str],
        account_id: Optional[Union[str, int]],  # steam_id for dota, something else for lol
    ) -> None:
        """Base function for removing accounts from the database"""
        ctx = await self.get_ctx(ctx_ntr)
        await ctx.typing()
        if name_lower is None and account_id is None:
            raise commands.BadArgument('You need to provide at least one of flags: `name`, `steam`')

        if account_id:
            if name_lower:  # check for both name_lower and account_id
                query = f"""SELECT a.id 
                            FROM {self.game}_players p
                            JOIN {self.game}_accounts a
                            ON p.name_lower = a.name_lower
                            WHERE a.id=$1 AND p.name_lower=$2
                        """
                val = await ctx.client.pool.fetchval(query, account_id, name_lower)
                if val is None:
                    raise commands.BadArgument(
                        'This account either is not in the database ' 'or does not belong to the said player'
                    )

            # query for account only
            query = f"""WITH del_child AS (
                            DELETE FROM {self.game}_accounts
                            WHERE  id = $1
                            RETURNING name_lower, id
                            )
                        DELETE FROM {self.game}_players p
                        USING  del_child x
                        WHERE  p.name_lower = x.name_lower
                        AND    NOT EXISTS (
                            SELECT 1
                            FROM   {self.game}_accounts c
                            WHERE  c.name_lower = x.name_lower
                            AND    c.id <> x.id
                            )
                        RETURNING display_name
                    """
            ans_name = await ctx.client.pool.fetchval(query, account_id)
            if ans_name is None:
                raise commands.BadArgument('There is no account with such account details')
        else:
            # query for name_lower only
            query = f"""DELETE FROM {self.game}_players
                        WHERE name_lower=$1
                        RETURNING display_name
                    """
            ans_name = await ctx.client.pool.fetchval(query, name_lower)
            if ans_name is None:
                raise commands.BadArgument('There is no account with such player name')

        e = discord.Embed(colour=self.colour)
        msg = 'Successfully removed account(-s) from the database'
        e.add_field(name=msg, value=f'{ans_name}{" - " + str(account_id) if account_id else ""}')
        e.set_author(name=self.game_mention, icon_url=self.game_icon)
        await ctx.reply(embed=e)

    def construct_the_embed(
        self, s_names: list[str], a_names: list[str], f_names: list[str], *, gather_word: str, mode_add: bool
    ) -> discord.Embed:
        e = discord.Embed()
        e.set_author(name=self.game_mention, icon_url=self.game_icon)
        if s_names:
            e.colour = const.MaterialPalette.green(shade=500)
            msg = f"Success: {gather_word} were {'added to' if mode_add else 'removed from'} your list"
            e.add_field(name=msg, value=f"`{', '.join(s_names)}`", inline=False)
        if a_names:
            e.colour = const.MaterialPalette.orange(shade=500)
            msg = f'Already: {gather_word} are already {"" if mode_add else "not"} in your list'
            e.add_field(name=msg, value=f"`{', '.join(a_names)}`", inline=False)
        if f_names:
            e.colour = const.MaterialPalette.red(shade=500)
            msg = f'Fail: These {gather_word} are not in the database'
            e.add_field(name=msg, value=f"`{', '.join(f_names)}`", inline=False)
        return e

    @staticmethod
    def get_names_list_from_locals(
        ctx: AluGuildContext | discord.Interaction[AluBot],
        local_dict: dict[str, Any],
    ) -> list[str]:
        if isinstance(ctx, discord.Interaction):
            # if it's interaction then locals is dictionary with keys
            # "cog(self), ntr, name1, name2, ..." where each name is a string
            # meaning we only need [2:]
            names = list(dict.fromkeys([name for name in list(local_dict.values())[2:] if name is not None]))
        else:
            # if it's Context then our locals is dictionary with keys
            # "cog(self), ctx, char_names" where char_names is a string
            # meaning we only need [2] and then strip all commas
            names_string = list(local_dict.values())[2]
            names = [b for x in names_string.split(",") if (b := x.lstrip().rstrip())]
        return names

    async def player_add_remove(
        self, ctx_ntr: AluGuildContext | discord.Interaction[AluBot], local_dict: dict[str, Any], *, mode_add: bool
    ) -> None:
        """
        Base function to add/remove players from user's favourite list.

        Parameters
        ----------
        ntr:
        local_dict :
        mode_add :
        """
        player_names = self.get_names_list_from_locals(ctx_ntr, local_dict)
        ctx = await self.get_ctx(ctx_ntr)
        await ctx.typing()
        await self.is_fpc_channel_set(ctx, raise_=True)

        if not player_names:
            raise commands.BadArgument("You cannot use this command without naming at least one player.")

        query = f'SELECT player_name FROM dota_favourite_players WHERE guild_id=$1'
        fav_names = [r for r, in await ctx.client.pool.fetch(query, ctx.guild.id)]
        query = f"""SELECT name_lower, display_name 
                    FROM {self.game}_players
                    WHERE name_lower=ANY($1)
                """
        success_and_already_rows = await ctx.client.pool.fetch(query, [name.lower() for name in player_names])
        # The following notations are assumed logically for mode_add being `True`.
        # +-----------------+-----------------------+-----------------------+
        # | variable_name   | `mode_add = True`     | `mode_add = False`    |
        # +=================+=======================+=======================+
        # | success         | successfully added    | already removed       |
        # +-----------------+-----------------------+-----------------------+
        # | already         | already added         | successfully removed  |
        # +-----------------+-----------------------+-----------------------+
        # | failed          | failed to add         | failed to remove      |
        # +-----------------+-----------------------+-----------------------+

        # ids, which are name_lower for this
        success_ids = [row.name_lower for row in success_and_already_rows if row.name_lower not in fav_names]
        already_ids = [row.name_lower for row in success_and_already_rows if row.name_lower in fav_names]

        # display names
        success_names = [row.display_name for row in success_and_already_rows if row.name_lower not in fav_names]
        already_names = [row.display_name for row in success_and_already_rows if row.name_lower in fav_names]

        failed_names = [
            name for name in player_names if name.lower() not in [row.name_lower for row in success_and_already_rows]
        ]

        if mode_add:
            query = f'''INSERT INTO {self.game}_favourite_players (guild_id, player_name) VALUES ($1, $2)'''
            await ctx.client.pool.executemany(query, [(ctx.guild.id, name) for name in success_ids])

            e = self.construct_the_embed(
                success_names, already_names, failed_names, gather_word='players', mode_add=mode_add
            )
        else:
            query = f'''DELETE FROM {self.game}_favourite_players WHERE guild_id=$1 AND player_name=ANY($2)'''
            await ctx.client.pool.execute(query, ctx.guild.id, already_ids)

            e = self.construct_the_embed(
                already_names, success_names, failed_names, gather_word='players', mode_add=mode_add
            )
        if failed_names:
            text = (
                f'Check your argument or consider adding (for trustees)/requesting such player with '
                f'`/{self.game} database add|request`'
            )
            e.set_footer(text=text)
        await ctx.reply(embed=e)

    async def player_add_remove_autocomplete(
        self, ntr: discord.Interaction, current: str, *, mode_add: bool
    ) -> list[app_commands.Choice[str]]:
        """Base function for player add/remove autocomplete"""
        assert ntr.guild

        query = f'SELECT player_name FROM {self.game}_favourite_players WHERE guild_id=$1'
        fav_ids = [r for r, in await self.bot.pool.fetch(query, ntr.guild.id)]
        clause = 'NOT' if mode_add else ''
        query = f"""SELECT display_name
                    FROM {self.game}_players
                    WHERE {clause} name_lower=ANY($1)
                    ORDER BY similarity(display_name, $2) DESC
                    LIMIT 6;
                """
        rows = await self.bot.pool.fetch(query, fav_ids, current)
        namespace_list = [x.lower() for x in ntr.namespace.__dict__.values() if x != current]
        choice_list = [x for x in [a for a, in rows] if x.lower() not in namespace_list]
        return [app_commands.Choice(name=n, value=n) for n in choice_list if current.lower() in n.lower()]

    async def player_list(self, ctx_ntr: AluGuildContext | discord.Interaction[AluBot]):
        """Base function for player list command"""
        ctx = await self.get_ctx(ctx_ntr)

        await ctx.typing()
        query = f'SELECT player_name FROM {self.game}_favourite_players WHERE guild_id=$1'
        fav_ids = [r for r, in await self.bot.pool.fetch(query, ctx.guild.id)]

        query = f"""SELECT display_name, twitch_id 
                    FROM {self.game}_players
                    WHERE name_lower=ANY($1)
                    ORDER BY display_name
                """
        rows = await self.bot.pool.fetch(query, fav_ids) or []

        player_names = [self.player_name_string(row.display_name, row.twitch_id) for row in rows]
        e = discord.Embed(title=f'List of favourite players', colour=self.colour)
        e.description = '\n'.join(player_names)
        e.set_author(name=self.game_mention, icon_url=self.game_icon)
        await ctx.reply(embed=e)

    async def character_add_remove(
        self, ctx_ntr: AluGuildContext | discord.Interaction[AluBot], local_dict: dict[str, Any], *, mode_add: bool
    ):
        """Base function for adding/removing characters such as heroes/champs from fav lists"""
        character_names = self.get_names_list_from_locals(ctx_ntr, local_dict)
        ctx = await self.get_ctx(ctx_ntr)

        if not character_names:
            raise commands.BadArgument("You cannot use this command without naming at least one character.")

        await ctx.typing()
        await self.is_fpc_channel_set(ctx, raise_=True)

        query = f'SELECT character_id FROM {self.game}_favourite_characters WHERE guild_id=$1'
        fav_ids: list[int] = [r for r, in await ctx.client.pool.fetch(query, ctx.guild.id)]

        failed_names, success_and_already_ids = [], []
        for name in character_names:
            try:
                success_and_already_ids.append(await self.character_id_by_name(name))
            except KeyError:
                failed_names.append(name)

        # ids
        success_ids = [i for i in success_and_already_ids if i not in fav_ids]
        already_ids = [i for i in success_and_already_ids if i in fav_ids]
        # display names
        success_names = [await self.character_name_by_id(i) for i in success_ids]
        already_names = [await self.character_name_by_id(i) for i in already_ids]

        if mode_add:
            query = f'''INSERT INTO {self.game}_favourite_characters (guild_id, character_id) VALUES ($1, $2)'''
            await ctx.client.pool.executemany(query, [(ctx.guild.id, name) for name in success_ids])

            e = self.construct_the_embed(
                success_names, already_names, failed_names, gather_word=self.character_gather_word, mode_add=mode_add
            )
        else:
            query = f'''DELETE FROM {self.game}_favourite_characters WHERE guild_id=$1 AND character_id=ANY($2)'''
            await ctx.client.pool.execute(query, ctx.guild.id, already_ids)
            e = self.construct_the_embed(
                already_names, success_names, failed_names, gather_word=self.character_gather_word, mode_add=mode_add
            )
        await ctx.reply(embed=e)

    async def character_add_remove_autocomplete(
        self, ntr: discord.Interaction, current: str, *, mode_add: bool
    ) -> list[app_commands.Choice[str]]:
        """Base function for character add/remove autocomplete"""
        query = f'SELECT character_id FROM {self.game}_favourite_characters WHERE guild_id=$1'
        assert ntr.guild
        fav_ids: list[int] = [r for r, in await self.bot.pool.fetch(query, ntr.guild.id)]

        fav_names = [await self.character_name_by_id(i) for i in fav_ids]

        if mode_add:
            all_names = await self.all_character_names()
            choice_names = [i for i in all_names if i not in fav_names]
        else:
            choice_names = fav_names

        namespace_list = [x.lower() for x in ntr.namespace.__dict__.values() if x != current]
        choice_names = [x for x in choice_names if x.lower() not in namespace_list]

        precise_match = [x for x in choice_names if x.lower().startswith(current.lower())]
        precise_match.sort()

        close_match = get_close_matches(current, choice_names, n=5, cutoff=0)

        return_list = list(dict.fromkeys(precise_match + close_match))
        return [app_commands.Choice(name=n, value=n) for n in return_list][:25]

    async def character_list(self, ctx_ntr: AluGuildContext | discord.Interaction[AluBot]) -> None:
        """Base function for character list commands"""
        ctx = await self.get_ctx(ctx_ntr)
        await ctx.typing()
        query = f'SELECT character_id FROM {self.game}_favourite_characters WHERE guild_id=$1'
        fav_ids: list[int] = [r for r, in await ctx.client.pool.fetch(query, ctx.guild.id)]
        fav_names = [f'{await self.character_name_by_id(i)} - `{i}`' for i in fav_ids]

        e = discord.Embed(title=f'List of your favourite {self.character_gather_word}', colour=self.colour)
        e.description = '\n'.join(fav_names)
        await ctx.reply(embed=e)

    async def spoil(self, ctx_ntr: AluGuildContext | discord.Interaction[AluBot], spoil: bool):
        """Base function for spoil commands"""
        ctx = await self.get_ctx(ctx_ntr)

        await self.is_fpc_channel_set(ctx, raise_=True)

        query = f'''UPDATE {self.game}_settings 
                    SET spoil=$2 WHERE guild_id=$1;
                '''
        await self.bot.pool.execute(query, ctx.guild.id, spoil)
        e = discord.Embed(description=f"Changed spoil value to {spoil}", colour=self.colour)
        await ctx.reply(embed=e)

    async def get_character_data(self):
        raise NotImplementedError

    async def character_setup(self, ctx_ntr: AluGuildContext | discord.Interaction[AluBot]):
        """New interactive version of favourite character selection.

        This might replace the old one.
        """

        ctx = await self.get_ctx(ctx_ntr)
        await ctx.typing()
        await self.is_fpc_channel_set(ctx, raise_=True)

        data = await self.get_character_data()

        new_hero_list = [(id_, name) for id_, name in data['name_by_id'].items()]
        new_hero_list.sort(key=lambda x: x[1])

        pages = CharacterPages(
            ctx, CharacterPageSource(new_hero_list), self.game, self.colour, self.character_gather_word
        )
        await pages.start()
        # await ctx.send(content=content)
