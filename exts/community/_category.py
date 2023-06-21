from utils import AluCog, ExtCategory, const

category = ExtCategory(
    name='Aluerie\'s Community',
    emote=const.Emote.peepoComfy,
    description='Community',
)


class CommunityCog(AluCog):
    def __init__(self, bot):
        super().__init__(bot, category=category)
