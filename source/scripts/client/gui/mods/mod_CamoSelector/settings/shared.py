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
    SHOP, HIDDEN, INTERNATIONAL, CUSTOM = range(4)
    AVAILABLE_REGIONS = (SHOP, HIDDEN, INTERNATIONAL, CUSTOM)
    ALL = (SHOP, HIDDEN, INTERNATIONAL, CUSTOM)
    VISIBLE = ALL


TAB_TO_RAND_MODE = {
    C11nTabs.SHOP: (RandMode.OFF, RandMode.RANDOM),
    C11nTabs.HIDDEN: (RandMode.OFF, RandMode.RANDOM),
    C11nTabs.INTERNATIONAL: (RandMode.OFF, RandMode.RANDOM, RandMode.TEAM),
    C11nTabs.CUSTOM: (RandMode.OFF, RandMode.RANDOM, RandMode.TEAM)}


def isItemSuitableForTab(item, tabIndex):
    if item is None:
        return False
    ct = C11nTabs
    isInter = isCamoInternational(item.descriptor)
    return not ((tabIndex == ct.SHOP and (item.isHidden or item.priceGroup == 'custom'))
                or (tabIndex == ct.HIDDEN and (not item.isHidden or isInter or item.priceGroup == 'custom'))
                or (tabIndex == ct.INTERNATIONAL and not isInter)
                or (tabIndex == ct.CUSTOM and item.priceGroup != 'custom'))
