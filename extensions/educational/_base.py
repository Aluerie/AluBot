from utils import AluCog, ExtCategory, const

category = ExtCategory(
    name='Educational features',
    emote=const.Emote.PepoG,
    description='Let us learn together.',
)


class EducationalCog(AluCog, category=category):
    ...
