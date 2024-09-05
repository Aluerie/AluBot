"""## Original source:
* RoboDanny's cogs.utils.buttons (license MPL v2 from Rapptz/RoboDanny)
    https://github.com/Rapptz/RoboDanny/blob/rewrite/cogs/buttons.py.

# todo: rework this according to my needs :x
"""

from __future__ import annotations

import logging
import re
from typing import TYPE_CHECKING, Any, NamedTuple, Self, override

import discord
import yarl
from discord import app_commands
from discord.ext import commands, menus
from lxml import html

from utils import pages

from .._base import EducationalCog

log = logging.getLogger(__name__)

if TYPE_CHECKING:
    from aiohttp import ClientSession

    from bot import AluContext

    # from .utils.context import Context, GuildContext
    # from .utils.paginator import RoboPages


DICTIONARY_EMBED_COLOUR = discord.Colour(0x5F9EB3)


def html_to_markdown(node: Any, *, include_spans: bool = False) -> str:
    text = []
    italics_marker = "_"
    for child in node:
        if child.tag == "i":
            text.append(f"{italics_marker}{child.text.strip()}{italics_marker}")
            italics_marker = "_" if italics_marker == "*" else "*"  # type: ignore # xd
        elif child.tag == "b":
            if text and text[-1].endswith("*"):
                text.append("\u200b")

            text.append(f"**{child.text.strip()}**")
        elif child.tag == "a":
            # No markup for links
            text.append(child.text)
        elif include_spans and child.tag == "span":
            text.append(child.text)

        if child.tail:
            text.append(child.tail)

    return "".join(text).strip()


def inner_trim(s: str, *, _regex: re.Pattern[str] = re.compile(r"\s+")) -> str:
    return _regex.sub(" ", s.strip())


class FreeDictionaryDefinition(NamedTuple):
    definition: str
    example: str | None
    children: list[FreeDictionaryDefinition]

    @classmethod
    def from_node(cls, node: Any) -> Self:
        # Note that in here we're inside either a ds-list or a ds-single node
        # The first child is basically always a superfluous bolded number
        number = node.find("b")
        definition: str = node.text or ""
        if number is not None:
            tail = number.tail
            node.remove(number)
            if tail:
                definition = tail

        definition += html_to_markdown(node, include_spans=False)
        definition = inner_trim(definition)

        example: str | None = None
        example_nodes = node.xpath("./span[@class='illustration']")
        if example_nodes:
            example = example_nodes[0].text_content()

        children: list[FreeDictionaryDefinition] = [
            cls.from_node(child) for child in node.xpath("./div[@class='sds-list']")
        ]
        return cls(definition, example, children)

    def to_json(self) -> dict[str, Any]:
        return {
            "definition": self.definition,
            "example": self.example,
            "children": [child.to_json() for child in self.children],
        }

    def to_markdown(self, *, indent: int = 2) -> str:
        content = self.definition
        if self.example:
            content = f"{content} [*{self.example}*]"
        if not content:
            content = "\u200b"
        if self.children:
            inner = "\n".join(f'{" " * indent }- {child.to_markdown(indent=indent + 2)}' for child in self.children)
            return f"{content}\n{inner}"
        return content


class FreeDictionaryMeaning:
    part_of_speech: str
    definitions: list[FreeDictionaryDefinition]

    __slots__ = ("part_of_speech", "definitions")

    def __init__(self, definitions: Any, part_of_speech: str) -> None:
        self.part_of_speech = part_of_speech
        self.definitions = [FreeDictionaryDefinition.from_node(definition) for definition in definitions]

    def to_json(self) -> dict[str, Any]:
        return {"part_of_speech": self.part_of_speech, "definitions": [defn.to_json() for defn in self.definitions]}

    @property
    def markdown(self) -> str:
        inner = "\n".join(f"{i}. {defn.to_markdown()}" for i, defn in enumerate(self.definitions, start=1))
        return f"{self.part_of_speech}\n{inner}"


