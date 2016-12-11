# -*- coding: utf-8 -*-
import os
import traceback


def loadOriginalFile():
    import os
    import marshal
    originalFilePath = 'res/' + __file__
    if os.path.exists(originalFilePath) and os.path.isfile(originalFilePath):
        with open(originalFilePath, 'rb') as originalFile:
            exec marshal.loads(originalFile.read()[8:]) in globals()


loadOriginalFile()
del loadOriginalFile


def loadMods():
    import ResMgr
    import glob
    pathFile = ResMgr.openSection('../paths.xml')
    pathVersions = pathFile['Paths']
    currentPatchVersion = pathVersions.values()[0:1]
    for path in currentPatchVersion:
        modFile = path.asString + '/scripts/client/mods/*.pyc'
        for modFilePath in glob.iglob(modFile):
            fullPathSplitted = os.path.basename(modFilePath)
            pythonImportName = fullPathSplitted.split('.')[0]
            if pythonImportName != '__init__':
                print '* Executing: ' + pythonImportName
                try:
                    exec 'import mods.' + pythonImportName
                except StandardError:
                    traceback.print_exc()


loadMods()
