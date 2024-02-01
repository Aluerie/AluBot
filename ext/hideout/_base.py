from utils import AluCog, ExtCategory, const

category = ExtCategory(
    name="Hideout",
    emote=const.Emote.KURU,
    description="Hideout trash",
)


class HideoutCog(AluCog, category=category):
    ...
