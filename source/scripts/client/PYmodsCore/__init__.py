# -*- coding: utf-8 -*-
import BigWorld
import ResMgr
from .config import *
from .utils import *

curCV = ResMgr.openSection('../paths.xml')['Paths'].values()[0].asString
print 'Current PYmodsCore version: 2.8.3 (%(file_compile_date)s)'
delayed = None


def __import_delayed():
    global delayed
    delayed = __import__('delayed', globals=globals(), level=1)  # sorry, dirty hax had to happen


BigWorld.callback(0, __import_delayed)
del __import_delayed
