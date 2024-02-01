"""
For some reason, any google-search "Python Google Translate" ends in some misery.
Ready-to-go libs are either blocking, abandoned, have unsolved bugs or just bad code
while I just need a simple function.
The best lib-solution in here is `async-google-trans-new` which still loses the race
bcs they have `detect` language method separated from `translate` meaning we need to do two requests.

So let's try writing my own simple `translate` function.
Obligatory sources I used to write this code:

* Issue #268 by SuperSonicHub1 in py-googletrans
    - https://github.com/ssut/py-googletrans/issues/268
* `async-google-trans-new` source code (MIT License)
    - https://github.com/sevenc-nanashi/async-google-trans-new
* RoboDanny's translator.py (license MPL v2 from Rapptz/RoboDanny)
    - https://github.com/Rapptz/RoboDanny/blob/rewrite/cogs/utils/translator.py
"""

from __future__ import annotations

from typing import TYPE_CHECKING, NamedTuple, TypedDict

from .bases import AluBotException

if TYPE_CHECKING:
    from aiohttp import ClientSession

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


class TranslateError(AluBotException):
    def __init__(self, status_code: int, text: str) -> None:
        self.status_code: int = status_code
        self.text: str = text
        super().__init__(f"Google Translate responded with HTTP Status Code {status_code}")


class TranslatedSentence(TypedDict):
    trans: str
    orig: str


class TranslateResult(NamedTuple):
    original: str
    translated: str
    source_lang: str
    target_lang: str


async def translate(
    text: str, *, source_lang: str = "auto", target_lang: str = "en", session: ClientSession
) -> TranslateResult:
    """Google Translate"""
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
            text = await resp.text()
            raise TranslateError(resp.status, text)

        data = await resp.json()
        src = data.get("src", "Unknown")
        sentences: list[TranslatedSentence] = data.get("sentences", [])
        if len(sentences) == 0:
            raise RuntimeError("Google translate returned no information")

        return TranslateResult(
            original="".join(sentence.get("orig", "") for sentence in sentences),
            translated="".join(sentence.get("trans", "") for sentence in sentences),
            source_lang=LANGUAGES.get(src, src),
            target_lang=LANGUAGES.get(target_lang, "Unknown"),
        )