class FreeDictionaryPhrasalVerb(NamedTuple):
    word: str
    meaning: FreeDictionaryMeaning

    def to_embed(self) -> discord.Embed:
        return discord.Embed(title=self.word, colour=DICTIONARY_EMBED_COLOUR, description=self.meaning.markdown)


class FreeDictionaryWord:
    raw_word: str
    word: str
    pronunciation_url: str | None
    pronunciation: str | None
    meanings: list[FreeDictionaryMeaning]
    phrasal_verbs: list[FreeDictionaryPhrasalVerb]

    def __init__(self, raw_word: str, word: str, node: Any) -> None:
        self.raw_word = raw_word
        self.word = word
        self.meanings = []
        self.phrasal_verbs = []
        self.get_pronunciation(node)
        self.get_meanings(node)

    def get_pronunciation(self, node: Any) -> None:
        self.pronunciation_url = None
        self.pronunciation = None
        snd = node.xpath("span[@class='snd' and @data-snd]")
        if not snd:
            return None

        snd = snd[0]
        pron = node.xpath("span[@class='pron']")
        if pron:
            self.pronunciation = pron[0].text_content() + (pron[0].tail or "")
            self.pronunciation = self.pronunciation.strip()

        data_src = node.attrib.get("data-src")
        if data_src is not None:
            mp3 = snd.attrib.get("data-snd")
            self.pronunciation_url = f"https://img.tfd.com/{data_src}/{mp3}.mp3"

    def get_meanings(self, node: Any) -> None:
        conjugations: str | None = None

        data_src = node.attrib.get("data-src")

        child_nodes = []
        if data_src == "hm":
            child_nodes = node.xpath("./div[@class='pseg']")
        elif data_src == "hc_dict":
            child_nodes = node.xpath("./div[not(@class)]")
        elif data_src == "rHouse":
            child_nodes = node

        for div in child_nodes:
            definitions = div.xpath("div[@class='ds-list' or @class='ds-single']")
            if not definitions:
                # Probably a conjugation
                # If it isn't a conjugation then it probably just has a single definition
                bolded = div.find("b")
                if bolded is not None:
                    children = iter(div)
                    next(children)  # skip the italic `v.` bit
                    conjugations = html_to_markdown(children, include_spans=True)
                    continue

            pos_node = div.find("i")
            if pos_node is None:
                continue

            pos = html_to_markdown(div)
            if conjugations is not None:
                pos = f"{pos}{conjugations}" if conjugations.startswith(",") else f"{pos} {conjugations}"

            meaning = FreeDictionaryMeaning(definitions, pos)
            self.meanings.append(meaning)

        for div in node.find_class("pvseg"):
            # phrasal verbs are simple
            # <b><i>{word}</i></b>
            # ... definitions
            word = div.find("b/i")
            if word is None:
                continue

            word = word.text_content().strip()
            meaning = FreeDictionaryMeaning(div, "phrasal verb")
            self.phrasal_verbs.append(FreeDictionaryPhrasalVerb(word, meaning))

    def to_json(self) -> dict[str, Any]:
        return {
            "raw_word": self.raw_word,
            "word": self.word,
            "pronunciation_url": self.pronunciation_url,
            "pronunciation": self.pronunciation,
            "meanings": [meaning.to_json() for meaning in self.meanings],
            "phrasal_verbs": [
                {
                    "word": verb.word,
                    "meaning": verb.meaning.to_json(),
                }
                for verb in self.phrasal_verbs
            ],
        }


