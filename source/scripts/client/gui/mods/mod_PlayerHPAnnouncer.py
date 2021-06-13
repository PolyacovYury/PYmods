# -*- coding: utf-8 -*-
import SoundGroups
from PYmodsCore import PYmodsConfigInterface, Analytics, overrideMethod, events
from PYmodsCore.config.interfaces.Simple import ConfigNoInterface
from gui.Scaleform.daapi.view.meta import DamagePanelMeta


class ConfigInterface(ConfigNoInterface, PYmodsConfigInterface):
    def __init__(self):
        self.currentPercent = None
        super(ConfigInterface, self).__init__()

    def init(self):
        self.ID = '%(mod_ID)s'
        self.version = '1.0.1 (%(file_compile_date)s)'
        self.data = {'10percent': 'PlayerHPAnnouncer_10',
                     '25percent': 'PlayerHPAnnouncer_25',
                     '50percent': 'PlayerHPAnnouncer_50'}
        super(ConfigInterface, self).init()

    def loadLang(self):
        pass


_config = ConfigInterface()
statistic_mod = Analytics(_config.ID, _config.version, 'UA-76792179-12')


@events.PlayerAvatar.startGUI.after
def new_startGUI(*_, **__):
    _config.currentPercent = 100


@events.PlayerAvatar.destroyGUI.before
def new_destroyGUI(*_, **__):
    _config.currentPercent = None


@overrideMethod(DamagePanelMeta.DamagePanelMeta, 'as_updateHealthS')
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
