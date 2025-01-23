from __future__ import annotations

from typing import Literal

import discord

__all__ = (
    "Accent",
    "Colour",
    "Material",
    "MaterialAccentPalette",
    "MaterialPalette",
)


class Colour:
    """My chosen colours."""

    # names are lower-case because "Color Highlight" VSCode extension doesn't highlight words in any other case
    # blueviolet - BlueViolet - blue_violet - blueViolet - BLUEVIOLET - BLUE_VIOLET ;
    # that extension uses colour names from https://www.w3.org/TR/css-color-4/#valdef-color-indigo or something
    # so when introducing new common colours - use something from there

    # my colour is Lavender Purple (Purple Mountain Majesty)
    # https://en.wikipedia.org/wiki/Lavender_(color)#Lavender_purple_(purple_mountain_majesty)
    # but I just chose the name that is supported by the said extension in highlight and is close enough in value.
    blueviolet = 0x9678B6  # dota fpc

    darkslategray = 0x2F4F4F  # lol fpc
    maroon = 0x800000  # errors

    slateblue = 0x6A5ACD
    darkviolet = 0x9400D3
    # TODO: add all colours from link above

    # other known colours
    twitch = 0x9146FF

    # raspberry = 0xC42C48
    # neon = 0x4D4DFF


def material_worker(
    colour_hexes: list[int],
    shade: Literal[900, 800, 700, 600, 500, 400, 300, 200, 100, 50],
) -> discord.Colour:
    """Boilerplate function to get the colour for Material Palette class."""
    return discord.Colour(colour_hexes[9 - shade // 100])


class MaterialPalette:
    """Material Design Color Palette.

    https://m2.material.io/design/color/the-color-system.html#tools-for-picking-colors
    """

    # Static methods in this class define `shades` list of colour hexes integers which
    # correspond to the following list of integer shades:
    # [900, 800, 700, 600, 500, 400, 300, 200, 100, 50]
    # which is converted to real index in material_worker function

    shades = (900, 800, 700, 600, 500, 400, 300, 200, 100, 50)

    @staticmethod
    def red(shade: Literal[900, 800, 700, 600, 500, 400, 300, 200, 100, 50] = 500) -> discord.Colour:
        """Get shade of red colour from Google Material Design."""
        shades = [0xB71C1C, 0xC62828, 0xD32F2F, 0xE53935, 0xF44336, 0xEF5350, 0xE57373, 0xEF9A9A, 0xFFCDD2, 0xFFEBEE]
        return material_worker(shades, shade)

    @staticmethod
    def pink(shade: Literal[900, 800, 700, 600, 500, 400, 300, 200, 100, 50] = 500) -> discord.Colour:
        """Get shade of pink colour from Google Material Design."""
        shades = [0x880E4F, 0xAD1457, 0xC2185B, 0xD81B60, 0xE91E63, 0xEC407A, 0xF06292, 0xF48FB1, 0xF8BBD0, 0xFCE4EC]
        return material_worker(shades, shade)

    @staticmethod
    def purple(shade: Literal[900, 800, 700, 600, 500, 400, 300, 200, 100, 50] = 500) -> discord.Colour:
        """Get shade of purple colour from Google Material Design."""
        shades = [0x4A148C, 0x6A1B9A, 0x7B1FA2, 0x8E24AA, 0x9C27B0, 0xAB47BC, 0xBA68C8, 0xCE93D8, 0xE1BEE7, 0xF3E5F5]
        return material_worker(shades, shade)

    @staticmethod
    def deep_purple(shade: Literal[900, 800, 700, 600, 500, 400, 300, 200, 100, 50] = 500) -> discord.Colour:
        """Get shade of deep purple colour from Google Material Design."""
        shades = [0x311B92, 0x4527A0, 0x512DA8, 0x5E35B1, 0x673AB7, 0x7E57C2, 0x9575CD, 0xB39DDB, 0xD1C4E9, 0xEDE7F6]
        return material_worker(shades, shade)

    @staticmethod
    def indigo(shade: Literal[900, 800, 700, 600, 500, 400, 300, 200, 100, 50] = 500) -> discord.Colour:
        """Get shade of deep indigo colour from Google Material Design."""
        shades = [0x1A237E, 0x283593, 0x303F9F, 0x3949AB, 0x3F51B5, 0x5C6BC0, 0x7986CB, 0x9FA8DA, 0xC5CAE9, 0xE8EAF6]
        return material_worker(shades, shade)

    @staticmethod
    def blue(shade: Literal[900, 800, 700, 600, 500, 400, 300, 200, 100, 50] = 500) -> discord.Colour:
        """Get shade of blue colour from Google Material Design."""
        shades = [0x0D47A1, 0x1565C0, 0x1976D2, 0x1E88E5, 0x2196F3, 0x42A5F5, 0x64B5F6, 0x90CAF9, 0xBBDEFB, 0xE3F2FD]
        return material_worker(shades, shade)

    @staticmethod
    def light_blue(shade: Literal[900, 800, 700, 600, 500, 400, 300, 200, 100, 50] = 500) -> discord.Colour:
        """Get shade of light blue colour from Google Material Design."""
        shades = [0x01579B, 0x0277BD, 0x0288D1, 0x039BE5, 0x03A9F4, 0x29B6F6, 0x4FC3F7, 0x81D4FA, 0xB3E5FC, 0xE1F5FE]
        return material_worker(shades, shade)

    @staticmethod
    def cyan(shade: Literal[900, 800, 700, 600, 500, 400, 300, 200, 100, 50] = 500) -> discord.Colour:
        """Get shade of cyan colour from Google Material Design."""
        shades = [0x006064, 0x00838F, 0x0097A7, 0x00ACC1, 0x00BCD4, 0x26C6DA, 0x4DD0E1, 0x80DEEA, 0xB2EBF2, 0xE0F7FA]
        return material_worker(shades, shade)

    @staticmethod
    def teal(shade: Literal[900, 800, 700, 600, 500, 400, 300, 200, 100, 50] = 500) -> discord.Colour:
        """Get shade of teal colour from Google Material Design."""
        shades = [0x004D40, 0x00695C, 0x00796B, 0x00897B, 0x009688, 0x26A69A, 0x4DB6AC, 0x80CBC4, 0xB2DFDB, 0xE0F2F1]
        return material_worker(shades, shade)

    @staticmethod
    def green(shade: Literal[900, 800, 700, 600, 500, 400, 300, 200, 100, 50] = 500) -> discord.Colour:
        """Get shade of green colour from Google Material Design."""
        shades = [0x1B5E20, 0x2E7D32, 0x388E3C, 0x43A047, 0x4CAF50, 0x66BB6A, 0x81C784, 0xA5D6A7, 0xC8E6C9, 0xE8F5E9]
        return material_worker(shades, shade)

    @staticmethod
    def light_green(shade: Literal[900, 800, 700, 600, 500, 400, 300, 200, 100, 50] = 500) -> discord.Colour:
        """Get shade of light green colour from Google Material Design."""
        shades = [0x33691E, 0x558B2F, 0x689F38, 0x7CB342, 0x8BC34A, 0x9CCC65, 0xAED581, 0xC5E1A5, 0xDCEDC8, 0xF1F8E9]
        return material_worker(shades, shade)

    @staticmethod
    def lime(shade: Literal[900, 800, 700, 600, 500, 400, 300, 200, 100, 50] = 500) -> discord.Colour:
        """Get shade of lime colour from Google Material Design."""
        shades = [0x827717, 0x9E9D24, 0xAFB42B, 0xC0CA33, 0xCDDC39, 0xD4E157, 0xDCE775, 0xE6EE9C, 0xF0F4C3, 0xF9FBE7]
        return material_worker(shades, shade)

    @staticmethod
    def yellow(shade: Literal[900, 800, 700, 600, 500, 400, 300, 200, 100, 50] = 500) -> discord.Colour:
        """Get shade of yellow colour from Google Material Design."""
        shades = [0xF57F17, 0xF9A825, 0xFBC02D, 0xFDD835, 0xFFEB3B, 0xFFEE58, 0xFFF176, 0xFFF59D, 0xFFF9C4, 0xFFFDE7]
        return material_worker(shades, shade)

    @staticmethod
    def amber(shade: Literal[900, 800, 700, 600, 500, 400, 300, 200, 100, 50] = 500) -> discord.Colour:
        """Get shade of amber colour from Google Material Design."""
        shades = [0xFF6F00, 0xFF8F00, 0xFFA000, 0xFFB300, 0xFFC107, 0xFFCA28, 0xFFD54F, 0xFFE082, 0xFFECB3, 0xFFF8E1]
        return material_worker(shades, shade)

    @staticmethod
    def orange(shade: Literal[900, 800, 700, 600, 500, 400, 300, 200, 100, 50] = 500) -> discord.Colour:
        """Get shade of orange colour from Google Material Design."""
        shades = [0xE65100, 0xEF6C00, 0xF57C00, 0xFB8C00, 0xFF9800, 0xFFA726, 0xFFB74D, 0xFFCC80, 0xFFE0B2, 0xFFF3E0]
        return material_worker(shades, shade)

    @staticmethod
    def deep_orange(shade: Literal[900, 800, 700, 600, 500, 400, 300, 200, 100, 50] = 500) -> discord.Colour:
        """Get shade of deep orange colour from Google Material Design."""
        shades = [0xBF360C, 0xD84315, 0xE64A19, 0xF4511E, 0xFF5722, 0xFF7043, 0xFF8A65, 0xFFAB91, 0xFFCCBC, 0xFBE9E7]
        return material_worker(shades, shade)

    @staticmethod
    def brown(shade: Literal[900, 800, 700, 600, 500, 400, 300, 200, 100, 50] = 500) -> discord.Colour:
        """Get shade of brown colour from Google Material Design."""
        shades = [0x3E2723, 0x4E342E, 0x5D4037, 0x6D4C41, 0x795548, 0x8D6E63, 0xA1887F, 0xBCAAA4, 0xD7CCC8, 0xEFEBE9]
        return material_worker(shades, shade)

    @staticmethod
    def gray(shade: Literal[900, 800, 700, 600, 500, 400, 300, 200, 100, 50] = 500) -> discord.Colour:
        """Get shade of gray colour from Google Material Design."""
        shades = [0x212121, 0x424242, 0x616161, 0x757575, 0x9E9E9E, 0xBDBDBD, 0xE0E0E0, 0xEEEEEE, 0xF5F5F5, 0xFAFAFA]
        return material_worker(shades, shade)

    @staticmethod
    def blue_gray(shade: Literal[900, 800, 700, 600, 500, 400, 300, 200, 100, 50] = 500) -> discord.Colour:
        """Get shade of blue gray colour from Google Material Design."""
        shades = [0x263238, 0x37474F, 0x455A64, 0x546E7A, 0x607D8B, 0x78909C, 0x90A4AE, 0xB0BEC5, 0xCFD8DC, 0xECEFF1]
        return material_worker(shades, shade)

    @staticmethod
    def black(shade: Literal[900, 800, 700, 600, 500, 400, 300, 200, 100, 50] = 500) -> discord.Colour:
        """Get shade of black colour from Google Material Design."""
        shades = [0x000000, 0x000000, 0x000000, 0x000000, 0x000000, 0x000000, 0x000000, 0x000000, 0x000000, 0x000000]
        return material_worker(shades, shade)

    @staticmethod
    def white(shade: Literal[900, 800, 700, 600, 500, 400, 300, 200, 100, 50] = 500) -> discord.Colour:
        """Get shade of white colour from Google Material Design."""
        shades = [0xFFFFFF, 0xFFFFFF, 0xFFFFFF, 0xFFFFFF, 0xFFFFFF, 0xFFFFFF, 0xFFFFFF, 0xFFFFFF, 0xFFFFFF, 0xFFFFFF]
        return material_worker(shades, shade)


def accent_worker(colour_hexes: list[int], shade: Literal[700, 400, 200, 100]) -> discord.Colour:
    """Boilerplate function to get the colour for Material Accent Palette class."""
    return discord.Colour(colour_hexes[3 - shade // 200])


class MaterialAccentPalette:
    """Material Design Color Palette with Accent Designs.

    https://m2.material.io/design/color/the-color-system.html#tools-for-picking-colors
    """

    # Static methods in this class define `shades` list of colour hexes integers which
    # correspond to the following list of integer shades:
    # [700, 400, 200, 100]
    # which is converted to real index in material_worker function

    shades = (700, 400, 200, 100)

    @staticmethod
    def red(shade: Literal[700, 400, 200, 100] = 200) -> discord.Colour:
        """Get shade of red colour from Google Material Accent Design."""
        shades = [0xD50000, 0xFF1744, 0xFF5252, 0xFF8A80]
        return accent_worker(shades, shade)

    @staticmethod
    def pink(shade: Literal[700, 400, 200, 100] = 200) -> discord.Colour:
        """Get shade of pink colour from Google Material Accent Design."""
        shades = [0xC51162, 0xF50057, 0xFF4081, 0xFF80AB]
        return accent_worker(shades, shade)

    @staticmethod
    def purple(shade: Literal[700, 400, 200, 100] = 200) -> discord.Colour:
        """Get shade of purple colour from Google Material Accent Design."""
        shades = [0xAA00FF, 0xD500F9, 0xE040FB, 0xEA80FC]
        return accent_worker(shades, shade)

    @staticmethod
    def deep_purple(shade: Literal[700, 400, 200, 100] = 200) -> discord.Colour:
        """Get shade of deep purple colour from Google Material Accent Design."""
        shades = [0x6200EA, 0x651FFF, 0x7C4DFF, 0xB388FF]
        return accent_worker(shades, shade)

    @staticmethod
    def indigo(shade: Literal[700, 400, 200, 100] = 200) -> discord.Colour:
        """Get shade of indigo colour from Google Material Accent Design."""
        shades = [0x304FFE, 0x3D5AFE, 0x536DFE, 0x8C9EFF]
        return accent_worker(shades, shade)

    @staticmethod
    def blue(shade: Literal[700, 400, 200, 100] = 200) -> discord.Colour:
        """Get shade of blue colour from Google Material Accent Design."""
        shades = [0x2962FF, 0x2979FF, 0x448AFF, 0x82B1FF]
        return accent_worker(shades, shade)

    @staticmethod
    def light_blue(shade: Literal[700, 400, 200, 100] = 200) -> discord.Colour:
        """Get shade of light blue colour from Google Material Accent Design."""
        shades = [0x0091EA, 0x00B0FF, 0x40C4FF, 0x80D8FF]
        return accent_worker(shades, shade)

    @staticmethod
    def cyan(shade: Literal[700, 400, 200, 100] = 200) -> discord.Colour:
        """Get shade of cyan colour from Google Material Accent Design."""
        shades = [0x00B8D4, 0x00E5FF, 0x18FFFF, 0x84FFFF]
        return accent_worker(shades, shade)

    @staticmethod
    def teal(shade: Literal[700, 400, 200, 100] = 200) -> discord.Colour:
        """Get shade of teal colour from Google Material Accent Design."""
        shades = [0x00BFA5, 0x1DE9B6, 0x64FFDA, 0xA7FFEB]
        return accent_worker(shades, shade)

    @staticmethod
    def green(shade: Literal[700, 400, 200, 100] = 200) -> discord.Colour:
        """Get shade of green colour from Google Material Accent Design."""
        shades = [0x00C853, 0x00E676, 0x69F0AE, 0xB9F6CA]
        return accent_worker(shades, shade)

    @staticmethod
    def light_green(shade: Literal[700, 400, 200, 100] = 200) -> discord.Colour:
        """Get shade of light green colour from Google Material Accent Design."""
        shades = [0x64DD17, 0x76FF03, 0xB2FF59, 0xCCFF90]
        return accent_worker(shades, shade)

    @staticmethod
    def lime(shade: Literal[700, 400, 200, 100] = 200) -> discord.Colour:
        """Get shade of lime colour from Google Material Accent Design."""
        shades = [0xAEEA00, 0xC6FF00, 0xEEFF41, 0xF4FF81]
        return accent_worker(shades, shade)

    @staticmethod
    def yellow(shade: Literal[700, 400, 200, 100] = 200) -> discord.Colour:
        """Get shade of yellow colour from Google Material Accent Design."""
        shades = [0xFFD600, 0xFFEA00, 0xFFFF00, 0xFFFF8D]
        return accent_worker(shades, shade)

    @staticmethod
    def amber(shade: Literal[700, 400, 200, 100] = 200) -> discord.Colour:
        """Get shade of amber colour from Google Material Accent Design."""
        shades = [0xFFAB00, 0xFFC400, 0xFFD740, 0xFFE57F]
        return accent_worker(shades, shade)

    @staticmethod
    def orange(shade: Literal[700, 400, 200, 100] = 200) -> discord.Colour:
        """Get shade of orange colour from Google Material Accent Design."""
        shades = [0xFF6D00, 0xFF9100, 0xFFAB40, 0xFFD180]
        return accent_worker(shades, shade)

    @staticmethod
    def deep_orange(shade: Literal[700, 400, 200, 100] = 200) -> discord.Colour:
        """Get shade of deep orange colour from Google Material Accent Design."""
        shades = [0xDD2C00, 0xFF3D00, 0xFF6E40, 0xFF9E80]
        return accent_worker(shades, shade)

    # PS. brown, gray, blue_gray, black, white - these colours do not have Accent versions


# ALIASES
Material = MaterialPalette
Accent = MaterialAccentPalette


if __name__ == "__main__":
    from PIL import Image

    x = MaterialPalette.purple()
    x = 0xDB7093

    rectangle = Image.new("RGB", (600, 300), f"#{x:0>6x}")
    rectangle.show()
