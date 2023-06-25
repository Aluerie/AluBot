from utils import AluCog, ExtCategory, const

category = ExtCategory(
    name='Aluerie\'s Community',
    emote=const.Emote.peepoComfy,
    description='Features that only available in the community server.',
    sort_back=True
)


class CommunityCog(AluCog, category=category):
    ...
