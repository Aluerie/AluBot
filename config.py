"""
For heroku reasons I need to have `config.py` via `.env` environmental variables

I promise I will do everything properly when I'm not broke. :(
"""

import platform
from os import getenv

if platform.system() == 'Windows':
    from dotenv import load_dotenv, find_dotenv

    load_dotenv(dotenv_path=find_dotenv(), verbose=True)

# DISCORD
DISCORD_BOT_TOKEN = getenv("DISCORD_BOT_TOKEN")
DISCORD_YEN_TOKEN = getenv("DISCORD_YEN_TOKEN")
DISCORD_BOT_INVLINK = getenv("DISCORD_BOT_INVLINK")

# STEAM (AluBot account)
STEAM_LGN = getenv("STEAM_LGN")
STEAM_PSW = getenv("STEAM_PSW")

STEAM_API_KEY = getenv("STEAM_API_KEY")

# TEST STEAM (YenBot account)
STEAM_TEST_LGN = getenv("STEAM_TEST_LGN")
STEAM_TEST_PSW = getenv("STEAM_TEST_PSW")

# MY STEAM
STEAM_MY_LGN = getenv("STEAM_MY_LGN")
STEAM_MY_PSW = getenv("STEAM_MY_PSW")

# DOTA 2
DOTA_STEAMID = getenv("DOTA_STEAMID")
DOTA_FRIENDID = getenv("DOTA_FRIENDID")

# LEAGUE OF LEGENDS
LOL_ID = getenv("LOL_ID")
LOL_REGION = getenv("LOL_REGION")
LOL_ACCNAME = getenv("LOL_ACCNAME")

# GIT KEY
GIT_KEY = getenv("GIT_KEY")
GIT_PERSONAL_TOKEN = getenv("GIT_PERSONAL_TOKEN")
GIT_LGN = getenv("GIT_LGN")
GIT_PSW = getenv("GIT_PSW")

# RIOT
RIOT_API_KEY = getenv("RIOT_API_KEY")

# TWITCH
TWITCH_NAME = getenv("TWITCH_NAME")
TWITCH_CLIENT_ID = getenv("TWITCH_CLIENT_ID")
TWITCH_CLIENT_SECRET = getenv("TWITCH_CLIENT_SECRET")
WEBHOOK_DISCORD_CHANNEL = getenv("WEBHOOK_DISCORD_CHANNEL")

# DATABASE
DATABASE_URL = getenv("DATABASE_URL")
SQL_URL = getenv("SQL_URL")

# WOLFRAM
WOLFRAM_TOKEN = getenv("WOLFRAM_TOKEN")

# REDDIT
REDDIT_CLIENT_ID = getenv("REDDIT_CLIENT_ID")
REDDIT_CLIENT_SECRET = getenv("REDDIT_CLIENT_SECRET")
REDDIT_PASSWORD = getenv("REDDIT_PASSWORD")
REDDIT_USER_AGENT = getenv("REDDIT_USER_AGENT")
REDDIT_USERNAME = getenv("REDDIT_USERNAME")

# DETECTLANGUAGE.COM
DETECTLANGUAGE_API_KEY = getenv("DETECTLANGUAGE_API_KEY")

# TWITTER
TWITTER_CONSUMER_KEY = getenv("TWITTER_CONSUMER_KEY")  # not used in API V2 ?
TWITTER_CONSUMER_SECRET = getenv("TWITTER_CONSUMER_SECRET")  # not used in API V2 ?
TWITTER_ACCESS_TOKEN = getenv("TWITTER_ACCESS_TOKEN")  # not used in API V2 ?
TWITTER_ACCESS_TOKEN_SECRET = getenv("TWITTER_ACCESS_TOKEN_SECRET")  # not used in API V2 ?
TWITTER_BEARER_TOKEN = getenv("TWITTER_BEARER_TOKEN")
