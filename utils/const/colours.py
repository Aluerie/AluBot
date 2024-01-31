from __future__ import annotations

from typing import TYPE_CHECKING, Literal

import discord

if TYPE_CHECKING:
    pass

__all__ = (
    "Colour",
    "MaterialPalette",
    "MaterialAccentPalette",
)

# fmt: off
class Colour:
    """My chosen colours"""

    # names are lower-case because "Color Highlight" VSCode extension doesn't highlight words in any other case
    # blueviolet - BlueViolet - blue_violet - blueViolet - BLUEVIOLET - BLUE_VIOLET ;
    # that extension uses colour names from https://www.w3.org/TR/css-color-4/#valdef-color-indigo or something
    # so when introducing new common colours - use something from there

    # my colour is Lavender Purple (Purple Mountain Majesty)
    # https://en.wikipedia.org/wiki/Lavender_(color)#Lavender_purple_(purple_mountain_majesty)
    # but I just chose the name that is supported by the said extension in highlight and is close enough in value.
    blueviolet    = 0x9678B6 # dota fpc
    
    palevioletred = 0xDB7093 # lol fpc
    maroon        = 0x800000  # errors
    
    slateblue     = 0x6A5ACD
    darkviolet    = 0x9400D3

    # other known colours
    twitch = 0x9146FF

    # raspberry = 0xC42C48
    # neon = 0x4D4DFF
# fmt: on


