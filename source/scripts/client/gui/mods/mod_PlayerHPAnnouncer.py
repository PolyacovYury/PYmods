# -*- coding: utf-8 -*-
import PYmodsCore
import SoundGroups
from Avatar import PlayerAvatar
from gui.Scaleform.daapi.view.meta import DamagePanelMeta


class _Config(PYmodsCore.Config):
    def __init__(self):
        super(self.__class__, self).__init__('%(mod_ID)s')
        self.version = '1.0.1 (%(file_compile_date)s)'
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
statistic_mod = PYmodsCore.Analytics(_config.ID, _config.version.split(' ', 1)[0], 'UA-76792179-12')


@PYmodsCore.overrideMethod(PlayerAvatar, '_PlayerAvatar__startGUI')
def new_startGUI(base, self):
    base(self)
    _config.currentPercent = 100


@PYmodsCore.overrideMethod(PlayerAvatar, '_PlayerAvatar__destroyGUI')
def new_destroyGUI(base, self):
    base(self)
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
