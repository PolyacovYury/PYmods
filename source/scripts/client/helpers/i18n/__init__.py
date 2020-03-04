# -*- coding: utf-8 -*-
import importlib
import marshal

import ResMgr
import traceback


def loadOriginalFile():
    filePath = 'scripts/client/helpers/i18n.pyc'
    fileSect = ResMgr.openSection(filePath)
    if fileSect is not None and ResMgr.isFile(filePath):
        originalFile = str(fileSect.asBinary)
        exec marshal.loads(originalFile[8:]) in globals()


loadOriginalFile()
del loadOriginalFile


def loadMods():
    filesList = set(x.lower() for x in ResMgr.openSection('scripts/client/helpers/i18n').keys()
                    if x.endswith('.pyc') and '__init__' not in x)
    filesList = [fileName.replace('.pyc', '') for idx in xrange(2) for fileName in sorted(filesList) if
                 bool(idx) != bool(fileName.startswith('_'))]
    for fileName in filesList:
        print '* Executing: ' + fileName
        try:
            curMod = importlib.import_module('%s.%s' % (__package__, fileName))
            for attr in curMod.i18nHooks:
                oldAttr = attr.replace('i18n_hook_', '')
                if 'i18n_hook_' in attr:
                    setattr(curMod, 'old_' + oldAttr, globals()[oldAttr])
                globals()[oldAttr] = getattr(curMod, attr)
        except StandardError:
            traceback.print_exc()

    def override_backport_text():
        from gui.impl import backport
        backport.text = lambda resId, *a, **k: globals()['makeString'](backport.msgid(resId), *a, **k)

    import BigWorld
    BigWorld.callback(0, override_backport_text)


try:
    loadMods()
finally:
    del loadMods
