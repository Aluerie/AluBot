from . import const as const
from .bases import *

# just a weird desire to be able to 
# from utils import AluBot in if TYPE_CHECKING:
# which won't work due to circular import 
# if the lines above go below the following one
from bot import *  # isort:skip
