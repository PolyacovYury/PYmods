import importlib
import os
import string
import traceback

import ResMgr
from adisp import adisp_process
from constants import IS_DEVELOPMENT
from debug_utils import LOG_DEBUG, LOG_ERROR
from shared_utils import awaitNextFrame, forEach

__file__ = 'scripts/client/gui/mods/__init__.pyc'
_mods = {}
if IS_DEVELOPMENT:
    _MOD_NAME_POSTFIX = '.py'
else:
    _MOD_NAME_POSTFIX = '.pyc'


def init():
    _findValidMODs()


def fini():
    forEach(lambda mod: _callModMethod(mod, 'fini'), _mods.itervalues())
    _mods.clear()


def sendEvent(eventName, *args, **kwargs):
    forEach(lambda mod: _callModMethod(mod, eventName, *args, **kwargs), _mods.itervalues())


def _callModMethod(mod, methodName, *args, **kwargs):
    try:
        return getattr(mod, methodName)(*args, **kwargs)
    except AttributeError:
        pass


def _isValidMOD(scriptName):
    return scriptName.startswith('mod_') and scriptName.endswith(_MOD_NAME_POSTFIX)


def _findValidMODs(path=None, package=None):
    import AsyncModLoader
    from skeletons.gameplay import IGameplayLogic
    from gameplay.machine import BattleReplayMachine
    if isinstance(AsyncModLoader.dependency.instance(IGameplayLogic)._GameplayLogic__machine, BattleReplayMachine):
        _loadMods(path, package)


@adisp_process
def _loadMods(path=None, package=None, view=None):
    _mods.clear()
    path = path or __path__[0]
    package = package or __package__
    modsFolder = ResMgr.openSection(path)
    success = True
    if not modsFolder:
        LOG_ERROR('No mods folder found', __path__)
        return
    modsList = set(filter(_isValidMOD, map(string.lower, modsFolder.keys())))
    modsNum = float(len(modsList))
    for idx, scriptName in enumerate(modsList):
        if view:
            view.setProgress(idx / modsNum)
            yield awaitNextFrame()
        mod = None
        try:
            moduleName = '%s.%s' % (package, scriptName.replace(_MOD_NAME_POSTFIX, ''))
            _mods[moduleName] = mod = importlib.import_module(moduleName)
            LOG_DEBUG('Gui mod found', moduleName, mod)
            getattr(mod, 'init', lambda: None)()
        except Exception:
            success = False
            print 'Could not import gui mod', scriptName
            traceback.print_exc()
            if view:
                view.addError(os.path.basename(mod.__file__) if mod else scriptName)
                yield awaitNextFrame()
    import BigWorld
    if not success:
        BigWorld.callback(0, BigWorld.quit)
    elif view:
        view.setProgress(1)
        yield awaitNextFrame()
        BigWorld.callback(0, view.close)
