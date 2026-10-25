"""Const.

Notices
-------
* MPL-2.0 License, see LICENSE file for more details.
* Copyright (C) 2020-present @Aluerie.
"""
# ruff: file-ignore[mixed-case-variable-in-class-scope]

from enum import UNIQUE, Enum, IntEnum, auto, verify
from typing import TYPE_CHECKING, override

import discord

if TYPE_CHECKING:
    from core import Bot


class Guild(IntEnum):
    """Discord guild ids."""

    community = 702561315478044804
    hideout = 759916212842659850


########################################################################################################################
# EMOJIS
########################################################################################################################


_RESOLVED_EMOTES: dict[str, str] = {}


class Emoji(Enum):
    """Application Emojis.

    Names must match the names in both bots' (production and test version) Developer Portals.
    """

    # Logos
    Discord = auto()
    GitHub = auto()

    # Non-animated Dank Emojis
    bubuGun = auto()
    DankApprove = auto()
    DankHey = auto()
    DankLove = auto()
    hu = auto()
    peepoComfy = auto()
    peepoNiceDay = auto()
    peepoPolice = auto()
    peepoRoseDank = auto()
    PepoDetective = auto()
    PepoG = auto()

    # Animated
    SmogeInTheRain = auto()

    @override
    def __str__(self) -> str:
        try:
            return _RESOLVED_EMOTES[self.name]
        except KeyError:
            msg = f"Emojis not loaded yet (tried accessing {self.name!r} before load_emojis)"
            raise RuntimeError(msg) from None


async def load_emojis(bot: Bot) -> None:
    """Fetch the bot's Application Emojis and make them available to `Emoji` enum.

    Must be awaited once (e.g. in `setup_hook`) before any `Emoji` member is converted to a string, since the markdown
    strings depend on which bot account (test or production) is logged in.

    Parameters
    ----------
    bot
        The bot whose Application Emojis are fetched.

    Raises
    ------
    RuntimeError
        If any `Emoji` member has no Application Emoji of the same name on this bot.
    """
    _RESOLVED_EMOTES.update({e.name: str(e) for e in await bot.fetch_application_emojis()})
    if missing := {e.name for e in Emoji} - _RESOLVED_EMOTES.keys():
        msg = f"Application emojis missing on this bot: {sorted(missing)}"
        raise RuntimeError(msg)


########################################################################################################################
# MENTIONABLE IDS
########################################################################################################################


class ChannelId(int):
    __slots__ = ()

    @property
    def mention(self) -> str:
        return f"<#{self}>"

    @property
    def object(self) -> discord.Object:
        return discord.Object(self, type=discord.abc.GuildChannel)  # ty: ignore[invalid-argument-type]


class RoleId(int):
    __slots__ = ()

    @property
    def mention(self) -> str:
        return f"<@&{self}>"

    @property
    def object(self) -> discord.Object:
        return discord.Object(self, type=discord.Role)


class UserId(int):
    __slots__ = ()

    @property
    def mention(self) -> str:
        return f"<@{self}>"

    @property
    def object(self) -> discord.Object:
        return discord.Object(self, type=discord.abc.User)


########################################################################################################################
# COLORS
########################################################################################################################


__all__ = (
    "Accent",
    "Color",
    "Palette",
)


# class Color:
#     """My chosen colors.

#     Names usually reflect where the color is chosen to be used.

#     Notes
#     -----
#     * "Color Highlight" VSCode extension uses colors from https://www.w3.org/TR/css-color-4/#valdef-color-indigo
#     * It only works for lowercase though: blueviolet - BlueViolet - blue_violet - blueViolet - BLUEVIOLET - BLUE_VIOLET
#     * Either way, if we want some fancy highlighting of words: we can grab colors from there.
#         But usually writing `Color.error` is more meaningful than `Color.marron`

#     """

#     prpl = 0x9678B6
#     """Main color in the bot, pretty much used everywhere.

