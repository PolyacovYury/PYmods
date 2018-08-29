import nations
from CurrentVehicle import g_currentVehicle
from gui.Scaleform.daapi.view.lobby.customization.shared import TABS_ITEM_MAPPING, TYPES_ORDER
from gui.Scaleform.genConsts.SEASONS_CONSTANTS import SEASONS_CONSTANTS
from gui.customization.shared import createCustomizationBaseRequestCriteria, C11N_ITEM_TYPE_MAP
from gui.shared.gui_items import GUI_ITEM_TYPE, ItemsCollection
from gui.shared.utils.requesters import REQ_CRITERIA
from helpers import i18n
from items.components.c11n_constants import SeasonType
from items.vehicles import g_cache
from shared_utils import CONST_CONTAINER
from .. import g_config


class CSMode(CONST_CONTAINER):
    BUY, INSTALL, SETUP = range(3)
    NAMES = {BUY: 'buy', INSTALL: 'install', SETUP: 'setup'}


class CSTabs(CONST_CONTAINER):
    STYLE, PAINT, CAMO_SHOP, CAMO_HIDDEN, CAMO_GLOBAL, CAMO_CUSTOM, EMBLEM, INSCRIPTION, EFFECT = ALL = range(9)
    AVAILABLE_REGIONS = (PAINT, CAMO_SHOP, CAMO_HIDDEN, CAMO_GLOBAL, CAMO_CUSTOM, EMBLEM, INSCRIPTION)
    VISIBLE = ALL  # legacy, maybe not all tabs will be visible, idk
    CAMO = (CAMO_SHOP, CAMO_HIDDEN, CAMO_GLOBAL, CAMO_CUSTOM)
    REGIONS = CAMO + (STYLE, EFFECT, PAINT)


ITEM_TO_TABS = {GUI_ITEM_TYPE.PAINT: (CSTabs.PAINT,), GUI_ITEM_TYPE.CAMOUFLAGE: CSTabs.CAMO,
                GUI_ITEM_TYPE.EMBLEM: (CSTabs.EMBLEM,), GUI_ITEM_TYPE.INSCRIPTION: (CSTabs.INSCRIPTION,),
                GUI_ITEM_TYPE.MODIFICATION: (CSTabs.EFFECT,), GUI_ITEM_TYPE.STYLE: (CSTabs.STYLE,)}


def tabToItem(tabIndex, mode):
    if mode == CSMode.BUY:
        return TABS_ITEM_MAPPING.get(tabIndex)
    return next(itemType for itemType in ITEM_TO_TABS if tabIndex in ITEM_TO_TABS[itemType])


class ACTION_ALIASES:
    CHANGE_SUMMER = 8
    CHANGE_WINTER = 9
    CHANGE_DESERT = 10
    CHANGE_ALLY = 11
    CHANGE_ENEMY = 12


def getItems(itemTypeID, ctx, criteria):
    if not isinstance(itemTypeID, tuple):
        itemTypeID = (itemTypeID,)
    if ctx.mode == CSMode.BUY:
        return ctx.itemsCache.items.getItems(itemTypeID, criteria)
    else:
        result = ItemsCollection()
        itemGetter = ctx.itemsCache.items.getItemByCD
        itemTypes = g_cache.customization20().itemTypes
        for typeID in itemTypeID:
            for item in itemTypes[C11N_ITEM_TYPE_MAP[typeID]].itervalues():
                guiItem = itemGetter(item.compactDescr)
                if criteria(guiItem):
                    result[guiItem.intCD] = guiItem
        return result


def CSComparisonKey(item):
    return TYPES_ORDER.index(item.itemTypeID), getGroupName(item), item.id


def getGroupName(item):
    groupName = item.groupUserName
    nationIDs = []
    if item.descriptor.filter:
        for filterNode in item.descriptor.filter.include:
            if filterNode.nations:
                nationIDs += filterNode.nations
    if len(nationIDs) == 1:
        nationUserName = i18n.makeString('#vehicle_customization:repaint/%s_base_color' % nations.NAMES[nationIDs[0]])
    elif len(nationIDs) > 1:
        nationUserName = g_config.i18n['UI_flashCol_camoGroup_multinational']
    else:
        nationUserName = g_config.i18n['UI_flashCol_camoGroup_special']
    if not groupName:
        groupName = g_config.i18n['UI_flashCol_camoGroup_special']
    else:  # HangarPainter support
        nationUserName = nationUserName.replace('</font>', '')
        if ' ' in nationUserName.replace('<font ', ''):
            nationUserName = nationUserName.rsplit(' ', 1)[0]
        if '>' in groupName:
            groupName = groupName.split('>', 1)[1]
        groupName = nationUserName + ' / ' + groupName
    return groupName


def getItemSeason(item):
    itemName, itemKey = (item.descriptor.userKey, 'custom') if item.priceGroup == 'custom' else (
        item.id, 'remap')
    itemSeason = item.season
    if itemName in g_config.camouflages[itemKey]:
        camoCfg = g_config.camouflages[itemKey][itemName]
        if 'season' in camoCfg:
            itemSeason = SeasonType.UNDEFINED
            for season in SEASONS_CONSTANTS.SEASONS:
                if season in camoCfg['season']:
                    itemSeason |= getattr(SeasonType, season.upper())
    return itemSeason


def createBaseRequirements(ctx, season=None):
    season = season or SeasonType.ALL
    if ctx.mode == CSMode.BUY:
        return createCustomizationBaseRequestCriteria(
            g_currentVehicle.item, ctx.eventsCache.questsProgress, ctx.getAppliedItems(), season)
    return REQ_CRITERIA.CUSTOM(lambda item: getItemSeason(item) & season)


def isItemSuitableForTab(item, tabIndex):
    if item is None or tabIndex not in ITEM_TO_TABS[item.itemTypeID]:
        return False
    if tabIndex in (CSTabs.EMBLEM, CSTabs.INSCRIPTION):
        return True
    vehicle = g_currentVehicle.item
    if tabIndex in (CSTabs.STYLE, CSTabs.PAINT, CSTabs.EFFECT):
        return item.mayInstall(vehicle)
    isGlobal = g_config.isCamoGlobal(item.descriptor)
    return not (
            (tabIndex == CSTabs.CAMO_SHOP and (item.isHidden or item.priceGroup == 'custom')) or
            (tabIndex == CSTabs.CAMO_HIDDEN and (not item.isHidden or isGlobal or item.priceGroup == 'custom')) or
            (tabIndex == CSTabs.CAMO_GLOBAL and not isGlobal) or
            (tabIndex == CSTabs.CAMO_CUSTOM and item.priceGroup != 'custom'))
