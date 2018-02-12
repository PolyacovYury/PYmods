import os
import items.vehicles
from CurrentVehicle import g_currentPreviewVehicle, g_currentVehicle
from gui.Scaleform.daapi.view.lobby.customization.shared import SEASON_TYPE_TO_NAME
from gui.shared.gui_items import GUI_ITEM_TYPE
from helpers import dependency
from shared_utils import CONST_CONTAINER
from skeletons.gui.shared import IItemsCache
from vehicle_systems.tankStructure import TankPartNames


class RandMode(CONST_CONTAINER):
    """ Customization mode.
    """
    OFF, RANDOM, TEAM = range(3)
    NAMES = {OFF: 'off', RANDOM: 'random', TEAM: 'team'}


class TeamMode(CONST_CONTAINER):
    """ Customization mode.
    """
    ALLY, ENEMY, BOTH = range(1, 4)
    NAMES = {ALLY: 'ally', ENEMY: 'enemy', BOTH: 'both'}


SEASON_NAME_TO_TYPE = {v: k for k, v in SEASON_TYPE_TO_NAME.iteritems()}


def getCurrentDesc():
    if g_currentPreviewVehicle.isPresent():
        vDesc = g_currentPreviewVehicle.item.descriptor
    elif g_currentVehicle.isPresent():
        vDesc = g_currentVehicle.item.descriptor
    else:
        raise AttributeError('g_currentVehicle.item.descriptor not found')
    return vDesc


def getCurrentNationID():
    return getCurrentDesc().type.customizationNationID


def getCamoTextureName(camo):
    return os.path.splitext(os.path.basename(camo.texture))[0]


def isCamoInternational(storage, camo):
    return getCamoTextureName(camo) in storage.interCamo


def applyCache(outfit, season, descriptor, config):
    itemsCache = dependency.instance(IItemsCache)
    nationName, vehicleName = descriptor.name.split(':')
    camouflages = items.vehicles.g_cache.customization20().camouflages
    vehConfig = config.camouflagesCache.get(nationName, {}).get(vehicleName, {})
    seasonConfig = vehConfig.get(season, {})
    for areaName in seasonConfig.keys():
        try:
            areaId = TankPartNames.getIdx(areaName)
        except Exception as e:
            print '%s: exception while reading camouflages cache for %s in %s: %s' % (
                config.ID, descriptor.name, areaName, e.message)
            continue
        slot = outfit.getContainer(areaId).slotFor(GUI_ITEM_TYPE.CAMOUFLAGE)
        if not seasonConfig[areaName]:
            slot.remove(0)
            continue
        camoID, paletteIdx, scale = seasonConfig[areaName]
        if camoID not in camouflages:
            print '%s: wrong camouflage ID for %s: %s' % (config.ID, areaName, camoID)
            del seasonConfig[areaName]
            continue
        item = itemsCache.items.getItemByCD(camouflages[camoID].camouflages)
        if paletteIdx > len(item.palettes):
            print '%s: wrong palette idx for %s camouflage: %s (available: %s)' % (
                config.ID, areaName, paletteIdx, range(len(item.palettes)))
            del seasonConfig[areaName]
            continue
        if scale not in item.scales:
            print '%s: wrong scale for %s camouflage: %s (available: %s)' % (
                config.ID, areaName, scale, item.scales)
        slot.set(item)
        component = slot.getComponent()
        component.palette = paletteIdx
        component.patternSize = scale
    if not seasonConfig:
        vehConfig.pop(season, {})
