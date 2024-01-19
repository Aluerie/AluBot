"""Config variables file

* Rename this file from `config.example.py` to `config.py`
* Fill out the variables below.
"""

# /* cSpell:disable */

# DISCORD (AluBot)
MAIN_TOKEN = ""  # your bot's token

# DISCORD (YenBot)
TEST_TOKEN = ""

# STEAM (MAIN BOT ACCOUNT)
# I have not yet implemented getting SteamGuard codes with super-secret thing
# So both main and test accounts should be without 2FA from SteamGuard (no email, no mobile codes).
# well, any empty new account with 0$ wallet works.
# For Game coordinator features add it to friends from your actual gaming steam account
STEAM_MAIN_LGN = ""
STEAM_MAIN_PSW = ""

# STEAM (TEST BOT'S ACCOUNT)
STEAM_TEST_LGN = ""
STEAM_TEST_PSW = ""

# STEAM API KEY
STEAM_WEB_API_KEY = ""

# DOTA 2
DOTA_FRIEND_ID = 123_456_789

# GIT PERSONAL TOKEN
GIT_PERSONAL_TOKEN = ""

# RIOT
RIOT_API_KEY = ""

# TWITCH # https://twitchtokengenerator.com/ for TOKEN
TWITCH_TOKEN = ""

# POSTGRES DATABASE
POSTGRES_URL = "postgresql://user:password@host:port/database"

# WOLFRAM # 2000 requests /month
WOLFRAM_TOKEN = ""

# ERROR HANDLER WEBHOOK URL
ERROR_HANDLER_WEBHOOK_URL = "https://discord.com/api/webhooks/something"

# TEST BOT'S ERROR HANDLER WEBHOOK URL
TEST_ERROR_HANDLER_WEBHOOK_URL = "https://discord.com/api/webhooks/something"

# BOT CONSOLE LOGGER SPAM WEEBHOOK URL
SPAM_LOGS_WEBHOOK_URL = "https://discord.com/api/webhooks/something"

# STRATZ
STRATZ_BEARER_TOKEN = ""

# /* cSpell:enable */
