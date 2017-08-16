# -*- coding: utf-8 -*-
import BattleReplay
import BigWorld
import PYmodsCore
import SoundGroups
from Avatar import PlayerAvatar
from bootcamp import BootcampSettings
from bootcamp.Assistant import BaseAssistant
from bootcamp.Bootcamp import g_bootcamp
from bootcamp.BootcampLobbyHintsConfig import g_bootcampHintsConfig
from bootcamp.BootcampReplayController import BootcampReplayController
from bootcamp.hints.HintsScenario import HintLowHP
from bootcamp.hints.HintsSystem import HintSystem as _HintSystem
from constants import ARENA_GUI_TYPE, HINT_NAMES, HINT_TYPE
from debug_utils_bootcamp import LOG_CURRENT_EXCEPTION_BOOTCAMP
from gui.Scaleform.daapi.settings.views import VIEW_ALIAS
from gui.Scaleform.daapi.view.bootcamp.BCHighlights import BCHighlights
from gui.Scaleform.daapi.view.bootcamp.BCSecondaryHint import BCSecondaryHint
from gui.Scaleform.daapi.view.meta import DamagePanelMeta
from gui.Scaleform.framework import ScopeTemplates, ViewSettings, ViewTypes, g_entitiesFactories
from gui.Scaleform.framework.managers.containers import POP_UP_CRITERIA
from gui.Scaleform.framework.managers.loaders import ViewLoadParams
from gui.Scaleform.genConsts.BATTLE_VIEW_ALIASES import BATTLE_VIEW_ALIASES
from gui.app_loader import g_appLoader
from gui.shared import EVENT_BUS_SCOPE, events, g_eventBus
from gui.shared.events import BootcampEvent


class _Config(PYmodsCore.Config):
    def __init__(self):
        super(self.__class__, self).__init__('%(mod_ID)s')
        self.version = '1.0.1 (%(file_compile_date)s)'
        self.data = {'10percent': 'percent_10',
                     '25percent': 'percent_25',
                     '50percent': 'percent_50'}
        self.currentPercent = None
        self.assistant = None

    def updateMod(self):
        pass

    def do_config_delayed(self):
        pass


class HintSystem(_HintSystem):
    def __init__(self, avatar=None, hintsInfo=None):
        if hintsInfo is None:
            hintsInfo = {}
        super(self.__class__, self).__init__(avatar, hintsInfo)
        replayPlaying = BattleReplay.g_replayCtrl.isPlaying
        replaySafeHints = (HINT_TYPE.HINT_MESSAGE_AVOID, HINT_TYPE.HINT_LOW_HP)
        for hintName, hintParams in hintsInfo.iteritems():
            try:
                if hintName != 'hintLowHP':
                    continue
                hintTypeId = HINT_NAMES.index(hintName)
                if hintTypeId in HINT_TYPE.BATTLE_HINTS:
                    if replayPlaying and hintTypeId not in replaySafeHints:
                        continue
                    cls = HintSystem.hintsBattleClasses.get(hintTypeId, None)
                    if cls is None:
                        raise Exception('Hint not implemented (%s)' % HINT_NAMES[hintTypeId])
                    hint = cls(avatar, hintParams)
                else:
                    cls = HintSystem.hintsLobbyClasses.get(hintTypeId, None)
                    if cls is None:
                        raise Exception('Hint not implemented (%s)' % HINT_NAMES[hintTypeId])
                    hint = cls(hintParams)
                timeCompleted = hintParams.get('time_completed', 2.0)
                cooldownAfter = hintParams.get('cooldown_after', 2.0)
                voiceover = hintParams.get('voiceover', None)
                message = hintParams.get('message', 'Default Message')
                hint.timeCompleted = timeCompleted
                hint.cooldownAfter = cooldownAfter
                hint.message = message
                if voiceover is not None:
                    hint.voiceover = voiceover
                self.addHint(hint)
            except StandardError:
                LOG_CURRENT_EXCEPTION_BOOTCAMP()


_config = _Config()
_config.load()
statistic_mod = PYmodsCore.Analytics(_config.ID, _config.version.split(' ', 1)[0], 'UA-76792179-12')


def loadViewByCtxEvent(event):
    g_appLoader.getDefBattleApp().loadView(ViewLoadParams(event.eventType, event.name), event.ctx)


def onHighlightHint(event):
    manager = g_appLoader.getDefBattleApp().containerManager
    if manager is not None:
        container = manager.getContainer(ViewTypes.WINDOW)
        if container is not None:
            hintWindow = container.getView(criteria={POP_UP_CRITERIA.VIEW_ALIAS: VIEW_ALIAS.BOOTCAMP_BATTLE_HIGHLIGHTS})
            if hintWindow is not None:
                hintWindow.showHint(event.ctx)


