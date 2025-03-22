"""
Base classes for FPC (Favourite Player + Character notifications) related cogs of the bot.

Currently supported games:
* Dota 2:               ext.dota.fpc
* League of Legends:    ext.lol.fpc
"""

from .models import *
from .notifications import *
from .settings import *
from .storage import *
