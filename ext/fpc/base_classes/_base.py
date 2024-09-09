from bot import AluCog, ExtCategory
from utils.const import Emote

__all__ = ("FPCCog",)


class FPCCog(
    AluCog,
    category=ExtCategory(
        name="FPC Notifications",
        emote=Emote.KURU,
        description="FPC (Favourite Player+Character) Notifications.",
    ),
):
    ...
