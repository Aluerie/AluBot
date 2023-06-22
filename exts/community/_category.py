from utils import AluCog, ExtCategory, const

category = ExtCategory(
    name='Aluerie\'s Community',
    emote=const.Emote.peepoComfy,
    description='Community',
    sort_back=True
)


class CommunityCog(AluCog, category=category):
    ...