#     https://en.wikipedia.org/wiki/Lavender_(color)#Lavender_purple_(purple_mountain_majesty)
#     Examples of usage: Dota 2 FPC.
#     """
#     league = 0x2F4F4F
#     """League of Legends green color that is somewhat average of most of its client's interface and icon colors."""
#     error = 0x800000
#     """Color for errors."""
#     twitch = 0x9146FF
#     """Twitch.tv Brand Color."""


@verify(UNIQUE)
class Palette(IntEnum):
    """Material Design Color Palette.

    https://m2.material.io/design/color/the-color-system.html#tools-for-picking-colors

    Members are `int`s because `discord.Embed.from_dict` only accepts `int` for its "color" field.
    """

    red_900 = 0xB71C1C
    red_800 = 0xC62828
    red_700 = 0xD32F2F
    red_600 = 0xE53935
    red_500 = 0xF44336
    red_400 = 0xEF5350
    red_300 = 0xE57373
    red_200 = 0xEF9A9A
    red_100 = 0xFFCDD2
    red_50 = 0xFFEBEE

    pink_900 = 0x880E4F
    pink_800 = 0xAD1457
    pink_700 = 0xC2185B
    pink_600 = 0xD81B60
    pink_500 = 0xE91E63
    pink_400 = 0xEC407A
    pink_300 = 0xF06292
    pink_200 = 0xF48FB1
    pink_100 = 0xF8BBD0
    pink_50 = 0xFCE4EC

    purple_900 = 0x4A148C
    purple_800 = 0x6A1B9A
    purple_700 = 0x7B1FA2
    purple_600 = 0x8E24AA
    purple_500 = 0x9C27B0
    purple_400 = 0xAB47BC
    purple_300 = 0xBA68C8
    purple_200 = 0xCE93D8
    purple_100 = 0xE1BEE7
    purple_50 = 0xF3E5F5

    deep_purple_900 = 0x311B92
    deep_purple_800 = 0x4527A0
    deep_purple_700 = 0x512DA8
    deep_purple_600 = 0x5E35B1
    deep_purple_500 = 0x673AB7
    deep_purple_400 = 0x7E57C2
    deep_purple_300 = 0x9575CD
    deep_purple_200 = 0xB39DDB
    deep_purple_100 = 0xD1C4E9
    deep_purple_50 = 0xEDE7F6

    @staticmethod
    def indigo(shade: Literal[900, 800, 700, 600, 500, 400, 300, 200, 100, 50] = 500) -> int:
        """Get shade of deep indigo color from Google Material Design."""
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
        return shades[shade]

    @staticmethod
    def blue(shade: Literal[900, 800, 700, 600, 500, 400, 300, 200, 100, 50] = 500) -> int:
        """Get shade of blue color from Google Material Design."""
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
        return shades[shade]

    @staticmethod
    def light_blue(shade: Literal[900, 800, 700, 600, 500, 400, 300, 200, 100, 50] = 500) -> int:
        """Get shade of light blue color from Google Material Design."""
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
        return shades[shade]

    @staticmethod
    def cyan(shade: Literal[900, 800, 700, 600, 500, 400, 300, 200, 100, 50] = 500) -> int:
        """Get shade of cyan color from Google Material Design."""
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
        return shades[shade]

    @staticmethod
    def teal(shade: Literal[900, 800, 700, 600, 500, 400, 300, 200, 100, 50] = 500) -> int:
        """Get shade of teal color from Google Material Design."""
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
        return shades[shade]

    green_900 = 0x1B5E20
    green_800 = 0x2E7D32
    green_700 = 0x388E3C
    green_600 = 0x43A047
    green_500 = 0x4CAF50
    green_400 = 0x66BB6A
    green_300 = 0x81C784
    green_200 = 0xA5D6A7
    green_100 = 0xC8E6C9
    green_50 = 0xE8F5E9

    @staticmethod
    def green(shade: Literal[900, 800, 700, 600, 500, 400, 300, 200, 100, 50] = 500) -> int:
        """Get shade of green color from Google Material Design."""
        shades = {}
        return shades[shade]

    @staticmethod
    def light_green(shade: Literal[900, 800, 700, 600, 500, 400, 300, 200, 100, 50] = 500) -> int:
        """Get shade of light green color from Google Material Design."""
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
        return shades[shade]

    @staticmethod
    def lime(shade: Literal[900, 800, 700, 600, 500, 400, 300, 200, 100, 50] = 500) -> int:
        """Get shade of lime color from Google Material Design."""
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
        return shades[shade]

    @staticmethod
    def yellow(shade: Literal[900, 800, 700, 600, 500, 400, 300, 200, 100, 50] = 500) -> int:
        """Get shade of yellow color from Google Material Design."""
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
        return shades[shade]

    @staticmethod
    def amber(shade: Literal[900, 800, 700, 600, 500, 400, 300, 200, 100, 50] = 500) -> int:
        """Get shade of amber color from Google Material Design."""
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
        return shades[shade]

    @staticmethod
    def orange(shade: Literal[900, 800, 700, 600, 500, 400, 300, 200, 100, 50] = 500) -> int:
        """Get shade of orange color from Google Material Design."""
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
        return shades[shade]

    @staticmethod
    def deep_orange(shade: Literal[900, 800, 700, 600, 500, 400, 300, 200, 100, 50] = 500) -> int:
        """Get shade of deep orange color from Google Material Design."""
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
        return shades[shade]

    @staticmethod
    def brown(shade: Literal[900, 800, 700, 600, 500, 400, 300, 200, 100, 50] = 500) -> int:
        """Get shade of brown color from Google Material Design."""
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
        return shades[shade]

    @staticmethod
    def gray(shade: Literal[900, 800, 700, 600, 500, 400, 300, 200, 100, 50] = 500) -> int:
        """Get shade of gray color from Google Material Design."""
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
        return shades[shade]

    @staticmethod
    def blue_gray(shade: Literal[900, 800, 700, 600, 500, 400, 300, 200, 100, 50] = 500) -> int:
        """Get shade of blue gray color from Google Material Design."""
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
        return shades[shade]

    @staticmethod
    def black(_shade: Literal[900, 800, 700, 600, 500, 400, 300, 200, 100, 50] = 500) -> int:
        """Get shade of black color from Google Material Design."""
        return 0x000000  # yes shade doesn't matter

    @staticmethod
    def white(_shade: Literal[900, 800, 700, 600, 500, 400, 300, 200, 100, 50] = 500) -> int:
        """Get shade of white color from Google Material Design."""
        return 0xFFFFFF  # yes shade doesn't matter


