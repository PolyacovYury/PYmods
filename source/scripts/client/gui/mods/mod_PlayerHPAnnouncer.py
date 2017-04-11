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
        self.data = {'10percent': '10percent',
                     '25percent': '25percent',
                     '50percent': '50percent'}
        self.currentPercent = None

    def updateMod(self):
        pass

    def load(self):
        self.update_data(True)
        print '%s: initialised.' % (self.message())


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
    if progress <= 10 < _config.currentPercent:
        SoundGroups.g_instance.playSound2D(_config.data['10percent'])
    elif progress <= 25 < _config.currentPercent:
        SoundGroups.g_instance.playSound2D(_config.data['25percent'])
    elif progress <= 50 < _config.currentPercent:
        SoundGroups.g_instance.playSound2D(_config.data['50percent'])
    _config.currentPercent = progress


old_afterCreate = PlayerAvatar._PlayerAvatar__startGUI
PlayerAvatar._PlayerAvatar__startGUI = new_afterCreate
old_beforeDelete = PlayerAvatar._PlayerAvatar__destroyGUI
PlayerAvatar._PlayerAvatar__destroyGUI = new_beforeDelete
old_updateHealth = DamagePanelMeta.DamagePanelMeta.as_updateHealthS
DamagePanelMeta.DamagePanelMeta.as_updateHealthS = new_updateHealth
statistic_mod = PYmodsCore.Analytics(_config.ID, _config.version.split(' ', 1)[0], 'UA-76792179-12')
