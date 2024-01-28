from utils import AluCog, ExtCategory, const

category = ExtCategory(
    name='Image Tools',
    emote=const.Emote.KURU,
    description='Image Tools',
)


class ImageToolsCog(AluCog, category=category):
    ...
