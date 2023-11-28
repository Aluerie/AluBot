from utils import AluCog, ExtCategory, const

category = ExtCategory(
    name="Cog",
    emote=const.Emote.DankHatTooBig,  # TODO: change emote
    description="Cog description.",
)


class BaseCog(AluCog, category=category):
    ...
