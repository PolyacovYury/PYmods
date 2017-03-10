import traceback

from gui.battle_control.arena_info import vos_collections
from helpers import dependency
from skeletons.gui.battle_session import IBattleSessionProvider


class PlayersPanelController(object):
    def __init__(self, container):
        self.uiFlash = None
        self.container = container
        vxBattleFlash.register(self.container)
        vxBattleFlash.onStateChanged += self.__onStateChanged

    def __onStateChanged(self, eventType, compID, compUI):
        if compID != self.container:
            return
        if eventType == vxBattleFlashEvents.COMPONENT_READY:
            self.uiFlash = compUI
            self.setup()
        if eventType == vxBattleFlashEvents.COMPONENT_DISPOSE:
            self.uiFlash = None

    def setup(self):
        if not self.uiFlash:
            return
        self.uiFlash.as_setPPConfigS(self.container, {'leftX': 0, 'leftY': 0, 'rightX': 0, 'rightY': 0,
                                                      'shadow': [0, 90, '0x000000', 100, 2, 200]})
        g_sessionProvider = dependency.instance(IBattleSessionProvider)
        collection = vos_collections.VehiclesInfoCollection().iterator(g_sessionProvider.getArenaDP())
        for vInfoVO in collection:
            vehicleID = vInfoVO.vehicleID
            maxHealth = vInfoVO.vehicleType.maxHealth
            self.uiFlash.as_setPPTextS(self.container, [vehicleID, "<p align='center'>%s</p>" % maxHealth])


try:
    from gui.mods.vxBattleFlash import *

    _gui_flash = PlayersPanelController('%(mod_ID)s')
except ImportError:
    vxBattleFlash = None
    vxBattleFlashEvents = None
    vxBattleFlashAliases = None
    _gui_flash = None
    print '%(mod_ID)s: Battle Flash API (vxBattleFlash) not found. Text viewing disabled.'
except StandardError:
    vxBattleFlash = None
    vxBattleFlashEvents = None
    vxBattleFlashAliases = None
    _gui_flash = None
    traceback.print_exc()
