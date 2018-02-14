import BigWorld
from CurrentVehicle import g_currentVehicle
from PYmodsCore import overrideMethod
from gui import g_tankActiveCamouflage
from gui.ClientHangarSpace import _VehicleAppearance
from gui.Scaleform.framework import ViewTypes
from gui.app_loader import g_appLoader
from items.vehicles import CAMOUFLAGE_KIND_INDICES
from vehicle_systems.CompoundAppearance import CompoundAppearance
from . import g_config
from .shared import SEASON_NAME_TO_TYPE, applyCache


@overrideMethod(_VehicleAppearance, '_VehicleAppearance__getActiveOutfit')
def new_getActiveOutfit(base, self):
    result = base(self).copy()
    manager = g_appLoader.getDefLobbyApp().containerManager
    if manager is not None:
        container = manager.getContainer(ViewTypes.LOBBY_SUB)
        if container is not None:
            c11nView = container.getView()
            if c11nView is not None and hasattr(c11nView, 'getCurrentOutfit'):
                return c11nView.getCurrentOutfit()  # fix for HangarFreeCam
    if g_config.data['enabled']:
        vehicle = g_currentVehicle.item
        applyCache(result, g_tankActiveCamouflage[vehicle.intCD], vehicle.descriptor)
    return result


@overrideMethod(CompoundAppearance, '_CompoundAppearance__getVehicleOutfit')
def new_getVehicleOutfit(base, self, *a, **kw):
    result = base(self, *a, **kw).copy()
    if not self._CompoundAppearance__vehicle:
        return result
    if g_config.data['enabled']:
        applyCache(
            result, SEASON_NAME_TO_TYPE[CAMOUFLAGE_KIND_INDICES[BigWorld.player().arena.arenaType.vehicleCamouflageKind]],
            self._CompoundAppearance__typeDesc)
    return result
