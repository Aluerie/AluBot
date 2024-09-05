from bot import AluCog, ExtCategory
from utils.const import Emote

category = ExtCategory(
    name="Server Settings",
    emote=Emote.KURU,
    description="Server Settings",
)


class GuildSettingsCog(AluCog, category=category):
    ...
