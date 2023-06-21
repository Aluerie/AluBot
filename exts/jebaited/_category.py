from utils import AluCog, ExtCategory, const

category = ExtCategory(
    name='Jebaited',
    emote=const.Emote.KURU,
    description='Jebaited',
)


class JebaitedCog(AluCog):
    def __init__(self, bot):
        super().__init__(bot, category=category)
