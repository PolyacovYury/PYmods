import BigWorld
from .api import *
from .utils import *

patreon = None


def __import_delayed():
    global patreon
    patreon = __import__('patreon', globals=globals(), level=1)  # sorry, dirty hax had to happen


BigWorld.callback(0, __import_delayed)
del __import_delayed
