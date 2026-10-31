# Copyright (C) 2020-present, Irene Adler ❤ (@Aluerie).
# Licensed under MPL-2.0, see the LICENSE file for details.
"""Images.

Small helpers shared by the features that draw images with ``Pillow`` (rank card, welcome image).
"""

from __future__ import annotations

import functools

from PIL import Image, ImageDraw, ImageFont

from . import const

__all__ = (
    "circle_mask",
    "font",
)

MASK_SUPERSAMPLING = 4
"""How many times bigger the circle is drawn before it is scaled down (that is what makes the edge smooth)."""


@functools.cache
def font(filename: str, size: int) -> ImageFont.FreeTypeFont:
    """Load a font from the assets folder (cached, since loading it from the disk is slow).

    Parameters
    ----------
    filename
        Name of the file in ``assets/fonts``.
    size
        Font size in pixels.
    """
    return ImageFont.truetype(str(const.ASSETS / "fonts" / filename), size)


def circle_mask(size: int) -> Image.Image:
    """Make an anti-aliased circular mask by drawing a big circle and scaling it down.

    Parameters
    ----------
    size
        Width and height of the mask in pixels.
    """
    big_size = size * MASK_SUPERSAMPLING
    big = Image.new("L", (big_size, big_size), 0)
    ImageDraw.Draw(big).ellipse((0, 0, big_size - 1, big_size - 1), fill=255)
    return big.resize((size, size), Image.Resampling.LANCZOS)
