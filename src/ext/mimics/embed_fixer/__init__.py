"""
Embed Fixer.

This module aims to solve a common problem with social media websites, where
if a person shares a link from those social medias (i.e. an instagram reel, tweet, reddit post, spotify track) -
the resulting meta-embed in Discord app is so bad and uninformative that other people either
have to click the link to actually see what it's about or ignore.
Both results are bad.

And here comes this module which will try to solve this problem by replacing people's messages with mimics
and using better embed services.

Similar projects
----------------
* https://github.com/seriaati/embed-fixer
* https://betterdiscord.app/plugin/SocialMediaLinkConverter (Now deleted)

License
-------
* This Source Code Form is subject to the terms of the [Mozilla Public License v2.0](<http://mozilla.org/MPL/2.0/>).
* Copyright (C) 2020-present [Aluerie](<https://github.com/Aluerie>).
"""

from .cog import *