# fmt: off
material_palette_dict_colours = {
    # shade value |   900   |   800   |   700   |   600   |   500   |   400   |   300   |   200   |   100   |    50    |     
    'red':         [0xB71C1C, 0xC62828, 0xD32F2F, 0xE53935, 0xF44336, 0xEF5350, 0xE57373, 0xEF9A9A, 0xFFCDD2, 0xFFEBEE],
    'pink':        [0x880E4F, 0xAD1457, 0xC2185B, 0xD81B60, 0xE91E63, 0xEC407A, 0xF06292, 0xF48FB1, 0xF8BBD0, 0xFCE4EC],
    'purple':      [0x4A148C, 0x6A1B9A, 0x7B1FA2, 0x8E24AA, 0x9C27B0, 0xAB47BC, 0xBA68C8, 0xCE93D8, 0xE1BEE7, 0xF3E5F5],
    'deep_purple': [0x311B92, 0x4527A0, 0x512DA8, 0x5E35B1, 0x673AB7, 0x7E57C2, 0x9575CD, 0xB39DDB, 0xD1C4E9, 0xEDE7F6],
    'indigo':      [0x1A237E, 0x283593, 0x303F9F, 0x3949AB, 0x3F51B5, 0x5C6BC0, 0x7986CB, 0x9FA8DA, 0xC5CAE9, 0xE8EAF6],
    'blue':        [0x0D47A1, 0x1565C0, 0x1976D2, 0x1E88E5, 0x2196F3, 0x42A5F5, 0x64B5F6, 0x90CAF9, 0xBBDEFB, 0xE3F2FD],
    'light_blue':  [0x01579B, 0x0277BD, 0x0288D1, 0x039BE5, 0x03A9F4, 0x29B6F6, 0x4FC3F7, 0x81D4FA, 0xB3E5FC, 0xE1F5FE],
    'cyan':        [0x006064, 0x00838F, 0x0097A7, 0x00ACC1, 0x00BCD4, 0x26C6DA, 0x4DD0E1, 0x80DEEA, 0xB2EBF2, 0xE0F7FA],
    'teal':        [0x004D40, 0x00695C, 0x00796B, 0x00897B, 0x009688, 0x26A69A, 0x4DB6AC, 0x80CBC4, 0xB2DFDB, 0xE0F2F1],
    'green':       [0x1B5E20, 0x2E7D32, 0x388E3C, 0x43A047, 0x4CAF50, 0x66BB6A, 0x81C784, 0xA5D6A7, 0xC8E6C9, 0xE8F5E9],
    'light_green': [0x33691E, 0x558B2F, 0x689F38, 0x7CB342, 0x8BC34A, 0x9CCC65, 0xAED581, 0xC5E1A5, 0xDCEDC8, 0xF1F8E9],
    'lime':        [0x827717, 0x9E9D24, 0xAFB42B, 0xC0CA33, 0xCDDC39, 0xD4E157, 0xDCE775, 0xE6EE9C, 0xF0F4C3, 0xF9FBE7],
    'yellow':      [0xF57F17, 0xF9A825, 0xFBC02D, 0xFDD835, 0xFFEB3B, 0xFFEE58, 0xFFF176, 0xFFF59D, 0xFFF9C4, 0xFFFDE7],
    'amber':       [0xFF6F00, 0xFF8F00, 0xFFA000, 0xFFB300, 0xFFC107, 0xFFCA28, 0xFFD54F, 0xFFE082, 0xFFECB3, 0xFFF8E1],
    'orange':      [0xE65100, 0xEF6C00, 0xF57C00, 0xFB8C00, 0xFF9800, 0xFFA726, 0xFFB74D, 0xFFCC80, 0xFFE0B2, 0xFFF3E0],
    'deep_orange': [0xBF360C, 0xD84315, 0xE64A19, 0xF4511E, 0xFF5722, 0xFF7043, 0xFF8A65, 0xFFAB91, 0xFFCCBC, 0xFBE9E7],
    'brown':       [0x3E2723, 0x4E342E, 0x5D4037, 0x6D4C41, 0x795548, 0x8D6E63, 0xA1887F, 0xBCAAA4, 0xD7CCC8, 0xEFEBE9],
    'gray':        [0x212121, 0x424242, 0x616161, 0x757575, 0x9E9E9E, 0xBDBDBD, 0xE0E0E0, 0xEEEEEE, 0xF5F5F5, 0xFAFAFA],
    'blue_gray':   [0x263238, 0x37474F, 0x455A64, 0x546E7A, 0x607D8B, 0x78909C, 0x90A4AE, 0xB0BEC5, 0xCFD8DC, 0xECEFF1],
    'black':       [0x000000, 0x000000, 0x000000, 0x000000, 0x000000, 0x000000, 0x000000, 0x000000, 0x000000, 0x000000],
    'white':       [0xFFFFFF, 0xFFFFFF, 0xFFFFFF, 0xFFFFFF, 0xFFFFFF, 0xFFFFFF, 0xFFFFFF, 0xFFFFFF, 0xFFFFFF, 0xFFFFFF],
}
# fmt: on

mp_shades = [900, 800, 700, 600, 500, 400, 300, 200, 100, 50]

material_palette = {
    colour: {shade: hex_value for shade, hex_value in zip(mp_shades, hex_values)}
    for colour, hex_values in material_palette_dict_colours.items()
}


