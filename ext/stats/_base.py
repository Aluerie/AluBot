from utils import AluCog, ExtCategory, const

category = ExtCategory(
    name='Statistics',
    emote=const.Emote.Jebaited,
    description='Some statistics that bot gathered/can gather.',
)


class StatsCog(AluCog, category=category):
    ...
