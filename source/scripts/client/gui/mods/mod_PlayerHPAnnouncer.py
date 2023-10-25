# -*- coding: utf-8 -*-
import BigWorld
import SoundGroups
from OpenModsCore import Analytics, ConfigNoInterface, SimpleConfigInterface, overrideMethod, events
from gui.Scaleform.daapi.view.meta import DamagePanelMeta
from gui.battle_control import avatar_getter


class ConfigInterface(ConfigNoInterface, SimpleConfigInterface):
    def __init__(self):
        self.currentPercent = None
        super(ConfigInterface, self).__init__()

    def init(self):
        self.ID = '%(mod_ID)s'
        self.version = '1.0.1 (%(file_compile_date)s)'
        self.author = 'by Polyacov_Yury'
        self.modsGroup = 'PYmods'
        self.data = {'10percent': 'PlayerHPAnnouncer_10',
                     '25percent': 'PlayerHPAnnouncer_25',
                     '50percent': 'PlayerHPAnnouncer_50'}
        super(ConfigInterface, self).init()

    def loadLang(self):
        pass


g_config = ConfigInterface()
statistic_mod = Analytics(g_config.ID, g_config.version, 'UA-76792179-12')


@events.PlayerAvatar.startGUI.after
def new_startGUI(*_, **__):
    g_config.currentPercent = 100


@events.PlayerAvatar.destroyGUI.before
def new_destroyGUI(*_, **__):
    g_config.currentPercent = None


@overrideMethod(DamagePanelMeta.DamagePanelMeta, 'as_updateHealthS')
def new_updateHealth(base, self, healthStr, progress, *args, **kwargs):
    base(self, healthStr, progress, *args, **kwargs)
    p = BigWorld.player()
    if g_config.currentPercent is None or avatar_getter.getPlayerVehicleID(p) != avatar_getter.getVehicleIDAttached(p):
        return
    for percentage in (10, 25, 50):
        if not progress:
            break
        if progress <= percentage < g_config.currentPercent:
            SoundGroups.g_instance.playSound2D(g_config.data['%spercent' % percentage])
            break
    g_config.currentPercent = progress
