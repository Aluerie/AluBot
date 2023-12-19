from __future__ import annotations

import logging
from io import BytesIO, StringIO
from typing import TYPE_CHECKING

import discord
from PIL import Image

from .bases.errors import SomethingWentWrong

if TYPE_CHECKING:
    from aiohttp import ClientSession
    from matplotlib.figure import Figure
    from PIL import ImageFont

log = logging.getLogger(__name__)
log.setLevel(logging.DEBUG)


class TransposeClient:
    """Transpose object of X class to an object of Y class

    The class primarily used to convert things into discord.File or PIL.Image.Image.
    These functions are used so often that I decided to make an extra class.

    There are also some image utilities.
    """

    # The name is "transpose" because "convert"/"transform" have meanings in discord.py

    def __init__(self, session: ClientSession):
        self.session: ClientSession = session

    @staticmethod
    def get_text_wh(text: str, font: ImageFont.FreeTypeFont) -> tuple[int, int]:
        """Get text wh-dimensions for selected font

        Returns
        ---
        Tuple[int, int]
            (width, height) - width and height of the text written in specified font
        """
        # https://stackoverflow.com/a/46220683/9263761
        # https://levelup.gitconnected.com/how-to-properly-calculate-text-size-in-pil-images-17a2cc6f51fd

        _ascent, descent = font.getmetrics()

        text_width = font.getmask(text).getbbox()[2]
        text_height = font.getmask(text).getbbox()[3] + descent

        return text_width, text_height

    @staticmethod
    def str_to_file(string: str, filename: str = "file.txt") -> discord.File:
        """Convert string to discord.File"""
        fp = BytesIO(StringIO(string).read().encode("utf8"))
        fp.seek(0)
        return discord.File(fp, filename=filename)

    @staticmethod
    def plot_to_file(figure: Figure, filename: str = "plt.png") -> discord.File:
        """Convert matplotlib.figure.Figure to discord.File"""
        image_binary = BytesIO()
        figure.savefig(image_binary)
        image_binary.seek(0)
        return discord.File(fp=image_binary, filename=filename)

    @staticmethod
    def image_to_file(image: Image.Image, filename: str = "fromAluBot.png", extension: str = "PNG") -> discord.File:
        """Convert PIL.Image.Image to discord.File"""
        image_binary = BytesIO()
        image.save(image_binary, extension)
        image_binary.seek(0)
        return discord.File(fp=image_binary, filename=filename)

    @staticmethod
    async def attachment_to_image(attachment: discord.Attachment) -> Image.Image:
        """Convert discord.Attachment to Image.Image"""
        return Image.open(BytesIO(await attachment.read()))

    async def url_to_image(self, url: str) -> Image.Image:
        """Convert URL to PIL.Image.Image"""
        log.debug(url)
        async with self.session.get(url) as response:
            # if not response.ok:
            #     raise SomethingWentWrong(f"url_to_img: could not download file from {url}")
            return Image.open(BytesIO(await response.read()))

    async def url_to_file(self, url: str, filename: str = "fromAluBot.png") -> discord.File:
        """Convert URL to discord.File"""
        async with self.session.get(url) as resp:
            data = BytesIO(await resp.read())
            return discord.File(data, filename)