class MaterialPalette:
    """Material Design Color Palette

    https://m2.material.io/design/color/the-color-system.html#tools-for-picking-colors
    """

    if TYPE_CHECKING:
        ShadeLiteral = Literal[900, 800, 700, 600, 500, 400, 300, 200, 100, 50]

    shades = mp_shades

    @staticmethod
    def red(shade: ShadeLiteral = 500) -> discord.Colour:
        return discord.Colour(material_palette["red"][shade])

    @staticmethod
    def pink(shade: ShadeLiteral = 500) -> discord.Colour:
        return discord.Colour(material_palette["pink"][shade])

    @staticmethod
    def purple(shade: ShadeLiteral = 500) -> discord.Colour:
        return discord.Colour(material_palette["purple"][shade])

    @staticmethod
    def deep_purple(shade: ShadeLiteral = 500) -> discord.Colour:
        return discord.Colour(material_palette["deep_purple"][shade])

    @staticmethod
    def indigo(shade: ShadeLiteral = 500) -> discord.Colour:
        return discord.Colour(material_palette["indigo"][shade])

    @staticmethod
    def blue(shade: ShadeLiteral = 500) -> discord.Colour:
        return discord.Colour(material_palette["blue"][shade])

    @staticmethod
    def light_blue(shade: ShadeLiteral = 500) -> discord.Colour:
        return discord.Colour(material_palette["light_blue"][shade])

    @staticmethod
    def cyan(shade: ShadeLiteral = 500) -> discord.Colour:
        return discord.Colour(material_palette["cyan"][shade])

    @staticmethod
    def teal(shade: ShadeLiteral = 500) -> discord.Colour:
        return discord.Colour(material_palette["teal"][shade])

    @staticmethod
    def green(shade: ShadeLiteral = 500) -> discord.Colour:
        return discord.Colour(material_palette["green"][shade])

    @staticmethod
    def light_green(shade: ShadeLiteral = 500) -> discord.Colour:
        return discord.Colour(material_palette["light_green"][shade])

    @staticmethod
    def lime(shade: ShadeLiteral = 500) -> discord.Colour:
        return discord.Colour(material_palette["lime"][shade])

    @staticmethod
    def yellow(shade: ShadeLiteral = 500) -> discord.Colour:
        return discord.Colour(material_palette["yellow"][shade])

    @staticmethod
    def amber(shade: ShadeLiteral = 500) -> discord.Colour:
        return discord.Colour(material_palette["amber"][shade])

    @staticmethod
    def orange(shade: ShadeLiteral = 500) -> discord.Colour:
        return discord.Colour(material_palette["orange"][shade])

    @staticmethod
    def deep_orange(shade: ShadeLiteral = 500) -> discord.Colour:
        return discord.Colour(material_palette["deep_orange"][shade])

    @staticmethod
    def brown(shade: ShadeLiteral = 500) -> discord.Colour:
        return discord.Colour(material_palette["brown"][shade])

    @staticmethod
    def gray(shade: ShadeLiteral = 500) -> discord.Colour:
        return discord.Colour(material_palette["gray"][shade])

    @staticmethod
    def blue_gray(shade: ShadeLiteral = 500) -> discord.Colour:
        return discord.Colour(material_palette["blue_gray"][shade])

    @staticmethod
    def black(shade: ShadeLiteral = 500) -> discord.Colour:
        return discord.Colour(material_palette["black"][shade])

    @staticmethod
    def white(shade: ShadeLiteral = 500) -> discord.Colour:
        return discord.Colour(material_palette["white"][shade])


# fmt: off
material_accent_palette_dict_colours = {
    'red':         [0xD50000, 0xFF1744, 0xFF5252, 0xFF8A80],
    'pink':        [0xC51162, 0xF50057, 0xFF4081, 0xFF80AB],
    'purple':      [0xAA00FF, 0xD500F9, 0xE040FB, 0xEA80FC],
    'deep_purple': [0x6200EA, 0x651FFF, 0x7C4DFF, 0xB388FF],
    'indigo':      [0x304FFE, 0x3D5AFE, 0x536DFE, 0x8C9EFF],
    'blue':        [0x2962FF, 0x2979FF, 0x448AFF, 0x82B1FF],
    'light_blue':  [0x0091EA, 0x00B0FF, 0x40C4FF, 0x80D8FF],
    'cyan':        [0x00B8D4, 0x00E5FF, 0x18FFFF, 0x84FFFF],
    'teal':        [0x00BFA5, 0x1DE9B6, 0x64FFDA, 0xA7FFEB],
    'green':       [0x00C853, 0x00E676, 0x69F0AE, 0xB9F6CA],
    'light_green': [0x64DD17, 0x76FF03, 0xB2FF59, 0xCCFF90],
    'lime':        [0xAEEA00, 0xC6FF00, 0xEEFF41, 0xF4FF81],
    'yellow':      [0xFFD600, 0xFFEA00, 0xFFFF00, 0xFFFF8D],
    'amber':       [0xFFAB00, 0xFFC400, 0xFFD740, 0xFFE57F],
    'orange':      [0xFF6D00, 0xFF9100, 0xFFAB40, 0xFFD180],
    'deep_orange': [0xDD2C00, 0xFF3D00, 0xFF6E40, 0xFF9E80],
    # brown, gray, blue_gray, black, white - these colours do not have Accent versions
}
# fmt: on

