from utils import AluCog, ExtCategory, const

__all__ = ("FPCCog",)


class FPCCog(
    AluCog,
    category=ExtCategory(
        name="FPC Notifications",
        emote=const.Emote.KURU,
        description="FPC (Favourite Player+Character) Notifications.",
    ),
):
    ...