async def parse_free_dictionary_for_word(session: ClientSession, *, word: str) -> FreeDictionaryWord | None:
    url = yarl.URL("https://www.thefreedictionary.com") / word

    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:109.0) Gecko/20100101 Firefox/114.0",
        "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,*/*;q=0.8",
        "Accept-Language": "en-US,en;q=0.5",
        "Accept-Encoding": "gzip, deflate",
        "Upgrade-Insecure-Requests": "1",
        "Sec-Fetch-Dest": "document",
        "Sec-Fetch-Mode": "navigate",
        "Sec-Fetch-Site": "same-origin",
        "Pragma": "no-cache",
        "Cache-Control": "no-cache",
        "TE": "trailers",
    }

    async with session.get(url, headers=headers) as resp:
        if resp.status != 200:
            log.info("Got non-200 status code from free dictionary for word %r: %s", word, resp.status)
            return None

        text = await resp.text()
        document = html.document_fromstring(text)

        try:
            definitions = document.get_element_by_id("Definition")
        except KeyError:
            log.info("Could not find definition element")
            return None

        h1 = document.find("h1")
        raw_word = h1.text if h1 is not None else word

        section = definitions.xpath("section[@data-src='hm' or @data-src='hc_dict' or @data-src='rHouse']")
        if not section:
            log.info("Could not find section element")
            return None

        node = section[0]
        h2: Any | None = node.find("h2")
        if h2 is None:
            log.info("Could not find word element")
            return None

        try:
            return FreeDictionaryWord(raw_word, h2.text, node)
        except RuntimeError:
            log.exception("Error happened while parsing free dictionary")
            return None


async def free_dictionary_autocomplete_query(session: ClientSession, *, query: str) -> list[str]:
    url = yarl.URL("https://www.thefreedictionary.com/_/search/suggest.ashx")

    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:109.0) Gecko/20100101 Firefox/114.0",
        "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,*/*;q=0.8",
        "Accept-Language": "en-US,en;q=0.5",
        "Accept-Encoding": "gzip, deflate",
        "Upgrade-Insecure-Requests": "1",
        "Sec-Fetch-Dest": "document",
        "Sec-Fetch-Mode": "navigate",
        "Sec-Fetch-Site": "same-origin",
        "Pragma": "no-cache",
        "Cache-Control": "no-cache",
        "TE": "trailers",
    }

    async with session.get(url, params={"query": query}, headers=headers) as resp:
        if resp.status != 200:
            return []

        js = await resp.json()
        if len(js) == 2:
            return js[1]
        return []


class FreeDictionaryWordMeaningPageSource(menus.ListPageSource):
    entries: list[FreeDictionaryMeaning]

    def __init__(self, word: FreeDictionaryWord) -> None:
        super().__init__(entries=word.meanings, per_page=1)
        self.word: FreeDictionaryWord = word

    @override
    async def format_page(self, menu: pages.Paginator, entry: FreeDictionaryMeaning) -> discord.Embed:
        maximum = self.get_max_pages()
        heading = (
            f"{self.word.raw_word}: {menu.current_page_number + 1} out of {maximum}"
            if maximum >= 2
            else self.word.raw_word
        )
        title = f"{self.word.word} {self.word.pronunciation}" if self.word.pronunciation else self.word.word

        embed = discord.Embed(title=title, colour=DICTIONARY_EMBED_COLOUR)
        embed.set_author(name=heading)
        embed.description = entry.markdown
        return embed


class DictionaryCog(EducationalCog):
    @commands.hybrid_command(name="define")
    @app_commands.describe(word="The word to look up")
    async def _define(self, ctx: AluContext, *, word: str) -> None:
        """Looks up an English word in the dictionary."""
        result = await parse_free_dictionary_for_word(ctx.session, word=word)
        if result is None:
            await ctx.send("Could not find that word.", ephemeral=True)
            return

        # Check if it's a phrasal verb somehow
        phrase = discord.utils.find(lambda v: v.word.lower() == word.lower(), result.phrasal_verbs)
        if phrase is not None:
            embed = phrase.to_embed()
            await ctx.send(embed=embed)
            return

        if not result.meanings:
            await ctx.send("Could not find any definitions for that word.", ephemeral=True)
            return

        # Paginate over the various meanings of the word
        p = pages.Paginator(ctx, FreeDictionaryWordMeaningPageSource(result))
        await p.start()

    @_define.autocomplete("word")
    async def _define_word_autocomplete(
        self, interaction: discord.Interaction, query: str
    ) -> list[app_commands.Choice[str]]:
        if not query:
            return []

        result = await free_dictionary_autocomplete_query(self.bot.session, query=query)
        return [app_commands.Choice(name=word, value=word) for word in result][:25]
