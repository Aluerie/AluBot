from __future__ import annotations

import re

SUPPORTED_SITES_DISPLAY_NAMES = (
    # Also remember to edit doc-string for `slash_fix_links`
    "Twitter",
    "Reddit",
    "Instagram",
    "TikTok",
    "DeviantArt",
    "Tumblr",
    "Pixiv",
    "Bsky",
    "Twitch Clips",
    "Spotify",
)

FIX_DICT: dict[str, str] = {
    # mapping: social network -> better embed site,
    # note the "slash" absence in the end and "https://" are important
    "x": "fxtwitter.com",
    "twitter": "fxtwitter.com",
    "reddit": "rxddit.com",
    "instagram": "oginstagram.com",
    "tiktok": "tnktok.com",
    "deviantart": "fixdeviantart.com",
    "tumblr": "tpmblr.com",
    "pixiv": "phixiv.net",
    "bsky": "bskyx.app",
    "twitch": "fxtwitch.seria.moe/clip",
    "clips": "fxtwitch.seria.moe/clip",
    "spotify": "fxspotify",
}

EMBED_FIXER_REGEX_PATTERN = re.compile(
    r"""
        # group(0) - the whole URL
        # group(1) - pre URL stuff
        (
        http[s]?
        ://
        (?: [a-zA-Z]+ \.)?  # `www.` or some subdomains like `open.spotify.`
        )
        # group(2) - the actual site host
        (
        x\.com|
        twitter\.com|
        reddit\.com|
        instagram\.com|
        tiktok\.com|
        deviantart\.com|
        tumblr\.com|
        pixiv\.net|
        bsky\.app|
        twitch\.tv/(?:[a-zA-Z]|[0-9]|[_])+/clip|
        clips\.twitch\.tv|
        spotify\.com
        )
        # group(3) - the rest of url
        # it's taken from `?tag url regex` in discord.py server. In a nutshell:
        # letters | digits | some symbols | some more symbols | url %percent-encoded symbols, i.e. %20 for space
        (/ (?: [a-zA-Z] | [0-9] | [$-_@.&+] | [!*(),] | (?:% [0-9a-fA-F][0-9a-fA-F]) )+ )
    """,
    flags=re.VERBOSE | re.IGNORECASE,  # X = VERBOSE, I = IGNORECASE
)


def find_all_links_to_fix(text: str) -> str:
    """
    Find common social links in text.

    Parameters
    ----------
    text: str
        Text to search social links in.

    Returns
    -------
    str
        A list of fixed links joined with line-break.
    """

    # Just a reminder on what groups actually are:
    # text = "https://www.instagram.com/p/DBg0L6foRNW/ bla bla bla https://x.com/IceFrog/status/1718834746300719265"
    # for group in EMBED_FIXER_REGEX_PATTERN.findall(text):
    #     print(group)
    #     return
    # >>> ('https://www.', 'instagram.com', '/p/DBg0L6foRNW/'), e.g. `group[1] = 'instagram.com'`, etc
    return "\n".join(
        [
            group[0].replace("www.", "") + FIX_DICT[group[1].lower().split(".")[0]] + group[2]
            for group in EMBED_FIXER_REGEX_PATTERN.findall(text)
        ]
    )


def subn_links_to_fix(text: str) -> tuple[str, int]:
    """
    Fix common social links by replacing them with links that provide better meta-embeds for Discord UI.

    Parameters
    ----------
    text: str
        Text to search social links in.

    Returns
    -------
    tuple[str, int]
        `re.subn` returns tuple `(new_string, number_of_subs_made)` which can be useful.

    Sources
    ------
    * https://stackoverflow.com/a/15175239/19217368
    """

    # text = "https://www.instagram.com/p/DBg0L6foRNW/ bla bla bla https://x.com/IceFrog/status/1718834746300719265"
    # mo.group(0) is 'https://www.instagram.com/p/DBg0L6foRNW/'
    # mo.group(1) is 'instagram.com'
    # mo.group(2) is '/p/DBg0L6foRNW/'
    # So `.findall` doesn't include `group(0)` into its groups, which makes sense, but might be confusing.
    return EMBED_FIXER_REGEX_PATTERN.subn(
        lambda mo: mo.group(1) + FIX_DICT[mo.group(2).lower().split(".")[0]] + mo.group(3), text
    )


TEST_STRING = """
    * https://www.instagram.com/taylorswift/p/DXrxObojod9/?hl=en - Taylor Swift;
    * https://instagram.com/reel/CsfO_chhPEe/ - Pale Waves;
    * https://x.com/IceFrog/status/1718834746300719265 - IceFrog;
    * https://open.spotify.com/track/42VUCXerQ5qTr4Qp6PhKo4 - Sabrina Carpenter'
"""

if __name__ == "__main__":
    # Just some lazy playground

    result = x = find_all_links_to_fix(TEST_STRING)
    # print(result)  # noqa: T201

    result = x = subn_links_to_fix(TEST_STRING)
    print(result[0])  # noqa: T201
    print(result[1])  # noqa: T201
