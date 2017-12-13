# -*- coding: utf-8 -*-
import BigWorld
import ResMgr
from .config import *
from .events import *
from .utils import *

res = ResMgr.openSection('../paths.xml')
sb = res['Paths']
vl = sb.values()[0]
if vl is not None and not hasattr(BigWorld, 'curCV'):
    BigWorld.curCV = vl.asString
if not hasattr(BigWorld, 'PMC_wasPrint'):
    BigWorld.PMC_wasPrint = True
    print 'Current PYmodsCore version: 2.4.0.2 (%(file_compile_date)s)'