map_shades = [700, 400, 200, 100]

material_accent_palette = {
    colour: {shade: hex_value for shade, hex_value in zip(map_shades, hex_values)}
    for colour, hex_values in material_palette_dict_colours.items()
}


class MaterialAccentPalette:
    """Material Design Color Palette with Accent Designs

    https://m2.material.io/design/color/the-color-system.html#tools-for-picking-colors
    """

    if TYPE_CHECKING:
        AccentShadeLiteral = Literal[700, 400, 200, 100]

    shades = map_shades

    @staticmethod
    def red(shade: AccentShadeLiteral = 200) -> discord.Colour:
        return discord.Colour(material_palette["red"][shade])

    @staticmethod
    def pink(shade: AccentShadeLiteral = 200) -> discord.Colour:
        return discord.Colour(material_palette["pink"][shade])

    @staticmethod
    def purple(shade: AccentShadeLiteral = 200) -> discord.Colour:
        return discord.Colour(material_palette["purple"][shade])

    @staticmethod
    def deep_purple(shade: AccentShadeLiteral = 200) -> discord.Colour:
        return discord.Colour(material_palette["deep_purple"][shade])

    @staticmethod
    def indigo(shade: AccentShadeLiteral = 200) -> discord.Colour:
        return discord.Colour(material_palette["indigo"][shade])

    @staticmethod
    def blue(shade: AccentShadeLiteral = 200) -> discord.Colour:
        return discord.Colour(material_palette["blue"][shade])

    @staticmethod
    def light_blue(shade: AccentShadeLiteral = 200) -> discord.Colour:
        return discord.Colour(material_palette["light_blue"][shade])

    @staticmethod
    def cyan(shade: AccentShadeLiteral = 200) -> discord.Colour:
        return discord.Colour(material_palette["cyan"][shade])

    @staticmethod
    def teal(shade: AccentShadeLiteral = 200) -> discord.Colour:
        return discord.Colour(material_palette["teal"][shade])

    @staticmethod
    def green(shade: AccentShadeLiteral = 200) -> discord.Colour:
        return discord.Colour(material_palette["green"][shade])

    @staticmethod
    def light_green(shade: AccentShadeLiteral = 200) -> discord.Colour:
        return discord.Colour(material_palette["light_green"][shade])

    @staticmethod
    def lime(shade: AccentShadeLiteral = 200) -> discord.Colour:
        return discord.Colour(material_palette["lime"][shade])

    @staticmethod
    def yellow(shade: AccentShadeLiteral = 200) -> discord.Colour:
        return discord.Colour(material_palette["yellow"][shade])

    @staticmethod
    def amber(shade: AccentShadeLiteral = 200) -> discord.Colour:
        return discord.Colour(material_palette["amber"][shade])

    @staticmethod
    def orange(shade: AccentShadeLiteral = 200) -> discord.Colour:
        return discord.Colour(material_palette["orange"][shade])

    @staticmethod
    def deep_orange(shade: AccentShadeLiteral = 200) -> discord.Colour:
        return discord.Colour(material_palette["deep_orange"][shade])


if __name__ == "__main__":
    from PIL import Image

    x = MaterialPalette.purple()
    x = 0xDB7093

    rectangle = Image.new("RGB", (600, 300), f"#{x:0>6x}")
    rectangle.show()
