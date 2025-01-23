"""CONFIGURATION VARIABLES.

I just use plain `config.py` file to store the secrets/tokens/passwords/etc for the bot.
Rename this file to `config.py` instead of `config.example.py` and fill the variables with your own secrets.

Notes.
* I use different bot accounts and some different secrets for production and testing versions of the bot.
    This is why there are some differences in variable values for Home PC (Windows) and VPS (Linux)
    which are covered by `if platform.system() == "Linux": condition.
* I have type-hints ": str" for the purpose to be safer when streaming VSCode window -
    this way if we hover over `config.TTG_ACCESS_TOKEN` in other files
    it will show type str instead of Literal["my actual token"]
"""

# ruff: noqa: S105 # This file is included in `.gitignore`

import platform

__all__ = (
    "DISCORD_BOT_TOKEN",
    "DOTA_FRIEND_ID",
    "DOTA_NEWS_WEBHOOK",
    "ERROR_PING",
    "ERROR_WEBHOOK",
    "GIT_PERSONAL_TOKEN",
    "LOGGER_WEBHOOK",
    "POSTGRES_URL",
    "RIOT_API_KEY",
    "SPAM_WEBHOOK",
    "STEAM_PASSWORD",
    "STEAM_USERNAME",
    "STEAM_WEB_API_KEY",
    "STRATZ_BEARER_TOKEN",
    "TTV_DEV_CLIENT_ID",
    "TTV_DEV_CLIENT_SECRET",
    "WOLFRAM_TOKEN",
)

# /* cSpell:disable */

############################################
#               1. DISCORD                 #
############################################

if platform.system() == "Linux":
    # AluBot - my main bot
    __discord_bot_token: str = "abcdefghijklmnopqrstuvwxyz_abcdefghijklmnopqrstuvwxyz_abcdefghijklmnopqrstuvwxyz"
else:
    # YenBot - testing bot
    __discord_bot_token: str = "xyz"

DISCORD_BOT_TOKEN: str = __discord_bot_token

############################################
#              2. DATABASE                 #
############################################

if platform.system() == "Linux":
    # VPS Machine
    __postgres_url: str = "postgresql://user:password@host:port/database"
else:
    # Home Computer
    __postgres_url: str = "postgresql://user:password@host:port/database"

POSTGRES_URL: str = __postgres_url

############################################
#               3. STEAM                   #
############################################

STEAM_USERNAME: str = ""
STEAM_PASSWORD: str = ""

# Steam WEB API Key
STEAM_WEB_API_KEY: str = ""
# Dota 2 Aluerie's Friend ID
DOTA_FRIEND_ID: int = 123

############################################
#               4. TWITCH                  #
############################################

TTV_DEV_CLIENT_ID: str = ""
TTV_DEV_CLIENT_SECRET: str = ""

############################################
#         5. WEBHOOK URL CATALOG           #
############################################

# Error Handler - send tracebacks and error pings into a proper channel;
ERROR_WEBHOOK: str = "https://discord.com/api/webhooks/1234567/ABCDEFG"
# Spam Messages - just miscallenous messages, can be anything;
SPAM_WEBHOOK: str = "https://discord.com/api/webhooks/1234567/ABCDEFG"
# Logger - send `log.info`, `log.warning`, `log.error` into #🐬logger;
LOGGER_WEBHOOK: str = "https://discord.com/api/webhooks/1234567/ABCDEFG"
# Dota 2 News Webhook - send Dota 2 news to #🍋dota2_news (or to #🍷test_spam when testing)
DOTA_NEWS_WEBHOOK: str = "https://discord.com/api/webhooks/1234567/ABCDEFG"
# Ping Aluerie with this
ERROR_PING: str = "<@&1234>"

############################################
#             6. OTHER SERVICES            #
############################################

# Stratz
STRATZ_BEARER_TOKEN: str = ""
# Wolfram # 2000 /month
WOLFRAM_TOKEN: str = ""
# Git Personal Token
GIT_PERSONAL_TOKEN: str = ""
# Riot API Key
RIOT_API_KEY: str = ""

# /* cSpell:enable */
