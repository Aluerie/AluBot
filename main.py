from utils.bot import AluBot, LogHandler

from os import getenv
from dotenv import load_dotenv
load_dotenv(dotenv_path='env.env', verbose=True)

import argparse
parser = argparse.ArgumentParser(description="Aluerie's personal bot, Alu or Yen (testing version)")
parser.add_argument('-n', '--name', help='Bot name, can only be "alu" or "yen"', required=True)
args = parser.parse_args()

import logging
log = logging.getLogger('root')
log.setLevel('INFO')

match args.name:
    case 'alu':
        token = getenv("DISCORD_BOT_TOKEN")
        from cogs.settings import get_pre
        prefix = get_pre
        yen = False
        log.addHandler(LogHandler(papertrail=False))
    case 'yen':
        token = getenv("DISCORD_YEN_TOKEN")
        prefix = '~'
        yen = True
        log.addHandler(LogHandler(papertrail=True))
    case _:
        raise Exception('Only names `alu` and `yen` are available')

bot = AluBot(prefix, yen)
bot.run(token)
