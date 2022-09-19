from discord import File

from PIL import Image, ImageOps
from io import BytesIO, StringIO

from typing import Union
from collections.abc import Sequence


def get_text_wh(text_string, font):  # wh for width, height = dimensions
    # https://stackoverflow.com/a/46220683/9263761
    # https://levelup.gitconnected.com/how-to-properly-calculate-text-size-in-pil-images-17a2cc6f51fd
    ascent, descent = font.getmetrics()

    text_width = font.getmask(text_string).getbbox()[2]
    text_height = font.getmask(text_string).getbbox()[3] + descent

    return text_width, text_height


def str_to_file(string, filename="file.txt") -> File:
    fp = BytesIO(StringIO(string).read().encode('utf8'))
    fp.seek(0)
    return File(fp, filename=filename)


def plt_to_file(fig, filename='plt.png') -> File:
    image_binary = BytesIO()
    fig.savefig(image_binary)
    image_binary.seek(0)
    return File(fp=image_binary, filename=filename)


def img_to_file(image, filename='fromalubot.png', fmt='PNG') -> File:
    image_binary = BytesIO()  # image is probably type PIL.PngImagePlugin.PngImageFile
    image.save(image_binary, fmt)
    image_binary.seek(0)
    return File(fp=image_binary, filename=filename)


async def url_to_img(
        session,
        url: Union[str, Sequence[str]],
        *,
        return_list: bool = False
):
    if isinstance(url, str):
        url_array = [url]
    elif isinstance(url, Sequence):
        url_array = url
    else:
        raise TypeError('Expected url as string or sequence of urls as strings')

    images = []
    for url_item in url_array:
        async with session.get(url_item) as resp:
            if resp.status != 200:
                print(f"imgtools.url_to_img: Oups; Could not download file from {url_item}")
            images.append(Image.open(BytesIO(await resp.read())))
    if return_list:
        return images
    else:
        return images if len(images) > 1 or len(images) == 0 else images[0]


async def url_to_file(
        session,
        url: Union[str, Sequence[str]],
        filename: str = 'fromalubot.png',
        *,
        return_list: bool = False
) -> Union[File, Sequence[File]]:
    if isinstance(url, str):
        url_array = [url]
    elif isinstance(url, Sequence):
        url_array = url
    else:
        raise TypeError('Expected url as string or sequence of urls as strings')

    files = []
    for counter, url_item in enumerate(url_array):
        async with session.get(url_item) as resp:
            data = BytesIO(await resp.read())
            files.append(File(data, f'{counter}{filename}'))
    if return_list:
        return files
    else:
        return files if len(files) > 1 or len(files) == 0 else files[0]


async def invert_image(r):
    img = Image.open(BytesIO(await r.read())).convert('RGB')
    inverted_image = ImageOps.invert(img)
    return inverted_image
