from __future__ import annotations

from typing import Literal

import discord

__all__ = (
    "Accent",
    "Colour",
    "Palette",
)


class Colour:
    """My chosen colours.

    Names usually reflect where the colour is chosen to be used.

    Notes
    -----
    * "Colour Highlight" VSCode extension uses colours from https://www.w3.org/TR/css-color-4/#valdef-color-indigo
    * It only works for lowercase though: blueviolet - BlueViolet - blue_violet - blueViolet - BLUEVIOLET - BLUE_VIOLET
    * Either way, if we want some fancy highlighting of words: we can grab colours from there.
        But usually writing `Colour.error` is more meaningful than `Colour.marron`

    """

    prpl = 0x9678B6
    """Main colour in the bot, pretty much used everywhere.

    https://en.wikipedia.org/wiki/Lavender_(color)#Lavender_purple_(purple_mountain_majesty)
    Examples of usage: Dota 2 FPC.
    """
    league = 0x2F4F4F
    """League of Legends green colour that is somewhat average of most of its client's interface and icon colours."""
    error = 0x800000
    """Colour for errors."""
    twitch = 0x9146FF
    """Twitch.tv Brand Colour."""


class Palette:
    """Material Design Color Palette.

    https://m2.material.io/design/color/the-color-system.html#tools-for-picking-colors
    """

    @staticmethod
    def red(shade: Literal[900, 800, 700, 600, 500, 400, 300, 200, 100, 50] = 500) -> discord.Colour:
        """Get shade of red colour from Google Material Design."""
        shades = {
            900: 0xB71C1C,
            800: 0xC62828,
            700: 0xD32F2F,
            600: 0xE53935,
            500: 0xF44336,
            400: 0xEF5350,
            300: 0xE57373,
            200: 0xEF9A9A,
            100: 0xFFCDD2,
            50: 0xFFEBEE,
        }
        return discord.Colour(shades[shade])

    @staticmethod
    def pink(shade: Literal[900, 800, 700, 600, 500, 400, 300, 200, 100, 50] = 500) -> discord.Colour:
        """Get shade of pink colour from Google Material Design."""
        shades = {
            900: 0x880E4F,
            800: 0xAD1457,
            700: 0xC2185B,
            600: 0xD81B60,
            500: 0xE91E63,
            400: 0xEC407A,
            300: 0xF06292,
            200: 0xF48FB1,
            100: 0xF8BBD0,
            50: 0xFCE4EC,
        }
        return discord.Colour(shades[shade])

    @staticmethod
    def purple(shade: Literal[900, 800, 700, 600, 500, 400, 300, 200, 100, 50] = 500) -> discord.Colour:
        """Get shade of purple colour from Google Material Design."""
        shades = {
            900: 0x4A148C,
            800: 0x6A1B9A,
            700: 0x7B1FA2,
            600: 0x8E24AA,
            500: 0x9C27B0,
            400: 0xAB47BC,
            300: 0xBA68C8,
            200: 0xCE93D8,
            100: 0xE1BEE7,
            50: 0xF3E5F5,
        }
        return discord.Colour(shades[shade])

    @staticmethod
    def deep_purple(shade: Literal[900, 800, 700, 600, 500, 400, 300, 200, 100, 50] = 500) -> discord.Colour:
        """Get shade of deep purple colour from Google Material Design."""
        shades = {
            900: 0x311B92,
            800: 0x4527A0,
            700: 0x512DA8,
            600: 0x5E35B1,
            500: 0x673AB7,
            400: 0x7E57C2,
            300: 0x9575CD,
            200: 0xB39DDB,
            100: 0xD1C4E9,
            50: 0xEDE7F6,
        }
        return discord.Colour(shades[shade])

    @staticmethod
    def indigo(shade: Literal[900, 800, 700, 600, 500, 400, 300, 200, 100, 50] = 500) -> discord.Colour:
        """Get shade of deep indigo colour from Google Material Design."""
        shades = {
            900: 0x1A237E,
            800: 0x283593,
            700: 0x303F9F,
            600: 0x3949AB,
            500: 0x3F51B5,
            400: 0x5C6BC0,
            300: 0x7986CB,
            200: 0x9FA8DA,
            100: 0xC5CAE9,
            50: 0xE8EAF6,
        }
        return discord.Colour(shades[shade])

    @staticmethod
    def blue(shade: Literal[900, 800, 700, 600, 500, 400, 300, 200, 100, 50] = 500) -> discord.Colour:
        """Get shade of blue colour from Google Material Design."""
        shades = {
            900: 0x0D47A1,
            800: 0x1565C0,
            700: 0x1976D2,
            600: 0x1E88E5,
            500: 0x2196F3,
            400: 0x42A5F5,
            300: 0x64B5F6,
            200: 0x90CAF9,
            100: 0xBBDEFB,
            50: 0xE3F2FD,
        }
        return discord.Colour(shades[shade])

    @staticmethod
    def light_blue(shade: Literal[900, 800, 700, 600, 500, 400, 300, 200, 100, 50] = 500) -> discord.Colour:
        """Get shade of light blue colour from Google Material Design."""
        shades = {
            900: 0x01579B,
            800: 0x0277BD,
            700: 0x0288D1,
            600: 0x039BE5,
            500: 0x03A9F4,
            400: 0x29B6F6,
            300: 0x4FC3F7,
            200: 0x81D4FA,
            100: 0xB3E5FC,
            50: 0xE1F5FE,
        }
        return discord.Colour(shades[shade])

    @staticmethod
    def cyan(shade: Literal[900, 800, 700, 600, 500, 400, 300, 200, 100, 50] = 500) -> discord.Colour:
        """Get shade of cyan colour from Google Material Design."""
        shades = {
            900: 0x006064,
            800: 0x00838F,
            700: 0x0097A7,
            600: 0x00ACC1,
            500: 0x00BCD4,
            400: 0x26C6DA,
            300: 0x4DD0E1,
            200: 0x80DEEA,
            100: 0xB2EBF2,
            50: 0xE0F7FA,
        }
        return discord.Colour(shades[shade])

    @staticmethod
    def teal(shade: Literal[900, 800, 700, 600, 500, 400, 300, 200, 100, 50] = 500) -> discord.Colour:
        """Get shade of teal colour from Google Material Design."""
        shades = {
            900: 0x004D40,
            800: 0x00695C,
            700: 0x00796B,
            600: 0x00897B,
            500: 0x009688,
            400: 0x26A69A,
            300: 0x4DB6AC,
            200: 0x80CBC4,
            100: 0xB2DFDB,
            50: 0xE0F2F1,
        }
        return discord.Colour(shades[shade])

    @staticmethod
    def green(shade: Literal[900, 800, 700, 600, 500, 400, 300, 200, 100, 50] = 500) -> discord.Colour:
        """Get shade of green colour from Google Material Design."""
        shades = {
            900: 0x1B5E20,
            800: 0x2E7D32,
            700: 0x388E3C,
            600: 0x43A047,
            500: 0x4CAF50,
            400: 0x66BB6A,
            300: 0x81C784,
            200: 0xA5D6A7,
            100: 0xC8E6C9,
            50: 0xE8F5E9,
        }
        return discord.Colour(shades[shade])

    @staticmethod
    def light_green(shade: Literal[900, 800, 700, 600, 500, 400, 300, 200, 100, 50] = 500) -> discord.Colour:
        """Get shade of light green colour from Google Material Design."""
        shades = {
            900: 0x33691E,
            800: 0x558B2F,
            700: 0x689F38,
            600: 0x7CB342,
            500: 0x8BC34A,
            400: 0x9CCC65,
            300: 0xAED581,
            200: 0xC5E1A5,
            100: 0xDCEDC8,
            50: 0xF1F8E9,
        }
        return discord.Colour(shades[shade])

    @staticmethod
    def lime(shade: Literal[900, 800, 700, 600, 500, 400, 300, 200, 100, 50] = 500) -> discord.Colour:
        """Get shade of lime colour from Google Material Design."""
        shades = {
            900: 0x827717,
            800: 0x9E9D24,
            700: 0xAFB42B,
            600: 0xC0CA33,
            500: 0xCDDC39,
            400: 0xD4E157,
            300: 0xDCE775,
            200: 0xE6EE9C,
            100: 0xF0F4C3,
            50: 0xF9FBE7,
        }
        return discord.Colour(shades[shade])

    @staticmethod
    def yellow(shade: Literal[900, 800, 700, 600, 500, 400, 300, 200, 100, 50] = 500) -> discord.Colour:
        """Get shade of yellow colour from Google Material Design."""
        shades = {
            900: 0xF57F17,
            800: 0xF9A825,
            700: 0xFBC02D,
            600: 0xFDD835,
            500: 0xFFEB3B,
            400: 0xFFEE58,
            300: 0xFFF176,
            200: 0xFFF59D,
            100: 0xFFF9C4,
            50: 0xFFFDE7,
        }
        return discord.Colour(shades[shade])

    @staticmethod
    def amber(shade: Literal[900, 800, 700, 600, 500, 400, 300, 200, 100, 50] = 500) -> discord.Colour:
        """Get shade of amber colour from Google Material Design."""
        shades = {
            900: 0xFF6F00,
            800: 0xFF8F00,
            700: 0xFFA000,
            600: 0xFFB300,
            500: 0xFFC107,
            400: 0xFFCA28,
            300: 0xFFD54F,
            200: 0xFFE082,
            100: 0xFFECB3,
            50: 0xFFF8E1,
        }
        return discord.Colour(shades[shade])

    @staticmethod
    def orange(shade: Literal[900, 800, 700, 600, 500, 400, 300, 200, 100, 50] = 500) -> discord.Colour:
        """Get shade of orange colour from Google Material Design."""
        shades = {
            900: 0xE65100,
            800: 0xEF6C00,
            700: 0xF57C00,
            600: 0xFB8C00,
            500: 0xFF9800,
            400: 0xFFA726,
            300: 0xFFB74D,
            200: 0xFFCC80,
            100: 0xFFE0B2,
            50: 0xFFF3E0,
        }
        return discord.Colour(shades[shade])

    @staticmethod
    def deep_orange(shade: Literal[900, 800, 700, 600, 500, 400, 300, 200, 100, 50] = 500) -> discord.Colour:
        """Get shade of deep orange colour from Google Material Design."""
        shades = {
            900: 0xBF360C,
            800: 0xD84315,
            700: 0xE64A19,
            600: 0xF4511E,
            500: 0xFF5722,
            400: 0xFF7043,
            300: 0xFF8A65,
            200: 0xFFAB91,
            100: 0xFFCCBC,
            50: 0xFBE9E7,
        }
        return discord.Colour(shades[shade])

    @staticmethod
    def brown(shade: Literal[900, 800, 700, 600, 500, 400, 300, 200, 100, 50] = 500) -> discord.Colour:
        """Get shade of brown colour from Google Material Design."""
        shades = {
            900: 0x3E2723,
            800: 0x4E342E,
            700: 0x5D4037,
            600: 0x6D4C41,
            500: 0x795548,
            400: 0x8D6E63,
            300: 0xA1887F,
            200: 0xBCAAA4,
            100: 0xD7CCC8,
            50: 0xEFEBE9,
        }
        return discord.Colour(shades[shade])

    @staticmethod
    def gray(shade: Literal[900, 800, 700, 600, 500, 400, 300, 200, 100, 50] = 500) -> discord.Colour:
        """Get shade of gray colour from Google Material Design."""
        shades = {
            900: 0x212121,
            800: 0x424242,
            700: 0x616161,
            600: 0x757575,
            500: 0x9E9E9E,
            400: 0xBDBDBD,
            300: 0xE0E0E0,
            200: 0xEEEEEE,
            100: 0xF5F5F5,
            50: 0xFAFAFA,
        }
        return discord.Colour(shades[shade])

    @staticmethod
    def blue_gray(shade: Literal[900, 800, 700, 600, 500, 400, 300, 200, 100, 50] = 500) -> discord.Colour:
        """Get shade of blue gray colour from Google Material Design."""
        shades = {
            900: 0x263238,
            800: 0x37474F,
            700: 0x455A64,
            600: 0x546E7A,
            500: 0x607D8B,
            400: 0x78909C,
            300: 0x90A4AE,
            200: 0xB0BEC5,
            100: 0xCFD8DC,
            50: 0xECEFF1,
        }
        return discord.Colour(shades[shade])

    @staticmethod
    def black(shade: Literal[900, 800, 700, 600, 500, 400, 300, 200, 100, 50] = 500) -> discord.Colour:
        """Get shade of black colour from Google Material Design."""
        return discord.Colour(0x000000)  # yes shade doesn't matter

    @staticmethod
    def white(shade: Literal[900, 800, 700, 600, 500, 400, 300, 200, 100, 50] = 500) -> discord.Colour:
        """Get shade of white colour from Google Material Design."""
        return discord.Colour(0xFFFFFF)  # yes shade doesn't matter


