import weakref

import BigWorld
import GUI
from frameworks.state_machine import State, ConditionTransition
from gameplay.delegator import GameplayLogic
from gameplay.machine import BattleReplayMachine
from gui.Scaleform.daapi.view.external_components import ExternalFlashComponent, ExternalFlashSettings
from gui.Scaleform.daapi.view.meta.GameLoadingMeta import GameLoadingMeta
from gui.Scaleform.genConsts.ROOT_SWF_CONSTANTS import ROOT_SWF_CONSTANTS
from gui.app_loader.observers import AppLoaderObserver
from gui.app_loader.settings import APP_NAME_SPACE
from gui.shared.personality import ServicesLocator as SL
from gui.shared.utils import graphics
from gui.shared.utils.decorators import ReprInjector
from helpers import getFullClientVersion, getClientOverride, uniprof, dependency
from skeletons.gameplay import IGameplayLogic
from skeletons.gui.app_loader import IGlobalSpace, ApplicationStateID


class _const:
    stateID = 'async.game_loading'
    finished = 'async.game_loading.finished'
    alias = 'AsyncModLoader'


def _new_start(self):
    machine = self._GameplayLogic__machine
    self._GameplayLogic__adaptor.startListening()
    machine.configure()
    if isinstance(machine, BattleReplayMachine):  # sadly, impossible. zero clue why.
        return machine.start()
    start_state = machine.getChildByIndex(0)
    loading = start_state.loading
    async_loading = State(stateID=_const.stateID)
    for transition in loading.getTransitions():
        targets = transition.getTargets()
        if isinstance(transition, ConditionTransition):
            condition = transition._ConditionTransition__condition
        loading.removeTransition(transition)
        async_loading.addTransition(transition)
        if isinstance(transition, ConditionTransition):
            # noinspection PyUnboundLocalVariable,PyDunderSlots,PyUnresolvedReferences
            transition._ConditionTransition__condition = condition
        for target in targets:
            transition.setTarget(target)
    loading.addTransition(ConditionTransition(lambda _: True), target=async_loading)
    start_state.addChildState(async_loading)
    machine.connect(_AsyncLoaderObserver(_const.stateID, weakref.proxy(SL.appLoader)))
    machine.start()


GameplayLogic.start = _new_start


@ReprInjector.simple()
class _AsyncLoaderSpace(IGlobalSpace):
    __slots__ = ()

    def getSpaceID(self):
        return 8

    def showGUI(self, appFactory, appNS, appState):
        if appState != ApplicationStateID.INITIALIZING or appNS != APP_NAME_SPACE.SF_LOBBY:
            return
        loader = _AsyncLoaderView()
        loader.active(True)
        # noinspection PyUnresolvedReferences
        from gui.mods import _loadMods
        _loadMods(view=loader)


class _AsyncLoaderObserver(AppLoaderObserver):
    __slots__ = ()

    def onEnterState(self, event=None):
        self._proxy.changeSpace(_AsyncLoaderSpace())


class _AsyncLoaderView(ExternalFlashComponent, GameLoadingMeta):
    gameplay = dependency.descriptor(IGameplayLogic)

    def __init__(self):
        self.__errorFiles = []
        super(_AsyncLoaderView, self).__init__(ExternalFlashSettings(
            'gameLoading', 'gameLoadingApp.swf', 'root.main', ROOT_SWF_CONSTANTS.GAME_LOADING_REGISTER_CALLBACK))
        self.createExternalComponent()

    @uniprof.regionDecorator(label=_const.stateID, scope='enter')
    def afterCreate(self):
        super(_AsyncLoaderView, self).afterCreate()
        self.as_setLocaleS(getClientOverride())
        self.as_setVersionS(getFullClientVersion())
        self.as_setInfoS('')
        self.as_setProgressS(0)
        self._updateStage()
        from gui import g_guiResetters
        g_guiResetters.add(self._updateStage)

    @uniprof.regionDecorator(label=_const.stateID, scope='exit')
    def _dispose(self):
        from gui import g_guiResetters
        g_guiResetters.discard(self._updateStage)
        BigWorld.callback(0, self.gameplay.tick)
        super(_AsyncLoaderView, self)._dispose()

    def setProgress(self, progress):
        self.as_setProgressS(progress)

    def addError(self, fileName):
        self.__errorFiles.append(fileName)
        self.as_setInfoS('<br>'.join(
            "<font face='$FieldFont' color='#DD7700' size='16'>Mod import failed: %s</font>" % x for x in self.__errorFiles))

    def _updateStage(self):
        width, height = GUI.screenResolution()
        scaleLength = len(graphics.getInterfaceScalesList([width, height]))
        self.as_updateStageS(width, height, scaleLength - 1)
