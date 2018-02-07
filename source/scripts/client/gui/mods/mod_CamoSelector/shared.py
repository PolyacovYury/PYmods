import os

from CurrentVehicle import g_currentPreviewVehicle, g_currentVehicle
from shared_utils import CONST_CONTAINER


class RAND_MODE(CONST_CONTAINER):
    """ Customization mode.
    """
    OFF, RANDOM, TEAM = range(3)
    NAMES = {OFF: 'off', RANDOM: 'random', TEAM: 'team'}


class TEAM_MODE(CONST_CONTAINER):
    """ Customization mode.
    """
    ALLY, ENEMY, BOTH = range(1, 4)
    NAMES = {ALLY: 'ally', ENEMY: 'enemy', BOTH: 'both'}


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
