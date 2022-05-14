from steam.client import SteamClient
from dota2.client import Dota2Client

import logging
log = logging.getLogger('root')


def sd_login(steam, dota, lgn, psw):
    if steam.connected is False:
        log.info(f"dota2info: client.connected {steam.connected}")
        if steam.login(username=lgn, password=psw):
            steam.change_status(persona_state=7)
            log.info('We successfully logged invis mode into Steam')
            dota.launch()
        else:
            log.info('Logging into Steam failed')
            return
