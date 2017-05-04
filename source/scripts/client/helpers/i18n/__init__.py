# -*- coding: utf-8 -*-
import marshal
import os
import os.path
import traceback
import zipfile

import ResMgr


def loadOriginalFile():
    filePath = 'scripts/client/helpers/i18n.pyc'
    fileSect = ResMgr.openSection(filePath)
    if fileSect is not None and ResMgr.isFile(filePath):
        originalFile = str(fileSect.asBinary)
        exec marshal.loads(originalFile[8:]) in globals()


loadOriginalFile()
del loadOriginalFile

filesList = [x for x in ResMgr.openSection('scripts/client/helpers/i18n').keys()
             if x.endswith('.pyc') and '__init__' not in x]
filesList = [fileName.replace('.pyc', '') for idx in xrange(2) for fileName in sorted(filesList) if
             bool(idx) != bool('_' in fileName)]
for fileName in filesList:
    print '* Executing: ' + fileName
    try:
        exec 'from helpers.i18n import ' + fileName
        attrsList = globals()[fileName].__dir__()
        for attr in attrsList:
            oldAttr = attr.replace('i18n_hook_', '')
            if 'i18n_hook_' in attr:
                setattr(globals()[fileName], 'old_' + oldAttr, globals()[oldAttr])
            globals()[oldAttr] = getattr(globals()[fileName], attr)
    except StandardError:
        traceback.print_exc()
