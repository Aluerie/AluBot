from utils import AluCog, ExtCategory, const

category = ExtCategory(
    name='FPC Notifications',
    emote=const.Emote.KURU,
    description='FPC (Favourite Player+Character) Notifications.',
)


class FPCCog(AluCog, category=category):
    ...
