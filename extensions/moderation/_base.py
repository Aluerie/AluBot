from utils import AluCog, ExtCategory, const

category = ExtCategory(
    name='Moderation',
    emote=const.Emote.peepoPolice,
    description='Moderation tools',
)


class ModerationCog(AluCog, category=category):
    ...
