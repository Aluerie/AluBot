"""CONFIGURATION VARIABLES.

I just use plain `config.py` file to store the secrets/tokens/passwords/etc for the bot.
Rename this file to `config.py` instead of `config.example.py` and fill the variables with your own secrets.

Notes.
* I use different bot accounts and some different secrets for production and testing versions of the bot.
    This is why there are some differences in variable values for Home PC (Windows) and VPS (Linux)
    which are covered by `if platform.system() == "Linux": condition.
* It's probably not extremely awful practice rather than always be checking for `if bot.test` in the code.
"""
import platform

# /* cSpell:disable */

############################################
#               1. DISCORD                 #
############################################

if platform.system() == "Linux":
    # AluBot - my main bot
    __discord_bot_token = "abcdefghijklmnopqrstuvwxyz_abcdefghijklmnopqrstuvwxyz_abcdefghijklmnopqrstuvwxyz"
else:
    # YenBot - testing bot
    __discord_bot_token = "xyz"

DISCORD_BOT_TOKEN = __discord_bot_token

############################################
#              2. DATABASE                 #
############################################

if platform.system() == "Linux":
    # VPS Machine
    __postgres_url = "postgresql://user:password@host:port/database"
else:
    # Home Computer
    __postgres_url = "postgresql://user:password@host:port/database"

POSTGRES_URL = __postgres_url

############################################
#               3. STEAM                   #
############################################

STEAM_USERNAME = ""
STEAM_PASSWORD = ""

# Steam WEB API Key
STEAM_WEB_API_KEY = ""
# Dota 2 my own Friend ID
DOTA_FRIEND_ID = 123

############################################
#               4. TWITCH                  #
############################################

TWITCH_ACCESS_TOKEN = ""
TWITCH_REFRESH_TOKEN = ""
TWITCH_CLIENT_ID = ""

############################################
#         5. WEBHOOK URL CATALOG           #
############################################

# Error Handler - send tracebacks and error pings into a proper channel;
ERROR_HANDLER_WEBHOOK = "https://discord.com/api/webhooks/1234567/ABCDEFG"
# Spam Messages - just miscallenous messages, can be anything;
SPAM_WEBHOOK = "https://discord.com/api/webhooks/1234567/ABCDEFG"
# Logger - send `log.info`, `log.warning`, `log.error` into #🐬logger;
LOGGER_WEBHOOK = "https://discord.com/api/webhooks/1234567/ABCDEFG"
# Dota 2 News Webhook - send Dota 2 news to #🍋dota2_news (or to #🍷test_spam when testing)
DOTA_NEWS_WEBHOOK = "https://discord.com/api/webhooks/1234567/ABCDEFG"

############################################
#             6. OTHER SERVICES            #
############################################

# Stratz
STRATZ_BEARER_TOKEN = ""
# Wolfram # 2000 /month
WOLFRAM_TOKEN = ""
# Git Personal Token
GIT_PERSONAL_TOKEN = ""
# Riot API Key
RIOT_API_KEY = ""

# /* cSpell:enable */
