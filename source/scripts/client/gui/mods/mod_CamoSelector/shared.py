import os

from CurrentVehicle import g_currentPreviewVehicle, g_currentVehicle
from gui.Scaleform.daapi.view.lobby.customization.shared import SEASON_TYPE_TO_NAME
from shared_utils import CONST_CONTAINER


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
