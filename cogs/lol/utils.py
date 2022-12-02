from pyot.models import lol
from pyot.utils.lol import champion, cdragon
from roleidentification import get_roles, pull_data


async def icon_url_by_champ_id(champ_id: int) -> str:
    """Get champion icon url by their champ_id """
    champ = await lol.champion.Champion(id=champ_id).get()
    return cdragon.abs_url(champ.square_path)


async def get_diff_list(champ_roles):
    data = await champion.champion_keys_cache.data
    return set(data['id_by_name'].values()) - set(champ_roles.keys())


async def get_champion_roles():
    """
    Unfortunately, Meraki run out of money to support their Json
    Thus sometimes it is behind a few patches ans
    I need to add new champions myself with this function.

    About Manual adding part:
    For Example, as in 12.13 patch - Nilah is not in Meraki Json
    Thus I can add it myself with the data from League of Graphs
    https://www.leagueofgraphs.com/champions/stats/nilah/master
    and it here for more precise data rather than 0.2 in all roles
    """
    champion_roles = pull_data()
    diff_list = await get_diff_list(champion_roles)

    manual_data = {
        895: {  # Nilah (data was taken 16/07/2022)
            'TOP': 9.0 * 0.043,
            'JUNGLE': 9.0 * 0.035,
            'MIDDLE': 9.0 * 0.058,
            'BOTTOM': 9.0 * 0.861,
            'UTILITY': 9.0 * 0.004  # global playrate in % * champ role appearance in decimal
        },
    }

    champion_roles = manual_data | champion_roles

    diff_dict = {
        x: {
            'TOP': 10 * 0.2,
            'JUNGLE': 10 * 0.2,
            'MIDDLE': 10 * 0.2,
            'BOTTOM': 10 * 0.2,
            'UTILITY': 10 * 0.2
        }
        for x in diff_list if x not in manual_data
    }
    return diff_dict | champion_roles


async def get_role_mini_list(all_players_champ_ids):
    champion_roles = await get_champion_roles()
    role_mini_list = \
        list(get_roles(champion_roles, all_players_champ_ids[:5]).values()) + \
        list(get_roles(champion_roles, all_players_champ_ids[5:]).values())
    return role_mini_list


async def lol_main():
    blue_team = [895, 200, 888, 238, 92]  # ['Nilah', 'BelVeth', 'Renata', '', 'Zed', 'Riven']
    red_team = [122, 69, 64, 201, 119]  # ['Darius', 'Cassiopeia', 'Lee Sin', 'Braum', 'Draven']

    sorted_champ_ids = await get_role_mini_list(blue_team + red_team)

    print([await champion.name_by_id(i) for i in sorted_champ_ids[:5]])
    print([await champion.name_by_id(i) for i in sorted_champ_ids[5:]])


if __name__ == '__main__':
    import asyncio
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)
    loop.run_until_complete(lol_main())
