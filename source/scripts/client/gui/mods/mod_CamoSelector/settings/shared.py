import os
from CurrentVehicle import g_currentPreviewVehicle, g_currentVehicle
from shared_utils import CONST_CONTAINER


class RandMode(CONST_CONTAINER):
    """ Customization mode.
    """
    OFF, TEAM, RANDOM = range(3)
    NAMES = {OFF: 'off', RANDOM: 'random', TEAM: 'team'}
    INDICES = {v: k for k, v in NAMES.iteritems()}


class TeamMode(CONST_CONTAINER):
    """ Customization mode.
    """
    ALLY, ENEMY, BOTH = range(1, 4)
    NAMES = {ALLY: 'ally', ENEMY: 'enemy', BOTH: 'both'}
    INDICES = {v: k for k, v in NAMES.iteritems()}


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


def isCamoInternational(camo):
    from . import g_config
    return getCamoTextureName(camo) in g_config.interCamo


class C11nMode(CONST_CONTAINER):
    """ Customization mode.
    """
    INSTALL, SETUP = range(2)
    NAMES = {INSTALL: 'install', SETUP: 'setup'}


class C11nTabs(CONST_CONTAINER):
    """
    Enumeration of customization item browser tabs.
    The order of the ALL property corresponds to the order the tab names will appear in.
    """
    PAINT, PAINT_CUSTOM, SHOP, HIDDEN, INTERNATIONAL, CUSTOM = range(6)
    AVAILABLE_REGIONS = (PAINT, PAINT_CUSTOM, SHOP, HIDDEN, INTERNATIONAL, CUSTOM)
    ALL = (PAINT, PAINT_CUSTOM, SHOP, HIDDEN, INTERNATIONAL, CUSTOM)
    VISIBLE = ALL
    PAINTS = (PAINT, PAINT_CUSTOM)
    CAMO = (SHOP, HIDDEN, INTERNATIONAL, CUSTOM)
