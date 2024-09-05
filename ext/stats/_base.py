from bot import AluCog, ExtCategory
from utils.const import Emote

category = ExtCategory(
    name="Statistics",
    emote=Emote.Jebaited,
    description="Some statistics that bot gathered/can gather.",
)


class StatsCog(AluCog, category=category):
    ...
