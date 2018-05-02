import os
from CurrentVehicle import g_currentPreviewVehicle, g_currentVehicle
from gui.shared.gui_items import GUI_ITEM_TYPE
from shared_utils import CONST_CONTAINER


class RandMode(CONST_CONTAINER):
    OFF, TEAM, RANDOM = range(3)
    NAMES = {OFF: 'off', RANDOM: 'random', TEAM: 'team'}
    INDICES = {v: k for k, v in NAMES.iteritems()}


class TeamMode(CONST_CONTAINER):
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
    INSTALL, SETUP = range(2)
    NAMES = {INSTALL: 'install', SETUP: 'setup'}


class C11nTabs(CONST_CONTAINER):
    PAINT_SHOP, PAINT_CUSTOM, CAMO_SHOP, CAMO_HIDDEN, CAMO_GLOBAL, CAMO_CUSTOM, EMBLEM, INSCRIPTION, EFFECT = range(8)
    AVAILABLE_REGIONS = (PAINT_SHOP, PAINT_CUSTOM, CAMO_SHOP, CAMO_HIDDEN, CAMO_GLOBAL, CAMO_CUSTOM, EMBLEM, INSCRIPTION)
    ALL = (PAINT_SHOP, PAINT_CUSTOM, CAMO_SHOP, CAMO_HIDDEN, CAMO_GLOBAL, CAMO_CUSTOM, EMBLEM, INSCRIPTION, EFFECT)
    VISIBLE = ALL  # legacy, maybe not all tabs will be visible, idk
    PAINT = (PAINT_SHOP, PAINT_CUSTOM)
    CAMO = (CAMO_SHOP, CAMO_HIDDEN, CAMO_GLOBAL, CAMO_CUSTOM)
    REGIONS = PAINT + CAMO + (EFFECT,)


ITEM_TO_TABS = {GUI_ITEM_TYPE.PAINT: C11nTabs.PAINT, GUI_ITEM_TYPE.CAMOUFLAGE: C11nTabs.CAMO,
                GUI_ITEM_TYPE.EMBLEM: (C11nTabs.EMBLEM,), GUI_ITEM_TYPE.INSCRIPTION: C11nTabs.INSCRIPTION,
                GUI_ITEM_TYPE.MODIFICATION: (C11nTabs.EFFECT,)}


def tabToItem(tabIndex):
    return next(itemType for itemType in ITEM_TO_TABS if tabIndex in ITEM_TO_TABS[itemType])
