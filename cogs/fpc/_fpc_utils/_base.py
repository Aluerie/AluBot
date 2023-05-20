from __future__ import annotations

from difflib import get_close_matches
from typing import TYPE_CHECKING, Any, Awaitable, Callable, Dict, List, Optional, Union

import discord
from discord import app_commands
from discord.ext import commands

from utils import AluCog, AluContext, const
from utils.pagination import EnumeratedPages

if TYPE_CHECKING:
    from utils import AluBot


class FPCBase(AluCog):
    """Base class for cogs representing FPC (Favourite Player+Character) feature
    for different games:

    * Dota 2
    * League of Legends
    * and probably more to come.

    Since many base features can be generalized -
    here is the base class containing base methods.

    Attributes
    -----------
    colour: :class:`discord.Colour`
        The colour that will be used for all embeds related to this game.
    game: :class:`str`
        Name of the game. This is used for `game` column in `fpc` SQL table.
        Important!!!
        1) It's assumed that SQL tables created for FPC are named accordingly.
        Meaning, f'{self.game}_accounts' should be a table of accounts for the game.
        2) name for slash command is assumed to be /{self.game}, i.e. /dota player add
    display_game: :class:`str`
        Display name of the game. This is used in response strings mentioning the game.
    display_icon: :class:`str`
        Display icon for the game. This is used in footnote icons mentioning the game.
    extra_account_info_columns: :class:`List[str]`
        Extra column-names for columns in "{self.game}_accounts" table.
        For example, you need `platform` as region name in League of Legends in order to find the account.
    """

    def __init__(
        self,
        bot: AluBot,
        # *args,
        colour: discord.Colour,
        game: str,
        game_mention: str,
        game_icon: str,
        extra_account_info_columns: List[str],
        character_name_by_id: Callable[[int], Awaitable[str]],
        character_id_by_name: Callable[[str], Awaitable[int]],
        all_character_names: Callable[[], Awaitable[List[str]]],
        character_gather_word: str,
        # **kwargs,
    ) -> None:
        super().__init__(bot)  # , *args, **kwargs)
        self.colour: discord.Colour = colour
        self.game: str = game
        self.game_mention: str = game_mention
        self.game_icon: str = game_icon
        self.extra_account_info_columns: List[str] = extra_account_info_columns
        self.character_name_by_id: Callable[[int], Awaitable[str]] = character_name_by_id
        self.character_id_by_name: Callable[[str], Awaitable[int]] = character_id_by_name
        self.all_character_names: Callable[[], Awaitable[List[str]]] = all_character_names
        self.character_gather_word: str = character_gather_word

    async def channel_set(
        self,
        ntr: discord.Interaction[AluBot],
        channel: Optional[discord.TextChannel],
    ) -> None:
        """Base function for setting channel for FPC Feed feature"""
        ch = channel or ntr.channel

        # it's probably not needed
        if not isinstance(ch, discord.TextChannel):
            raise TypeError('You can\'t select a channel of this type for FPC channel.')

        assert ntr.guild and ch

        if not ch.permissions_for(ntr.guild.me).send_messages:
            # TODO: There is probably a better error type for this or like BotMissingPerms(send_messages)
            msg = 'I do not have permission to `send_messages` in that channel'
            raise app_commands.BotMissingPermissions([msg])

        query = f'''INSERT INTO fpc (game, guild_id, channel_id)
                    VALUES ($1, $2, $3)
                    ON CONFLICT (game, guild_id) DO UPDATE
                        SET channel_id=$3;
                '''
        await ntr.client.pool.execute(query, self.game, ntr.guild.id, ch.id)

        e = discord.Embed(colour=self.colour, title='FPC (Favourite Player+Character) channel set')
        e.description = f'Notifications will be sent to {ch.mention}.'
        e.set_footer(icon_url=self.game_icon, text=self.game_mention)
        await ntr.response.send_message(embed=e)

    async def get_fpc_channel(self, ntr: discord.Interaction[AluBot]) -> discord.TextChannel:
        assert ntr.guild

        query = f'SELECT channel_id FROM fpc WHERE guild_id=$1 AND game=$2'
        ch_id = await ntr.client.pool.fetchval(query, ntr.guild.id, self.game)

        if ch_id is None:
            # TODO: better error, maybe its own embed ?
            msg = (
                f'FPC (Favourite Player+Character) notifications channel for {self.game_mention}'
                'is not set or already was reset.'
            )
            raise commands.BadArgument(msg)

        ch = ntr.client.get_channel(ch_id)
        assert isinstance(ch, discord.TextChannel)
        return ch

    async def channel_disable(self, ntr: discord.Interaction[AluBot]) -> None:
        """Base function for disabling channel for FPC Feed feature"""
        assert ntr.guild

        ch = await self.get_fpc_channel(ntr)

        query = f'''INSERT INTO fpc (game, guild_id, channel_id)
                    VALUES ($1, $2, NULL)
                    ON CONFLICT (game, guild_id) DO UPDATE
                        SET channel_id=NULL;
                '''
        await ntr.client.pool.execute(query, ntr.guild.id)
        e = discord.Embed(colour=self.colour, title='FPC (Favourite Player+Character) channel disabled')
        e.description = (
            f'Notifications will not be sent to {ch.mention} anymore.'
            'Your data was not affected in case it was a miss-click or something.'
        )
        e.set_footer(icon_url=self.game_icon, text=self.game_mention)
        await ntr.response.send_message(embed=e)

    async def channel_check(self, ntr: discord.Interaction[AluBot]) -> None:
        """Base function for checking if channel is set for FPC Feed feature"""
        assert ntr.guild

        ch = await self.get_fpc_channel(ntr)

        e = discord.Embed(colour=self.colour, title='FPC (Favourite Player+Character) channel check')
        e.description = f'Notifications are set to be sent to {ch.mention}.'
        e.set_footer(icon_url=self.game_icon, text=self.game_mention)
        await ntr.response.send_message(embed=e)

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

    async def database_list(self, ntr: discord.Interaction[AluBot]) -> None:
        """Base function for sending database list embed"""
        await ntr.response.defer()

        assert ntr.guild

        query = f'SELECT players FROM fpc WHERE guild_id=$1 AND game=$2'
        favourite_player_list = await ntr.client.pool.fetchval(query, ntr.guild.id, self.game) or []

        columns = ', '.join(['player_id', 'display_name', 'twitch_id', 'a.id'] + self.extra_account_info_columns)
        query = f"""SELECT {columns}
                    FROM {self.game}_players p
                    JOIN {self.game}_accounts a
                    ON p.id = a.player_id
                    ORDER BY {'display_name'} 
                """
        rows = await ntr.client.pool.fetch(query) or []

        player_dict = dict()

        for row in rows:
            if row.player_id not in player_dict:
                followed = ' {0} {0} {0}'.format(const.Emote.DankLove) if row.player_id in favourite_player_list else ''
                player_dict[row.player_id] = {
                    'name': f"{self.player_name_string(row.display_name, row.twitch_id)}{followed}",
                    'info': [],
                }
            kwargs = {col: row[col] for col in ['id'] + self.extra_account_info_columns}
            player_dict[row.player_id]['info'].append(self.player_acc_string(**kwargs))

        ans_array = [f"{v['name']}\n{chr(10).join(v['info'])}" for v in player_dict.values()]

        pgs = EnumeratedPages(
            ntr,
            ans_array,
            per_page=10,
            no_enumeration=True,
            colour=self.colour,
            title=f"List of {self.game_mention} players in Database",
            footer_text=f'With love, {ntr.guild.me.display_name}',
        )
        await pgs.start()

    async def get_player_dict(self, *, name_flag: str, twitch_flag: bool) -> dict:
        name_lower = name_flag.lower()
        if twitch_flag:
            twitch_id, display_name = await self.bot.twitch.twitch_id_and_display_name_by_login(name_lower)
        else:
            twitch_id, display_name = None, name_flag

        return {'name_lower': name_lower, 'display_name': display_name, 'twitch_id': twitch_id}

    async def get_account_dict(self, **kwargs) -> dict:
        ...

    async def check_if_already_in_database(self, account_dict: dict):
        query = f""" SELECT display_name, name_lower
                    FROM {self.game}_players 
                    WHERE id =(
                        SELECT player_id
                        FROM {self.game}_accounts
                        WHERE id=$1
                    )
                """
        user = await self.bot.pool.fetchrow(query, account_dict['id'])
        if user is not None:
            # TODO: better error
            raise commands.BadArgument(
                'This steam account is already in the database.\n'
                f'It is marked as {user.display_name}\'s account.\n\n'
                f'Did you mean to use `/dota player add {user.name_lower}` to add the stream into your fav list?'
            )

    async def database_add(self, ntr: discord.Interaction[AluBot], player_dict: dict, account_dict: dict):
        """Base function for adding accounts into the database"""
        await ntr.response.defer()
        await self.check_if_already_in_database(account_dict)

        query = f"""WITH e AS (
                        INSERT INTO {self.game}_players
                            (name_lower, display_name, twitch_id)
                                VALUES ($1, $2, $3)
                            ON CONFLICT DO NOTHING
                            RETURNING id
                    )
                    SELECT * FROM e
                    UNION 
                        SELECT {'id'} FROM {self.game}_players WHERE {'name_lower'}=$1
                """
        player_id = await ntr.client.pool.fetchval(query, *player_dict.values())
        dollars = [f'${i}' for i in range(1, len(self.extra_account_info_columns) + 3)]  # [$1, $2, ... ]
        query = f"""INSERT INTO {self.game}_accounts
                    (player_id, id, {', '.join(self.extra_account_info_columns)})
                    VALUES {'('}{', '.join(dollars)}{')'}
                """
        await ntr.client.pool.execute(query, player_id, *account_dict.values())
        e = discord.Embed(colour=self.colour)
        e.add_field(
            name=f'Successfully added the account to the database',
            value=self.player_name_acc_string(player_dict['display_name'], player_dict['twitch_id'], **account_dict),
        )
        e.set_footer(text=self.game_mention, icon_url=self.game_icon)
        await ntr.followup.send(embed=e)
        e.colour = const.MaterialPalette.green(shade=200)
        e.set_author(name=ntr.user, icon_url=ntr.user.display_avatar.url)
        await self.bot.hideout.global_logs.send(embed=e)

    async def database_request(
        self,
        ntr: discord.Interaction[AluBot],
        player_dict: dict,
        account_dict: dict,
    ) -> None:
        """Base function for requesting to add accounts into the database"""
        await ntr.response.defer()
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
        warn_e.set_footer(text=self.game_mention, icon_url=self.game_icon)
        if not await ntr.client.prompt(ntr, embed=warn_e):
            assert isinstance(ntr.channel, discord.TextChannel)
            await ntr.channel.send('Aborting...', delete_after=5.0)
            return

        e = discord.Embed(colour=self.colour)
        e.add_field(name='Successfully made a request to add the account into the database', value=player_string)
        await ntr.response.send_message(embed=e)

        warn_e.colour = const.MaterialPalette.orange(shade=200)
        warn_e.title = ''
        warn_e.description = ''
        warn_e.set_author(name=ntr.user, icon_url=ntr.user.display_avatar.url)
        # cmd_str = ' '.join(f'{k}: {v}' for k, v in flags.__dict__.items())
        # warn_em.add_field(name='Command', value=f'`$dota stream add {cmd_str}`', inline=False)
        cmd_usage_str = f"name: {player_dict['display_name']} {self.cmd_usage_str(**account_dict)}"
        warn_e.add_field(name='Command', value=f'{self.game} player add {cmd_usage_str}')
        await self.bot.hideout.global_logs.send(embed=warn_e)

    async def database_remove(
        self,
        ntr: discord.Interaction[AluBot],
        name_lower: Optional[str],
        account_id: Optional[Union[str, int]],  # steam_id for dota, something else for lol
    ) -> None:
        """Base function for removing accounts from the database"""
        await ntr.response.defer()
        if name_lower is None and account_id is None:
            raise commands.BadArgument('You need to provide at least one of flags: `name`, `steam`')

        if account_id:
            if name_lower:  # check for both name_lower and account_id
                query = f"""SELECT a.id 
                            FROM {self.game}_players p
                            JOIN {self.game}_accounts a
                            ON p.id = a.player_id
                            WHERE a.id=$1 AND p.name_lower=$2
                        """
                val = await ntr.client.pool.fetchval(query, account_id, name_lower)
                if val is None:
                    raise commands.BadArgument(
                        'This account either is not in the database ' 'or does not belong to the said player'
                    )

            # query for account only
            query = f"""WITH del_child AS (
                            DELETE FROM {self.game}_accounts
                            WHERE  id = $1
                            RETURNING player_id, id
                            )
                        DELETE FROM {self.game}_players p
                        USING  del_child x
                        WHERE  p.id = x.player_id
                        AND    NOT EXISTS (
                            SELECT 1
                            FROM   {self.game}_accounts c
                            WHERE  c.player_id = x.player_id
                            AND    c.id <> x.id
                            )
                        RETURNING display_name
                    """
            ans_name = await ntr.client.pool.fetchval(query, account_id)
            if ans_name is None:
                raise commands.BadArgument('There is no account with such account details')
        else:
            # query for name_lower only
            query = f"""DELETE FROM {self.game}_players
                        WHERE name_lower=$1
                        RETURNING display_name
                    """
            ans_name = await ntr.client.pool.fetchval(query, name_lower)
            if ans_name is None:
                raise commands.BadArgument('There is no account with such player name')

        e = discord.Embed(colour=self.colour)
        msg = 'Successfully removed account(-s) from the database'
        e.add_field(name=msg, value=f'{ans_name}{" - " + str(account_id) if account_id else ""}')
        e.set_footer(text=self.game_mention, icon_url=self.game_icon)
        await ntr.followup.send(embed=e)

    @staticmethod
    def construct_the_embed(
        s_names: List[str], a_names: List[str], f_names: List[str], *, gather_word: str, mode_add: bool
    ) -> discord.Embed:
        e = discord.Embed()
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
    def get_names_list_from_locals(ntr: discord.Interaction[AluBot], local_dict: Dict[str, Any]) -> List[str]:
        names = list(dict.fromkeys([name for name in list(local_dict.values())[2:] if name is not None]))
        return names

    async def player_add_remove(
        self, ntr: discord.Interaction[AluBot], local_dict: Dict[str, Any], *, mode_add: bool
    ) -> None:
        """
        Base function to add/remove players from user's favourite list.

        Parameters
        ----------
        ctx :
        local_dict :
        mode_add :
        """
        await ntr.response.defer()
        assert ntr.guild

        player_names = self.get_names_list_from_locals(ntr, local_dict)

        if not player_names:
            raise commands.BadArgument("You cannot use this command without naming at least one player.")

        query = f'SELECT players FROM fpc WHERE guild_id=$1 AND game=$2'
        fav_ids: List[int] = await ntr.client.pool.fetchval(query, ntr.guild.id, self.game) or []  # type: ignore
        query = f"""SELECT id, name_lower, display_name 
                    FROM {self.game}_players
                    WHERE name_lower=ANY($1)
                """  # AND NOT id=ANY($2)
        sa_rows = await ntr.client.pool.fetch(query, [name.lower() for name in player_names])
        # The following notations are assumed logically for mode_add being `True`.
        # +-----------------+-----------------------+-----------------------+
        # | variable_name   | `mode_add = True`     | `mode_add = False`    |
        # +=================+=======================+=======================+
        # | s               | successfully added    | already removed       |
        # +-----------------+-----------------------+-----------------------+
        # | a               | already added         | successfully removed  |
        # +-----------------+-----------------------+-----------------------+
        # | f               | failed to add         | failed to remove      |
        # +-----------------+-----------------------+-----------------------+
        s_ids = [row.id for row in sa_rows if row.id not in fav_ids]
        s_names = [row.display_name for row in sa_rows if row.id not in fav_ids]
        a_ids = [row.id for row in sa_rows if row.id in fav_ids]
        a_names = [row.display_name for row in sa_rows if row.id in fav_ids]
        f_names = [name for name in player_names if name.lower() not in [row.name_lower for row in sa_rows]]

        query = f'''INSERT INTO fpc (game, guild_id)
                    VALUES ($1, $2)
                    ON CONFLICT (game, guild_id) DO UPDATE
                        SET players=$3;
                '''
        new_fav_ids = fav_ids + s_ids if mode_add else [i for i in fav_ids if i not in a_ids]
        await ntr.client.pool.execute(query, self.game, ntr.guild.id, new_fav_ids)

        if mode_add:
            e = self.construct_the_embed(s_names, a_names, f_names, gather_word='players', mode_add=mode_add)
        else:
            e = self.construct_the_embed(a_names, s_names, f_names, gather_word='players', mode_add=mode_add)
        if f_names:
            text = (
                'Check your argument or consider adding (for trustees)/requesting such player with '
                '`$ or /dota database add|request name: <name> steam: <steam_id> twitch: <yes/no>`'
            )
            e.set_footer(text=text)
        await ntr.followup.send(embed=e)

    async def player_add_remove_autocomplete(
        self, ntr: discord.Interaction, current: str, *, mode_add: bool
    ) -> List[app_commands.Choice[str]]:
        """Base function for player add/remove autocomplete"""
        assert ntr.guild

        query = f'SELECT players FROM fpc WHERE guild_id=$1 AND game=$2'
        fav_ids = await self.bot.pool.fetch(query, ntr.guild.id, self.game) or []
        clause = 'NOT' if mode_add else ''
        query = f"""SELECT display_name
                    FROM {self.game}_players
                    WHERE {clause} id=ANY($1)
                    ORDER BY similarity(display_name, $2) DESC
                    LIMIT 6;
                """
        rows = await self.bot.pool.fetch(query, fav_ids, current)
        namespace_list = [x.lower() for x in ntr.namespace.__dict__.values() if x != current]
        choice_list = [x for x in [a for a, in rows] if x.lower() not in namespace_list]
        return [app_commands.Choice(name=n, value=n) for n in choice_list if current.lower() in n.lower()]

    async def player_list(self, ntr: discord.Interaction[AluBot]):
        """Base function for player list command"""
        assert ntr.guild

        await ntr.response.defer()
        query = f'SELECT players FROM fpc WHERE guild_id=$1 AND game=$2'
        fav_ids = await self.bot.pool.fetchval(query, ntr.guild.id, self.game) or []

        query = f"""SELECT display_name, twitch_id 
                    FROM {self.game}_players
                    WHERE id=ANY($1)
                    ORDER BY display_name
                """
        rows = await self.bot.pool.fetch(query, fav_ids) or []

        player_names = [self.player_name_string(row.display_name, row.twitch_id) for row in rows]
        e = discord.Embed(title=f'List of favourite players', colour=self.colour)
        e.description = '\n'.join(player_names)
        e.set_footer(text=self.game_mention, icon_url=self.game_icon)
        await ntr.followup.send(embed=e)

    async def character_add_remove(
        self, ntr: discord.Interaction[AluBot], local_dict: Dict[str, Any], *, mode_add: bool
    ):
        """Base function for adding/removing characters such as heroes/champs from fav lists"""
        assert ntr.guild

        character_names = self.get_names_list_from_locals(ntr, local_dict)

        if not character_names:
            raise commands.BadArgument("You cannot use this command without naming at least one character.")

        await ntr.response.defer()

        query = f'SELECT characters FROM fpc WHERE guild_id=$1'
        fav_ids: List[int] = await ntr.client.pool.fetchval(query, ntr.guild.id) or []  # type: ignore

        f_names, sa_ids = [], []
        for name in character_names:
            try:
                sa_ids.append(await self.character_id_by_name(name))
            except KeyError:
                f_names.append(name)

        s_ids = [i for i in sa_ids if i not in fav_ids]
        a_ids = [i for i in sa_ids if i in fav_ids]
        s_names = [await self.character_name_by_id(i) for i in s_ids]
        a_names = [await self.character_name_by_id(i) for i in a_ids]

        query = f'''INSERT INTO fpc (game, guild_id)
                    VALUES ($1, $2)
                    ON CONFLICT (game, guild_id) DO UPDATE 
                        SET characters=$3;
                '''
        new_fav_ids = fav_ids + s_ids if mode_add else [i for i in fav_ids if i not in a_ids]
        await ntr.client.pool.execute(query, self.game, ntr.guild.id, new_fav_ids)

        if mode_add:
            e = self.construct_the_embed(
                s_names, a_names, f_names, gather_word=self.character_gather_word, mode_add=mode_add
            )
        else:
            e = self.construct_the_embed(
                a_names, s_names, f_names, gather_word=self.character_gather_word, mode_add=mode_add
            )
        await ntr.followup.send(embed=e)

    async def character_add_remove_autocomplete(
        self, ntr: discord.Interaction, current: str, *, mode_add: bool
    ) -> List[app_commands.Choice[str]]:
        """Base function for character add/remove autocomplete"""
        query = f'SELECT characters FROM fpc WHERE guild_id=$1'
        fav_ids: List[int] = await self.bot.pool.fetchval(query, ntr.guild.id) or []  # type:ignore

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
        return [app_commands.Choice(name=n, value=n) for n in return_list][:25]  # type: ignore

    async def character_list(self, ntr: discord.Interaction[AluBot]) -> None:
        """Base function for character list commands"""
        await ntr.response.defer()
        query = f'SELECT characters FROM fpc WHERE guild_id=$1 AND game=$2'
        fav_ids: List[int] = await ntr.client.pool.fetchval(query, ntr.guild.id, self.game) or []  # type: ignore
        fav_names = [f'{await self.character_name_by_id(i)} - `{i}`' for i in fav_ids]

        e = discord.Embed(title=f'List of your favourite {self.character_gather_word}', colour=self.colour)
        e.description = '\n'.join(fav_names)
        await ntr.followup.send(embed=e)

    async def spoil(self, ntr: discord.Interaction[AluBot], spoil: bool):
        """Base function for spoil commands"""
        assert ntr.guild

        query = f'''INSERT INTO fpc (game, guild_id)
                    VALUES ($1, $2)
                    ON CONFLICT (game, guild_id) DO UPDATE
                        SET spoil=$3;
                '''
        await self.bot.pool.execute(query, self.game, ntr.guild.id, spoil)
        e = discord.Embed(description=f"Changed spoil value to {spoil}", colour=self.colour)
        await ntr.response.send_message(embed=e)
