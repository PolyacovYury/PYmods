from functools import partial

import ResMgr
import importlib
import os
import string
import traceback
from adisp import adisp_async, adisp_process
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
        method = getattr(mod, methodName)
    except AttributeError:
        return None
    return method(*args, **kwargs)


def _isValidMOD(scriptName):
    return scriptName.startswith('mod_') and scriptName.endswith(_MOD_NAME_POSTFIX)


def _findValidMODs(path=None, package=None):
    import AsyncModLoader
    from skeletons.gameplay import IGameplayLogic
    from gameplay.machine import BattleReplayMachine
    if isinstance(AsyncModLoader.dependency.instance(IGameplayLogic)._GameplayLogic__machine, BattleReplayMachine):
        _loadMods(path, package)


@adisp_process
def _loadMods(path=None, package=None, game_loader=None):
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
    idx = 0
    for idx, scriptName in enumerate(modsList):
        if game_loader:
            game_loader.setProgress(int(50 + 50.0 * idx / modsNum))
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
            if game_loader:
                game_loader.addError(os.path.basename(mod.__file__) if mod else scriptName)
                yield awaitNextFrame()
    import BigWorld
    if game_loader:
        if success:
            game_loader.setProgress(100)
            yield awaitNextFrame()
            BigWorld.callback(0, game_loader.close)
            return
        while idx > 0:
            idx -= 1
            game_loader.setProgress(int(100 * idx / modsNum))
            yield adisp_async(lambda callback: BigWorld.callback(0.025, partial(callback, None)))()
    if not success:
        BigWorld.callback(0, BigWorld.quit)
