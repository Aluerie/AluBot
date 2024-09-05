from bot import AluCog, ExtCategory
from utils.const import Emote

category = ExtCategory(
    name="Server Config",
    emote=Emote.peepoBusiness,
    description="Server Config",
)


class ConfigGuildCog(AluCog, category=category):
    ...
