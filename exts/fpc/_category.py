from utils import AluCog, ExtCategory, const

category = ExtCategory(
    name='FPC',
    emote=const.Emote.KURU,
    description='Notifs about streamers picking your fav characters',
)


class FPCCog(AluCog):
    def __init__(self, bot):
        super().__init__(bot, category=category)