class Accent:
    """Material Design Color Palette with Accent Designs.

    https://m2.material.io/design/color/the-color-system.html#tools-for-picking-colors

    Notes
    -----
    This class' static methods return `int` because `discord.Embed.from_dict` only accepts `int` for its "color" field.
    """

    @staticmethod
    def red(shade: Literal[700, 400, 200, 100] = 200) -> int:
        """Get shade of red color from Google Material Accent Design."""
        shades = {
            700: 0xD50000,
            400: 0xFF1744,
            200: 0xFF5252,
            100: 0xFF8A80,
        }
        return shades[shade]

    @staticmethod
    def pink(shade: Literal[700, 400, 200, 100] = 200) -> int:
        """Get shade of pink color from Google Material Accent Design."""
        shades = {
            700: 0xC51162,
            400: 0xF50057,
            200: 0xFF4081,
            100: 0xFF80AB,
        }
        return shades[shade]

    @staticmethod
    def purple(shade: Literal[700, 400, 200, 100] = 200) -> int:
        """Get shade of purple color from Google Material Accent Design."""
        shades = {
            700: 0xAA00FF,
            400: 0xD500F9,
            200: 0xE040FB,
            100: 0xEA80FC,
        }
        return shades[shade]

    @staticmethod
    def deep_purple(shade: Literal[700, 400, 200, 100] = 200) -> int:
        """Get shade of deep purple color from Google Material Accent Design."""
        shades = {
            700: 0x6200EA,
            400: 0x651FFF,
            200: 0x7C4DFF,
            100: 0xB388FF,
        }
        return shades[shade]

    @staticmethod
    def indigo(shade: Literal[700, 400, 200, 100] = 200) -> int:
        """Get shade of indigo color from Google Material Accent Design."""
        shades = {
            700: 0x304FFE,
            400: 0x3D5AFE,
            200: 0x536DFE,
            100: 0x8C9EFF,
        }
        return shades[shade]

    @staticmethod
    def blue(shade: Literal[700, 400, 200, 100] = 200) -> int:
        """Get shade of blue color from Google Material Accent Design."""
        shades = {
            700: 0x2962FF,
            400: 0x2979FF,
            200: 0x448AFF,
            100: 0x82B1FF,
        }
        return shades[shade]

    @staticmethod
    def light_blue(shade: Literal[700, 400, 200, 100] = 200) -> int:
        """Get shade of light blue color from Google Material Accent Design."""
        shades = {
            700: 0x0091EA,
            400: 0x00B0FF,
            200: 0x40C4FF,
            100: 0x80D8FF,
        }
        return shades[shade]

    @staticmethod
    def cyan(shade: Literal[700, 400, 200, 100] = 200) -> int:
        """Get shade of cyan color from Google Material Accent Design."""
        shades = {
            700: 0x00B8D4,
            400: 0x00E5FF,
            200: 0x18FFFF,
            100: 0x84FFFF,
        }
        return shades[shade]

    @staticmethod
    def teal(shade: Literal[700, 400, 200, 100] = 200) -> int:
        """Get shade of teal color from Google Material Accent Design."""
        shades = {
            700: 0x00BFA5,
            400: 0x1DE9B6,
            200: 0x64FFDA,
            100: 0xA7FFEB,
        }
        return shades[shade]

    @staticmethod
    def green(shade: Literal[700, 400, 200, 100] = 200) -> int:
        """Get shade of green color from Google Material Accent Design."""
        shades = {
            700: 0x00C853,
            400: 0x00E676,
            200: 0x69F0AE,
            100: 0xB9F6CA,
        }
        return shades[shade]

    @staticmethod
    def light_green(shade: Literal[700, 400, 200, 100] = 200) -> int:
        """Get shade of light green color from Google Material Accent Design."""
        shades = {
            700: 0x64DD17,
            400: 0x76FF03,
            200: 0xB2FF59,
            100: 0xCCFF90,
        }
        return shades[shade]

    @staticmethod
    def lime(shade: Literal[700, 400, 200, 100] = 200) -> int:
        """Get shade of lime color from Google Material Accent Design."""
        shades = {
            700: 0xAEEA00,
            400: 0xC6FF00,
            200: 0xEEFF41,
            100: 0xF4FF81,
        }
        return shades[shade]

    @staticmethod
    def yellow(shade: Literal[700, 400, 200, 100] = 200) -> int:
        """Get shade of yellow color from Google Material Accent Design."""
        shades = {
            700: 0xFFD600,
            400: 0xFFEA00,
            200: 0xFFFF00,
            100: 0xFFFF8D,
        }
        return shades[shade]

    @staticmethod
    def amber(shade: Literal[700, 400, 200, 100] = 200) -> int:
        """Get shade of amber color from Google Material Accent Design."""
        shades = {
            700: 0xFFAB00,
            400: 0xFFC400,
            200: 0xFFD740,
            100: 0xFFE57F,
        }
        return shades[shade]

    @staticmethod
    def orange(shade: Literal[700, 400, 200, 100] = 200) -> int:
        """Get shade of orange color from Google Material Accent Design."""
        shades = {
            700: 0xFF6D00,
            400: 0xFF9100,
            200: 0xFFAB40,
            100: 0xFFD180,
        }
        return shades[shade]

    @staticmethod
    def deep_orange(shade: Literal[700, 400, 200, 100] = 200) -> int:
        """Get shade of deep orange color from Google Material Accent Design."""
        shades = {
            700: 0xDD2C00,
            400: 0xFF3D00,
            200: 0xFF6E40,
            100: 0xFF9E80,
        }
        return shades[shade]

    # PS. brown, gray, blue_gray, black, white - these colors do not have Accent versions


if __name__ == "__main__":
    from PIL import Image

    x = Palette.purple()
    x = 0xDB7093

    rectangle = Image.new("RGB", (600, 300), f"#{x:0>6x}")
    rectangle.show()
