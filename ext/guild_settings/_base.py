from utils import AluCog, ExtCategory, const

category = ExtCategory(
    name="Server Settings",
    emote=const.Emote.KURU,
    description="Server Settings",
)


class GuildSettingsCog(AluCog, category=category):
    ...
