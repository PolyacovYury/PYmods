# -*- coding: utf-8 -*-
import PYmodsCore
import SoundGroups
from Avatar import PlayerAvatar
from gui.Scaleform.daapi.view.meta import DamagePanelMeta


class ConfigInterface(PYmodsCore.PYmodsConfigInterface):
    def __init__(self):
        self.currentPercent = None
        super(ConfigInterface, self).__init__()

    def init(self):
        self.ID = '%(mod_ID)s'
        self.version = '1.0.1 (%(file_compile_date)s)'
        self.data = {'10percent': 'percent_10',
                     '25percent': 'percent_25',
                     '50percent': 'percent_50'}
        super(ConfigInterface, self).init()

    def loadLang(self):
        pass

    def updateMod(self):
        pass

    def createTemplate(self):
        pass

    def registerSettings(self):
        pass


_config = ConfigInterface()
statistic_mod = PYmodsCore.Analytics(_config.ID, _config.version, 'UA-76792179-12')


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
