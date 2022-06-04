from roleidentification import get_roles, pull_data

from discord import Embed
from discord.abc import Messageable
from pyot.utils.lol import champion
from utils.var import Uid, Clr
from utils.distools import umntn
# if they again run into no money issue then we should but new champions into dict below
# just copypaste playrates data from page like https://www.leagueofgraphs.com/champions/stats/zeri/master

extra_data = {
    888: {  # Renata (currently gets overwritren bcs they updated the table to 12.7 patch 21/04/22)
        'TOP': 0.0,  # but still it is a nice example of what to do if things break
        'JUNGLE': 0.0,
        'MIDDLE': 0.0,
        'BOTTOM': 12.2 * 0.001,
        'UTILITY': 12.2 * 0.999  # global playrate * champ role apperance
    },
}

champion_roles = extra_data | pull_data()


async def get_role_mini_list(session, all_players_champ_ids, destination: Messageable):
    try:
        role_mini_list = \
            list(get_roles(champion_roles, all_players_champ_ids[:5]).values()) + \
            list(get_roles(champion_roles, all_players_champ_ids[5:]).values())
        return role_mini_list
    except KeyError as e:
        # notify irene that there is some champ who isn't in meraki json
        champ_id = e.args[0]
        try:
            champ_name = await champion.key_by_id(champ_id)
        except KeyError:
            champ_name = 'Unknown by Pyot'
        embed = Embed(colour=Clr.prpl, title='Meraki Json problem')
        url_json = 'http://cdn.merakianalytics.com/riot/lol/resources/latest/en-US/championrates.json'
        async with session.get(url_json) as resp:
            json_dict = await resp.json()

        embed.description = \
            f'It seems like **{champ_name}** with id `{champ_id}` is missing from Meraki json\n ' \
            f'Meraki json was last updated on patch {json_dict["patch"]}\n' \
            f'• [Link to GitHub](https://github.com/meraki-analytics/role-identification)\n' \
            f'• [Link to Json](http://cdn.merakianalytics.com/riot/lol/resources/latest/en-US/championrates.json)'
        await destination.send(content=umntn(Uid.alu), embed=embed)
        return all_players_champ_ids