class Accent:
    """Material Design Color Palette with Accent Designs.

    https://m2.material.io/design/color/the-color-system.html#tools-for-picking-colors
    """

    @staticmethod
    def red(shade: Literal[700, 400, 200, 100] = 200) -> discord.Colour:
        """Get shade of red colour from Google Material Accent Design."""
        shades = {
            700: 0xD50000,
            400: 0xFF1744,
            200: 0xFF5252,
            100: 0xFF8A80,
        }
        return discord.Colour(shades[shade])

    @staticmethod
    def pink(shade: Literal[700, 400, 200, 100] = 200) -> discord.Colour:
        """Get shade of pink colour from Google Material Accent Design."""
        shades = {
            700: 0xC51162,
            400: 0xF50057,
            200: 0xFF4081,
            100: 0xFF80AB,
        }
        return discord.Colour(shades[shade])

    @staticmethod
    def purple(shade: Literal[700, 400, 200, 100] = 200) -> discord.Colour:
        """Get shade of purple colour from Google Material Accent Design."""
        shades = {
            700: 0xAA00FF,
            400: 0xD500F9,
            200: 0xE040FB,
            100: 0xEA80FC,
        }
        return discord.Colour(shades[shade])

    @staticmethod
    def deep_purple(shade: Literal[700, 400, 200, 100] = 200) -> discord.Colour:
        """Get shade of deep purple colour from Google Material Accent Design."""
        shades = {
            700: 0x6200EA,
            400: 0x651FFF,
            200: 0x7C4DFF,
            100: 0xB388FF,
        }
        return discord.Colour(shades[shade])

    @staticmethod
    def indigo(shade: Literal[700, 400, 200, 100] = 200) -> discord.Colour:
        """Get shade of indigo colour from Google Material Accent Design."""
        shades = {
            700: 0x304FFE,
            400: 0x3D5AFE,
            200: 0x536DFE,
            100: 0x8C9EFF,
        }
        return discord.Colour(shades[shade])

    @staticmethod
    def blue(shade: Literal[700, 400, 200, 100] = 200) -> discord.Colour:
        """Get shade of blue colour from Google Material Accent Design."""
        shades = {
            700: 0x2962FF,
            400: 0x2979FF,
            200: 0x448AFF,
            100: 0x82B1FF,
        }
        return discord.Colour(shades[shade])

    @staticmethod
    def light_blue(shade: Literal[700, 400, 200, 100] = 200) -> discord.Colour:
        """Get shade of light blue colour from Google Material Accent Design."""
        shades = {
            700: 0x0091EA,
            400: 0x00B0FF,
            200: 0x40C4FF,
            100: 0x80D8FF,
        }
        return discord.Colour(shades[shade])

    @staticmethod
    def cyan(shade: Literal[700, 400, 200, 100] = 200) -> discord.Colour:
        """Get shade of cyan colour from Google Material Accent Design."""
        shades = {
            700: 0x00B8D4,
            400: 0x00E5FF,
            200: 0x18FFFF,
            100: 0x84FFFF,
        }
        return discord.Colour(shades[shade])

    @staticmethod
    def teal(shade: Literal[700, 400, 200, 100] = 200) -> discord.Colour:
        """Get shade of teal colour from Google Material Accent Design."""
        shades = {
            700: 0x00BFA5,
            400: 0x1DE9B6,
            200: 0x64FFDA,
            100: 0xA7FFEB,
        }
        return discord.Colour(shades[shade])

    @staticmethod
    def green(shade: Literal[700, 400, 200, 100] = 200) -> discord.Colour:
        """Get shade of green colour from Google Material Accent Design."""
        shades = {
            700: 0x00C853,
            400: 0x00E676,
            200: 0x69F0AE,
            100: 0xB9F6CA,
        }
        return discord.Colour(shades[shade])

    @staticmethod
    def light_green(shade: Literal[700, 400, 200, 100] = 200) -> discord.Colour:
        """Get shade of light green colour from Google Material Accent Design."""
        shades = {
            700: 0x64DD17,
            400: 0x76FF03,
            200: 0xB2FF59,
            100: 0xCCFF90,
        }
        return discord.Colour(shades[shade])

    @staticmethod
    def lime(shade: Literal[700, 400, 200, 100] = 200) -> discord.Colour:
        """Get shade of lime colour from Google Material Accent Design."""
        shades = {
            700: 0xAEEA00,
            400: 0xC6FF00,
            200: 0xEEFF41,
            100: 0xF4FF81,
        }
        return discord.Colour(shades[shade])

    @staticmethod
    def yellow(shade: Literal[700, 400, 200, 100] = 200) -> discord.Colour:
        """Get shade of yellow colour from Google Material Accent Design."""
        shades = {
            700: 0xFFD600,
            400: 0xFFEA00,
            200: 0xFFFF00,
            100: 0xFFFF8D,
        }
        return discord.Colour(shades[shade])

    @staticmethod
    def amber(shade: Literal[700, 400, 200, 100] = 200) -> discord.Colour:
        """Get shade of amber colour from Google Material Accent Design."""
        shades = {
            700: 0xFFAB00,
            400: 0xFFC400,
            200: 0xFFD740,
            100: 0xFFE57F,
        }
        return discord.Colour(shades[shade])

    @staticmethod
    def orange(shade: Literal[700, 400, 200, 100] = 200) -> discord.Colour:
        """Get shade of orange colour from Google Material Accent Design."""
        shades = {
            700: 0xFF6D00,
            400: 0xFF9100,
            200: 0xFFAB40,
            100: 0xFFD180,
        }
        return discord.Colour(shades[shade])

    @staticmethod
    def deep_orange(shade: Literal[700, 400, 200, 100] = 200) -> discord.Colour:
        """Get shade of deep orange colour from Google Material Accent Design."""
        shades = {
            700: 0xDD2C00,
            400: 0xFF3D00,
            200: 0xFF6E40,
            100: 0xFF9E80,
        }
        return discord.Colour(shades[shade])

    # PS. brown, gray, blue_gray, black, white - these colours do not have Accent versions


if __name__ == "__main__":
    from PIL import Image

    x = Palette.purple()
    x = 0xDB7093

    rectangle = Image.new("RGB", (600, 300), f"#{x:0>6x}")
    rectangle.show()
