import os

from CurrentVehicle import g_currentPreviewVehicle, g_currentVehicle
from shared_utils import CONST_CONTAINER


class RAND_MODE(CONST_CONTAINER):
    """ Customization mode.
    """
    OFF, INCLUDE, OVERRIDE = range(3)
    NAMES = {OFF: 'off', INCLUDE: 'include', OVERRIDE: 'override'}


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
