from utils.cache_my import KeyCache

from .const import *

__all__ = ('lazy_aghs_shard_url', 'lazy_aghs_bless_url', 'name_by_id', 'iconurl_by_id')

ATTR_BONUS_ICON = "https://static.wikia.nocookie.net/dota2_gamepedia/images/e/e2/Attribute_Bonus_icon.png"
TALENTS_ICON = "https://liquipedia.net/commons/images/5/54/Talents.png"

lazy_aghs_bless_url = f"{STEAM_CDN_URL}/apps/dota2/images/dota_react/items/ultimate_scepter_2.png"
lazy_aghs_shard_url = f"{STEAM_CDN_URL}/apps/dota2/images/dota_react/items/aghanims_shard.png"


class AbilityKeyCache(KeyCache):
    async def fill_data(self) -> dict:
        ab_ids_dict = await self.get_resp_json(url=f'{ODOTA_API_URL}/constants/ability_ids')
        abs_dict = await self.get_resp_json(url=f'{ODOTA_API_URL}/constants/abilities')
        hero_abs_dict = await self.get_resp_json(url=f'{ODOTA_API_URL}/constants/hero_abilities')

        revert_ab_ids_dict = {v: int(k) for k, v in ab_ids_dict.items()}

        data = {
            'iconurl_by_id': {0: DISCONNECT_ICON, 730: ATTR_BONUS_ICON},
            "name_by_id": {730: None},
        }
        for k, v in hero_abs_dict.items():
            for npc_name in v['abilities']:
                ability_id = revert_ab_ids_dict[npc_name]
                data['iconurl_by_id'][ability_id] = f"{STEAM_CDN_URL}{abs_dict[npc_name].get('img', None)}"
                data['name_by_id'][ability_id] = None
            for talent in v['talents']:
                npc_name = talent['name']
                ability_id = revert_ab_ids_dict.get(npc_name, None)
                if ability_id is None:
                    continue
                data['iconurl_by_id'][ability_id] = TALENTS_ICON
                data['name_by_id'][ability_id] = abs_dict[npc_name].get('dname', None)
        return data


ability_keys_cache = AbilityKeyCache()


async def iconurl_by_id(value: int) -> str:
    """Get ability icon url by id"""
    data = await ability_keys_cache.data
    return data['iconurl_by_id'].get(value, DISCONNECT_ICON)


async def name_by_id(value: int) -> str:
    """Get ability name by its id

    Currently only return data on talents and None for everything else,
    bcs we do not need anything else for now
    """
    data = await ability_keys_cache.data
    return data['name_by_id'].get(value, 'New Talent')
