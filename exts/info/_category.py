from utils import AluCog, ExtCategory, const

category = ExtCategory(
    name='Information',
    emote=const.Emote.KURU,
    description='Information',
)


class InfoCog(AluCog, category=category):
    ...