def onRemoveHighlight(event):
    manager = g_appLoader.getDefBattleApp().containerManager
    if manager is not None:
        container = manager.getContainer(ViewTypes.WINDOW)
        if container is not None:
            hintWindow = container.getView(criteria={POP_UP_CRITERIA.VIEW_ALIAS: VIEW_ALIAS.BOOTCAMP_BATTLE_HIGHLIGHTS})
            if hintWindow is not None:
                hintWindow.hideHint(event.ctx)


def onRemoveAllHighlights(event):
    manager = g_appLoader.getDefBattleApp().containerManager
    if manager is not None:
        container = manager.getContainer(ViewTypes.WINDOW)
        if container is not None:
            hintWindow = container.getView(criteria={POP_UP_CRITERIA.VIEW_ALIAS: VIEW_ALIAS.BOOTCAMP_BATTLE_HIGHLIGHTS})
            if hintWindow is not None:
                hintWindow.hideAllHints()


@PYmodsCore.overrideMethod(PlayerAvatar, '_PlayerAvatar__startGUI')
def new_startGUI(base, self):
    base(self)
    _config.currentPercent = 100
    if self.arena.guiType != ARENA_GUI_TYPE.BOOTCAMP:
        g_entitiesFactories.initSettings(
            (ViewSettings(BATTLE_VIEW_ALIASES.BOOTCAMP_SECONDARY_HINT, BCSecondaryHint,
                          None, ViewTypes.COMPONENT, None, ScopeTemplates.DEFAULT_SCOPE),
             ViewSettings(VIEW_ALIAS.BOOTCAMP_BATTLE_HIGHLIGHTS, BCHighlights,
                          'BCHighlights.swf', ViewTypes.WINDOW, None, ScopeTemplates.DEFAULT_SCOPE)))
        for eventType, listener in ((VIEW_ALIAS.BOOTCAMP_BATTLE_HIGHLIGHTS, loadViewByCtxEvent),
                                    (BootcampEvent.ADD_HIGHLIGHT, onHighlightHint),
                                    (BootcampEvent.REMOVE_HIGHLIGHT, onRemoveHighlight),
                                    (BootcampEvent.REMOVE_ALL_HIGHLIGHTS, onRemoveAllHighlights)):
            g_eventBus.addListener(eventType, listener, EVENT_BUS_SCOPE.BATTLE)
        # g_appLoader.getDefBattleApp().loadView(ViewLoadParams(BATTLE_VIEW_ALIASES.BOOTCAMP_SECONDARY_HINT))
        g_eventBus.handleEvent(events.LoadViewEvent(
            VIEW_ALIAS.BOOTCAMP_BATTLE_HIGHLIGHTS, None,
            {'descriptors': {'DamagePanelHealthbar': {'viewAlias': VIEW_ALIAS.CLASSIC_BATTLE_PAGE,
                                                      'path': 'damagePanel.healthBar'}}}))
    if BattleReplay.g_replayCtrl.isPlaying and g_bootcamp._Bootcamp__replayController is None:
        g_bootcamp._Bootcamp__replayController = BootcampReplayController()
        g_bootcamp._Bootcamp__replayController.init()
    _config.assistant = BaseAssistant(
        HintSystem(BigWorld.player(), {'hintLowHP': BootcampSettings.getBattleDefaults()['hints']['hintLowHP']}))
    _config.assistant.start()


@PYmodsCore.overrideMethod(PlayerAvatar, '_PlayerAvatar__destroyGUI')
def new_destroyGUI(base, self):
    base(self)
    _config.assistant.stop()
    _config.assistant = None
    if self.arena.guiType != ARENA_GUI_TYPE.BOOTCAMP:
        for eventType, listener in ((VIEW_ALIAS.BOOTCAMP_BATTLE_HIGHLIGHTS, loadViewByCtxEvent),
                                    (BootcampEvent.ADD_HIGHLIGHT, onHighlightHint),
                                    (BootcampEvent.REMOVE_HIGHLIGHT, onRemoveHighlight),
                                    (BootcampEvent.REMOVE_ALL_HIGHLIGHTS, onRemoveAllHighlights)):
            g_eventBus.removeListener(eventType, listener, EVENT_BUS_SCOPE.BATTLE)
    _config.currentPercent = None


@PYmodsCore.overrideMethod(DamagePanelMeta.DamagePanelMeta, 'as_updateHealthS')
def new_updateHealth(base, self, healthStr, progress):
    base(self, healthStr, progress)
    if _config.currentPercent is None:
        return
    for percentage in (10, 25, 50):
        if not progress:
            break
        if progress <= percentage < _config.currentPercent:
            SoundGroups.g_instance.playSound2D(_config.data['%spercent' % percentage])
            break
    _config.currentPercent = progress


@PYmodsCore.overrideMethod(HintLowHP, '_HintLowHP__setHealthValues')
def new_setHealthValues(base, self, vehicle, *args):
    base(self, vehicle, *args)
    self._HintLowHP__isFirstWarningAppeared = False
    self._HintLowHP__isSecondWarningAppeared = False
