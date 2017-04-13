# -*- coding: utf-8 -*-

import ResMgr

import BigWorld
import PYmodsCore
from Avatar import PlayerAvatar
import SoundGroups
from gui.Scaleform.daapi.view.meta import DamagePanelMeta

res = ResMgr.openSection('../paths.xml')
sb = res['Paths']
vl = sb.values()[0]
if vl is not None and not hasattr(BigWorld, 'curCV'):
    BigWorld.curCV = vl.asString


class _Config(PYmodsCore._Config):
    def __init__(self):
        super(_Config, self).__init__('%(mod_ID)s')
        self.version = '1.0.0 (%(file_compile_date)s)'
        self.data = {'10percent': 'percent_10',
                     '25percent': 'percent_25',
                     '50percent': 'percent_50'}
        self.currentPercent = None

    def updateMod(self):
        pass

    def do_config_delayed(self):
        pass

_config = _Config()
_config.load()


def new_afterCreate(self):
    old_afterCreate(self)
    _config.currentPercent = 100


def new_beforeDelete(self):
    old_beforeDelete(self)
    _config.currentPercent = None


def new_updateHealth(self, healthStr, progress):
    old_updateHealth(self, healthStr, progress)
    if _config.currentPercent is None:
        return
    for percentage in (10, 25, 50):
        if not progress:
            break
        if progress <= percentage < _config.currentPercent:
            SoundGroups.g_instance.playSound2D(_config.data['%spercent' % percentage])
            break
    _config.currentPercent = progress


old_afterCreate = PlayerAvatar._PlayerAvatar__startGUI
PlayerAvatar._PlayerAvatar__startGUI = new_afterCreate
old_beforeDelete = PlayerAvatar._PlayerAvatar__destroyGUI
PlayerAvatar._PlayerAvatar__destroyGUI = new_beforeDelete
old_updateHealth = DamagePanelMeta.DamagePanelMeta.as_updateHealthS
DamagePanelMeta.DamagePanelMeta.as_updateHealthS = new_updateHealth
statistic_mod = PYmodsCore.Analytics(_config.ID, _config.version.split(' ', 1)[0], 'UA-76792179-12')
