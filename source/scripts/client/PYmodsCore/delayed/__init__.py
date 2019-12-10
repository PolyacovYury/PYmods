import BigWorld
from .api import *
from .utils import *

support = None


def __import_delayed():
    global support
    support = __import__('support', globals=globals(), level=1)  # sorry, dirty hax had to happen


BigWorld.callback(0, __import_delayed)
del __import_delayed
