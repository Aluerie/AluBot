from bot import AluCog, ExtCategory
from utils import const

category = ExtCategory(
    name="Cog",
    emote=const.Emote.DankHatTooBig,  # TODO: change emote
    description="Cog description.",
)


class BaseCog(AluCog, category=category):
    ...
