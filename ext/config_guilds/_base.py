from utils import AluCog, ExtCategory, const

category = ExtCategory(
    name="Server Config",
    emote=const.Emote.peepoBusiness,
    description="Server Config",
)


class ConfigGuildCog(AluCog, category=category):
    ...
