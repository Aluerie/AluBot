from __future__ import annotations

from collections.abc import Sequence
from io import BytesIO, StringIO
from typing import TYPE_CHECKING, Tuple, Union, overload

import discord
from PIL import Image, ImageOps

if TYPE_CHECKING:
    from aiohttp import ClientSession
    from matplotlib.figure import Figure
    from PIL import ImageFont


class ImgToolsClient:
    def __init__(self, session: ClientSession):
        self.session: ClientSession = session

    @staticmethod
    def get_text_wh(text: str, font: ImageFont.FreeTypeFont) -> Tuple[int, int]:
        """Get text wh-dimensions for selected font

        Returns
        ---
        Tuple[int, int]
            (width, height) - width and height of the text written in specified font
        """
        # https://stackoverflow.com/a/46220683/9263761
        # https://levelup.gitconnected.com/how-to-properly-calculate-text-size-in-pil-images-17a2cc6f51fd

        ascent, descent = font.getmetrics()

        text_width = font.getmask(text).getbbox()[2]
        text_height = font.getmask(text).getbbox()[3] + descent

        return text_width, text_height

    @staticmethod
    def str_to_file(string: str, filename: str = "file.txt") -> discord.File:
        fp = BytesIO(StringIO(string).read().encode('utf8'))
        fp.seek(0)
        return discord.File(fp, filename=filename)

    @staticmethod
    def plt_to_file(fig: Figure, filename: str = 'plt.png') -> discord.File:
        image_binary = BytesIO()
        fig.savefig(image_binary)
        image_binary.seek(0)
        return discord.File(fp=image_binary, filename=filename)

    @staticmethod
    def img_to_file(image: Image.Image, filename: str = 'FromAluBot.png', fmt: str = 'PNG') -> discord.File:
        image_binary = BytesIO()
        image.save(image_binary, fmt)
        image_binary.seek(0)
        return discord.File(fp=image_binary, filename=filename)

    @overload
    async def url_to_img(self, url: str, *, return_list: bool = ...) -> Image.Image:
        ...

    @overload
    async def url_to_img(self, url: Sequence[str], *, return_list: bool = ...) -> Sequence[Image.Image]:
        ...

    async def url_to_img(self, url: Union[str, Sequence[str]], *, return_list: bool = False):
        if isinstance(url, str):
            url_array = [url]
        elif isinstance(url, Sequence):
            url_array = url
        else:
            raise TypeError('Expected url as string or sequence of urls as strings')

        images = []
        for url_item in url_array:
            async with self.session.get(url_item) as resp:
                if resp.status != 200:
                    print(f"imgtools.url_to_img: Oups; Could not download file from {url_item}")
                images.append(Image.open(BytesIO(await resp.read())))
        if return_list:
            return images
        else:
            return images if len(images) > 1 or len(images) == 0 else images[0]

    async def url_to_file(
        self, url: Union[str, Sequence[str]], filename: str = 'FromAluBot.png', *, return_list: bool = False
    ) -> Union[discord.File, Sequence[discord.File]]:
        if isinstance(url, str):
            url_array = [url]
        elif isinstance(url, Sequence):
            url_array = url
        else:
            raise TypeError('Expected url as string or sequence of urls as strings')

        files = []
        for counter, url_item in enumerate(url_array):
            async with self.session.get(url_item) as resp:
                data = BytesIO(await resp.read())
                files.append(discord.File(data, f'{counter}{filename}'))
        if return_list:
            return files
        else:
            return files if len(files) > 1 or len(files) == 0 else files[0]

    @staticmethod
    async def invert_image(r):
        img = Image.open(BytesIO(await r.read())).convert('RGB')
        inverted_image = ImageOps.invert(img)
        return inverted_image


# just convenience for importing static methods,
# so we don't have to
# >>> from imgtools import ImgToolsClient
# >>> ImgToolsClient.str_to_file
# but just
# >>> from imgtools import str_to_file
str_to_file = ImgToolsClient.str_to_file
