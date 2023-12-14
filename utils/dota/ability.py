from utils.cache import KeysCache

from ..const import DOTA

__all__ = (
    "lazy_aghs_shard_url",
    "lazy_aghs_bless_url",
    "name_by_id",
    "icon_url_by_id",
)

ATTR_BONUS_ICON = "https://static.wikia.nocookie.net/dota2_gamepedia/images/e/e2/Attribute_Bonus_icon.png"


lazy_aghs_bless_url = (
    f"https://cdn.cloudflare.steamstatic.com/apps/dota2/images/dota_react/items/ultimate_scepter_2.png"
)
lazy_aghs_shard_url = f"https://cdn.cloudflare.steamstatic.com/apps/dota2/images/dota_react/items/aghanims_shard.png"


class AbilityKeyCache(KeysCache):
    TALENT_ICON = "https://liquipedia.net/commons/images/5/54/Talents.png"

    async def fill_data(self) -> dict:
        ability_ids = await self.get_response_json("https://api.opendota.com/api/constants/ability_ids")
        reverse_ability_ids = {v: int(k) for k, v in ability_ids.items()}
        abilities = await self.get_response_json("https://api.opendota.com/api/constants/abilities")
        hero_abilities = await self.get_response_json("https://api.opendota.com/api/constants/hero_abilities")

        data = {
            "icon_url_by_id": {
                0: DOTA.HERO_DISCONNECT,
                730: ATTR_BONUS_ICON,
            },
            "name_by_id": {
                730: None,
            },
        }
        for hero_ability in hero_abilities.values():
            # fill ability icons related data
            for ability_name in hero_ability["abilities"]:
                ability_id = reverse_ability_ids[ability_name]

                img_url = abilities[ability_name].get("img", None)
                if img_url:
                    data["icon_url_by_id"][ability_id] = f"https://cdn.cloudflare.steamstatic.com{img_url}"
                else:
                    # todo: check if this ever proc
                    data["icon_url_by_id"][ability_id] = DOTA.HERO_DISCONNECT

            for talent in hero_ability["talents"]:
                talent_name = talent["name"]
                ability_id = reverse_ability_ids.get(talent_name, None)
                if ability_id is None:
                    continue
                data["icon_url_by_id"][ability_id] = self.TALENT_ICON
                data["name_by_id"][ability_id] = abilities[talent_name].get("dname", None)
        return data


ability_keys_cache = AbilityKeyCache()


async def icon_url_by_id(value: int) -> str:
    """Get ability icon url by id"""
    return await ability_keys_cache.get("icon_url_by_id", value, DOTA.HERO_DISCONNECT)


async def name_by_id(value: int) -> str:
    """Get ability name by its id

    Currently only return data on talents and None for everything else,
    bcs we do not need anything else for now
    """
    return await ability_keys_cache.get("name_by_id", value, "Unknown Talent Name")
