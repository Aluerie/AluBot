from utils import AluCog, ExtCategory, const

category = ExtCategory(
    name='About',
    emote=const.Emote.KURU,
    description='Meta info',
)


class MetaCog(AluCog, category=category):
    ...
