from utils.mybot import MyBot

from os import getenv
from dotenv import load_dotenv
load_dotenv(dotenv_path='env.env', verbose=True)

import argparse
parser = argparse.ArgumentParser(description="Irene Adler's personal bot, Violet or Yennifer (testing version)")
parser.add_argument('-n', '--name', help='Bot name, can only be "yen" or "vio"', required=True)
args = parser.parse_args()

from utils import custom_logger
import logging
log = logging.getLogger('root')
log.setLevel('INFO')

match args.name:
    case 'vio':
        token = getenv("DISCORD_BOT_TOKEN")
        from cogs.settings import get_pre
        prefix = get_pre
        yen = False
        log.addHandler(custom_logger.MyHandler(trail=False))
    case 'yen':
        token = getenv("DISCORD_YEN_TOKEN")
        prefix = '~'
        yen = True
        log.addHandler(custom_logger.MyHandler(trail=True))
    case _:
        raise Exception('Only names `vio` and `yen` are available')

bot = MyBot(prefix, yen)
bot.run(token)
