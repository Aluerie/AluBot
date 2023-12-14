BASE_URL = "https://raw.communitydragon.org/latest/plugins/rcp-be-lol-game-data/global/default/"


def cdragon_asset_url(path: str) -> str:
    """Return the CDragon url for the given game asset path"""
    path = path.lower()
    splitted = path.split("/lol-game-data/assets/")
    if len(splitted) == 2:
        return BASE_URL + splitted[1]
    return BASE_URL + path
