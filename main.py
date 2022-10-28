import argparse
import logging

from config import DISCORD_BOT_TOKEN, DISCORD_YEN_TOKEN
from cogs.utils.bot import AluBot, LogHandler

parser = argparse.ArgumentParser(description="Aluerie's personal bot, Alu or Yen (testing version)")
parser.add_argument('-n', '--name', help='Bot name, can only be "alu" or "yen"', required=True)
args = parser.parse_args()

log = logging.getLogger('root')
log.setLevel('INFO')

match args.name:
    case 'alu':
        token = DISCORD_BOT_TOKEN
        yen = False
        log.addHandler(LogHandler(papertrail=True))
    case 'yen':
        token = DISCORD_YEN_TOKEN
        yen = True
        log.addHandler(LogHandler(papertrail=False))
    case _:
        raise Exception('Only names `alu` and `yen` are allowed')

bot = AluBot(yen)
bot.run(token)
