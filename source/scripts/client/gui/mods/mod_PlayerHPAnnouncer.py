# -*- coding: utf-8 -*-
import BattleReplay
import BigWorld
import PYmodsCore
import SoundGroups
from Avatar import PlayerAvatar
from bootcamp import BootcampSettings
from bootcamp.Assistant import BaseAssistant
from bootcamp.Bootcamp import g_bootcamp
from bootcamp.BootcampReplayController import BootcampReplayController
from bootcamp.hints.HintsScenario import HintLowHP
from bootcamp.hints.HintsSystem import HintSystem
from gui.Scaleform.daapi.view.meta import DamagePanelMeta


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


_config = _Config()
_config.load()
statistic_mod = PYmodsCore.Analytics(_config.ID, _config.version.split(' ', 1)[0], 'UA-76792179-12')


@PYmodsCore.overrideMethod(PlayerAvatar, '_PlayerAvatar__startGUI')
def new_startGUI(base, self):
    base(self)
    _config.currentPercent = 100
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
