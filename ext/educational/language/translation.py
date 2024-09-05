"""TRANSLATION COMMANDS.

This extension provides commands to translate to English using Google Translate services.

Disclaimer
----------
For some reason, any google-search "Python Google Translate" ends in some misery.
Ready-to-go libs are either blocking, abandoned, have unsolved bugs or bad code while I just need a simple function.

The best lib-solution in here is `async-google-trans-new` which still loses the race
because they have `detect` language method separated from `translate` meaning we need to do two requests.
So let's try writing my own simple `translate` function (90% of which is yoinked from RoboDanny - source below).

Sources
-------
* Issue #268 by SuperSonicHub1 in py-googletrans
    - https://github.com/ssut/py-googletrans/issues/268
* `async-google-trans-new` source code (MIT License)
    - https://github.com/sevenc-nanashi/async-google-trans-new
* RoboDanny's translator.py (license MPL v2 from Rapptz/RoboDanny)
    - https://github.com/Rapptz/RoboDanny/blob/rewrite/cogs/utils/translator.py
"""
from __future__ import annotations

from typing import TYPE_CHECKING, Any, NamedTuple, TypedDict, override

import discord
from discord import app_commands
from discord.ext import commands

from utils import const, errors

from .._base import EducationalCog

if TYPE_CHECKING:
    from aiohttp import ClientSession

    from bot import AluBot, AluContext


# fmt: off
LANGUAGES = {  # there are 109 languages
    "af": "Afrikaans", "sq": "Albanian", "am": "Amharic", "ar": "Arabic", "hy": "Armenian", "az": "Azerbaijani",
    "eu": "Basque", "be": "Belarusian", "bn": "Bengali", "bs": "Bosnian", "bg": "Bulgarian", "ca": "Catalan",
    "ceb": "Cebuano", "ny": "Chichewa", "zh-cn": "Chinese (simplified)", "zh-tw": "Chinese (traditional)",
    "co": "Corsican", "hr": "Croatian", "cs": "Czech", "da": "Danish", "nl": "Dutch", "en": "English",
    "eo": "Esperanto", "et": "Estonian", "tl": "Filipino", "fi": "Finnish", "fr": "French", "fy": "Frisian",
    "gl": "Galician", "ka": "Georgian", "de": "German", "el": "Greek", "gu": "Gujarati", "ht": "Haitian creole",
    "ha": "Hausa", "haw": "Hawaiian", "iw": "Hebrew", "he": "Hebrew", "hi": "Hindi", "hmn": "Hmong", "hu": "Hungarian",
    "is": "Icelandic", "ig": "Igbo", "id": "Indonesian", "ga": "Irish", "it": "Italian", "ja": "Japanese",
    "jw": "Javanese", "kn": "Kannada", "kk": "Kazakh", "km": "Khmer", "ko": "Korean", "ku": "Kurdish (kurmanji)",
    "ky": "Kyrgyz", "lo": "Lao", "la": "Latin", "lv": "Latvian", "lt": "Lithuanian", "lb": "Luxembourgish",
    "mk": "Macedonian", "mg": "Malagasy", "ms": "Malay", "ml": "Malayalam", "mt": "Maltese", "mi": "Maori",
    "mr": "Marathi", "mn": "Mongolian", "my": "Myanmar (burmese)", "ne": "Nepali", "no": "Norwegian", "or": "Odia",
    "ps": "Pashto", "fa": "Persian", "pl": "Polish", "pt": "Portuguese", "pa": "Punjabi", "ro": "Romanian",
    "ru": "Russian", "sm": "Samoan", "gd": "Scots gaelic", "sr": "Serbian", "st": "Sesotho", "sn": "Shona",
    "sd": "Sindhi", "si": "Sinhala", "sk": "Slovak", "sl": "Slovenian", "so": "Somali", "es": "Spanish",
    "su": "Sundanese", "sw": "Swahili", "sv": "Swedish", "tg": "Tajik", "ta": "Tamil", "tt": "Tatar", "te": "Telugu",
    "th": "Thai", "tr": "Turkish", "tk": "Turkmen", "uk": "Ukrainian", "ur": "Urdu", "ug": "Uyghur", "uz": "Uzbek",
    "vi": "Vietnamese", "cy": "Welsh", "xh": "Xhosa", "yi": "Yiddish", "yo": "Yoruba", "zu": "Zulu",
}
# fmt: on


class TranslatedSentence(TypedDict):
    """TranslatedSentence."""

    trans: str
    orig: str


class TranslateResult(NamedTuple):
    """TranslatedResult."""

    original: str
    translated: str
    source_lang: str
    target_lang: str


async def translate(
    text: str,
    *,
    source_lang: str = "auto",
    target_lang: str = "en",
    session: ClientSession,
) -> TranslateResult:
    """Google Translate."""
    query = {
        "dj": "1",
        "dt": ["sp", "t", "ld", "bd"],
        "client": "dict-chrome-ex",  # Needs to be dict-chrome-ex or else you'll get a 403 error.
        "sl": source_lang,
        "tl": target_lang,
        "q": text,
    }

    headers = {
        "User-Agent": (
            "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
            "AppleWebKit/537.36 (KHTML, like Gecko) "
            "Chrome/104.0.0.0 Safari/537.36"
        )
    }

    async with session.get("https://clients5.google.com/translate_a/single", params=query, headers=headers) as resp:
        if resp.status != 200:
            raise errors.TranslateError(resp.status, text=await resp.text())

        data = await resp.json()
        src = data.get("src", "Unknown")
        sentences: list[TranslatedSentence] = data.get("sentences", [])
        if not sentences:
            msg = "Google translate returned no information"
            raise RuntimeError(msg)

        return TranslateResult(
            original="".join(sentence.get("orig", "") for sentence in sentences),
            translated="".join(sentence.get("trans", "") for sentence in sentences),
            source_lang=LANGUAGES.get(src, src),
            target_lang=LANGUAGES.get(target_lang, "Unknown"),
        )


class TranslateCog(EducationalCog):
    """Translate to English commands."""

    def __init__(self, bot: AluBot, *args: Any, **kwargs: Any) -> None:
        super().__init__(bot, *args, **kwargs)
        self.translate_context_menu = app_commands.ContextMenu(
            name="Translate to English",
            callback=self.translate_context_menu_callback,
        )

    @override
    def cog_load(self) -> None:
        self.bot.tree.add_command(self.translate_context_menu)

    @override
    async def cog_unload(self) -> None:
        self.bot.tree.remove_command(self.translate_context_menu.name, type=self.translate_context_menu.type)

    async def translate_embed(self, text: str) -> discord.Embed:
        """Embed-answer for translation commands."""
        # PS: TranslateError is handled in global ErrorHandler as `AluBotError`.
        result = await translate(text, session=self.bot.session)

        return discord.Embed(
            colour=const.Colour.blueviolet,
            title="Translate to English",
            description=result.translated,
        ).set_footer(text=f"Detected language: {result.source_lang}")

    async def translate_context_menu_callback(self, interaction: discord.Interaction, message: discord.Message) -> None:
        """Context Menu Translate."""
        if len(text := message.content) == 0:
            msg = "Sorry, but it seems, that this message doesn't have any text content to translate."
            raise errors.BadArgument(msg)

        e = await self.translate_embed(text)
        await interaction.response.send_message(embed=e, ephemeral=True)

    @commands.hybrid_command()
    @app_commands.describe(text="Enter text to translate")
    async def translate(self, ctx: AluContext, *, text: str) -> None:
        """Google Translate to English, auto-detects source language."""
        e = await self.translate_embed(text)
        await ctx.reply(embed=e)
