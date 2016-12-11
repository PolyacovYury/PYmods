# -*- coding: utf-8 -*-
import traceback

import BigWorld
import ResMgr

import PYmodsCore
from gui.Scaleform.daapi.view.battle.shared.ribbons_panel import BattleRibbonsPanel
from gui.Scaleform.daapi.view.lobby.LobbyView import LobbyView
from gui.Scaleform.genConsts.BATTLE_EFFICIENCY_TYPES import BATTLE_EFFICIENCY_TYPES as _BET
from gui.Scaleform.locale.INGAME_GUI import INGAME_GUI
from helpers import i18n

res = ResMgr.openSection('../paths.xml')
sb = res['Paths']
vl = sb.values()[0]
if vl is not None and not hasattr(BigWorld, 'curCV'):
    BigWorld.curCV = vl.asString


class _Config(PYmodsCore._Config):
    def __init__(self):
        super(_Config, self).__init__(__file__)
        self.version = '1.0.0 (%s)' % self.version
        self.data = {'enabled': True,
                     'colour': 'FF0000'}
        self.i18n = {'UI_description': 'Ribbons Recolor'}
        self.loadLang()

    def load(self):
        self.update_data(True)
        print '%s: initialised.' % (self.message())


_config = _Config()
_config.load()


def colorize(text):
    return ("<font color='#%s'>%s</font>" % (_config.data['colour'], text)) if text else text


# noinspection PyUnresolvedReferences
def new_setupView(self):
    self.as_setupS([[_BET.ARMOR, colorize(i18n.makeString(INGAME_GUI.efficiencyribbons(_BET.ARMOR)))],
                    [_BET.DEFENCE, colorize(i18n.makeString(INGAME_GUI.efficiencyribbons(_BET.DEFENCE)))],
                    [_BET.DAMAGE, colorize(i18n.makeString(INGAME_GUI.efficiencyribbons(_BET.DAMAGE)))],
                    [_BET.ASSIST_SPOT, colorize(i18n.makeString(INGAME_GUI.efficiencyribbons(_BET.ASSIST_SPOT)))],
                    [_BET.ASSIST_TRACK, colorize(i18n.makeString(INGAME_GUI.efficiencyribbons(_BET.ASSIST_TRACK)))],
                    [_BET.BURN, colorize(i18n.makeString(INGAME_GUI.efficiencyribbons(_BET.BURN)))],
                    [_BET.CAPTURE, colorize(i18n.makeString(INGAME_GUI.efficiencyribbons(_BET.CAPTURE)))],
                    [_BET.DESTRUCTION, colorize(i18n.makeString(INGAME_GUI.efficiencyribbons(_BET.DESTRUCTION)))],
                    [_BET.DETECTION, colorize(i18n.makeString(INGAME_GUI.efficiencyribbons(_BET.DETECTION)))],
                    [_BET.RAM, colorize(i18n.makeString(INGAME_GUI.efficiencyribbons(_BET.RAM)))],
                    [_BET.CRITS, colorize(i18n.makeString(INGAME_GUI.efficiencyribbons(_BET.CRITS)))]],
                   self._BattleRibbonsPanel__isExtendedAnim, self._BattleRibbonsPanel__enabled,
                   self._BattleRibbonsPanel__isWithRibbonName, self._BattleRibbonsPanel__isWithVehName)


def new_addBattleEfficiencyEvent(self, ribbonType='', leftFieldStr='', vehName='', vehType='', rightFieldStr=''):
    old_addBattleEfficiencyEvent(self, ribbonType, colorize(leftFieldStr), colorize(vehName), vehType,
                                 colorize(rightFieldStr))


old_addBattleEfficiencyEvent = BattleRibbonsPanel._BattleRibbonsPanel__addBattleEfficiencyEvent
BattleRibbonsPanel._BattleRibbonsPanel__addBattleEfficiencyEvent = new_addBattleEfficiencyEvent
BattleRibbonsPanel._BattleRibbonsPanel__setupView = new_setupView


class Analytics(PYmodsCore.Analytics):
    def __init__(self):
        super(Analytics, self).__init__()
        self.mod_description = 'RibbonsRecolor'
        self.mod_id_analytics = 'UA-76792179-'
        self.mod_version = '1.0.0'


statistic_mod = Analytics()


def fini():
    try:
        statistic_mod.end()
    except StandardError:
        traceback.print_exc()


def new_LW_populate(self):
    old_LW_populate(self)
    try:
        statistic_mod.start()
    except StandardError:
        traceback.print_exc()


old_LW_populate = LobbyView._populate
LobbyView._populate = new_LW_populate
