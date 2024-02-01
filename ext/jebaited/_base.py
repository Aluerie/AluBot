from utils import AluCog, ExtCategory, const

category = ExtCategory(
    name="Jebaited",
    emote=const.Emote.Jebaited,
    description="These features are coming \N{TRADE MARK SIGN}\N{VARIATION SELECTOR-16} soon, for sure.",
)


class JebaitedCog(AluCog, category=category):
    ...
