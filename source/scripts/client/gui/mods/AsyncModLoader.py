import game_loading_bindings

import BigWorld
import re
import weakref
from frameworks.state_machine import State, StateFlags, StringEventTransition
from functools import partial
from gameplay.machine import GameplayStateMachine
from gui.app_loader.observers import AppLoaderObserver
from gui.app_loader.settings import APP_NAME_SPACE
from gui.game_loading.loading import getLoader
from gui.game_loading.resources.cdn.models import LocalSlideModel
from gui.shared.personality import ServicesLocator as SL
from gui.shared.utils.decorators import ReprInjector
from helpers import dependency
from skeletons.gameplay import IGameplayLogic
from skeletons.gui.app_loader import IGlobalSpace


class _const:
    stateID = 'async.game_loading'
    done = 'async.game_loading.done'


def _new_configure_gameplay(machine):
    _old_configure_gameplay(machine)
    async_loading = State(stateID=_const.stateID, flags=StateFlags.INITIAL)
    offline_state = SL.gameplay._GameplayLogic__machine.offline
    offline_state.login._State__flags = StateFlags.UNDEFINED
    async_loading.addTransition(StringEventTransition(_const.done), target=offline_state.login)
    offline_state.addChildState(async_loading)
    machine.connect(_AsyncLoaderObserver(_const.stateID, weakref.proxy(SL.appLoader)))


def _new_configure_game_loading(machine):
    playerLoadingState = machine.getChildByIndex(3)
    playerLoadingProgressMixinState = playerLoadingState.getChildByIndex(1)
    playerLoadingProgressMixinState._settings.startPercent = 0
    playerLoadingProgressMixinState._setInitialProgress()


@ReprInjector.simple()
class _AsyncLoaderSpace(IGlobalSpace):
    __slots__ = ()

    def getSpaceID(self):
        return 8

    def showGUI(self, appFactory, appNS, appState):
        if appNS != APP_NAME_SPACE.SF_LOBBY:
            return
        loader = _AsyncLoaderTracker()
        # noinspection PyUnresolvedReferences
        from gui.mods import _loadMods
        _loadMods(game_loader=loader)


class _AsyncLoaderObserver(AppLoaderObserver):
    __slots__ = ()

    def onEnterState(self, event=None):
        self._proxy.changeSpace(_AsyncLoaderSpace())


class _AsyncLoaderTracker:
    gameplay = dependency.descriptor(IGameplayLogic)

    def __init__(self):
        self.__errorFiles = []
        from helpers.i18n import makeString
        self._status_user_string = re.sub(r'<[^>]+>', '', makeString(
            '#system_messages:vehiclePostProgression/buyPairModification/title'))
        game_loading_bindings.setStatusText(self._status_user_string)

    def setProgress(self, progress):
        game_loading_bindings.setProgress(progress, 100)

    def addError(self, fileName):
        self.__errorFiles.append(fileName)
        slide_state = getLoader().getChildByIndex(1).mainState
        slide_state._image = LocalSlideModel(
            slide_state.lastShownImage.imageRelativePath, slide_state.lastShownImage.vfx,
            "Mod%s import failed:" % (('s' if len(self.__errorFiles) > 1 else ''),), ', '.join(map(str, self.__errorFiles)),
            slide_state.lastShownImage.minShowTimeSec, slide_state.lastShownImage.transition)
        slide_state._view(slide_state.lastShownImage)

    def close(self):
        BigWorld.callback(0, partial(self.gameplay.postStateEvent, _const.done))


_old_configure_gameplay = GameplayStateMachine.configure
GameplayStateMachine.configure = _new_configure_gameplay
_new_configure_game_loading(getLoader())
