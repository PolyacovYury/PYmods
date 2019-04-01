import nations
from CurrentVehicle import g_currentVehicle
from PYmodsCore import overrideMethod
from collections import defaultdict
from functools import partial
from gui.Scaleform.daapi.view.lobby.customization.customization_carousel import CustomizationBookmarkVO, \
    CustomizationCarouselDataProvider as WGCarouselDataProvider, CustomizationSeasonAndTypeFilterData, comparisonKey
from gui.Scaleform.daapi.view.lobby.customization.shared import TABS_ITEM_TYPE_MAPPING, TYPE_TO_TAB_IDX, TYPES_ORDER, C11nTabs
from gui.Scaleform.locale.VEHICLE_CUSTOMIZATION import VEHICLE_CUSTOMIZATION
from gui.customization.shared import createCustomizationBaseRequestCriteria, C11N_ITEM_TYPE_MAP
from gui.shared.gui_items import GUI_ITEM_TYPE, ItemsCollection
from gui.shared.utils.requesters import REQ_CRITERIA
from helpers.i18n import makeString as _ms
from items.components.c11n_constants import SeasonType
from items.vehicles import g_cache
from .shared import getItemSeason
from .. import g_config


def createBaseRequirements(ctx, season=None):
    season = season or SeasonType.ALL
    if ctx.isBuy:
        return createCustomizationBaseRequestCriteria(
            g_currentVehicle.item, ctx.eventsCache.questsProgress, ctx.getAppliedItems(), season)
    return REQ_CRITERIA.CUSTOM(lambda item: getItemSeason(item) & season)


class CustomizationCarouselDataProvider(WGCarouselDataProvider):
    def __init__(self, currentVehicle, carouselItemWrapper, proxy):
        super(CustomizationCarouselDataProvider, self).__init__(currentVehicle, carouselItemWrapper, proxy)
        self._customizationItems = []
        self._itemSizeData = []
        self._customizationBookmarks = []
        self._selectedIdx = -1

    def updateTabGroups(self):
        self._allSeasonAndTabFilterData.clear()
        visibleTabs = defaultdict(set)
        anchorsData = self._proxy.hangarSpace.getSlotPositions()
        requirement = createBaseRequirements(self._proxy)
        allItems = getItems(GUI_ITEM_TYPE.CUSTOMIZATIONS, self._proxy, requirement)
        for tabIndex in C11nTabs.ALL:
            self._allSeasonAndTabFilterData[tabIndex] = {}
            for season in SeasonType.COMMON_SEASONS:
                self._allSeasonAndTabFilterData[tabIndex][season] = CustomizationSeasonAndTypeFilterData()

        isBuy = self._proxy.isBuy
        for item in sorted(allItems.itervalues(), key=comparisonKey if isBuy else CSComparisonKey):
            if isBuy and item.isHiddenInUI():
                continue
            groupName = item.groupUserName if isBuy else getGroupName(item)
            tabIndex = TYPE_TO_TAB_IDX.get(item.itemTypeID)
            if not (isBuy or isItemSuitableForTab(item, tabIndex)):
                continue
            if (isBuy and tabIndex == C11nTabs.CAMOUFLAGE and
                    g_currentVehicle.item.descriptor.type.hasCustomDefaultCamouflage):
                continue
            for seasonType in SeasonType.COMMON_SEASONS:
                if (item.season if isBuy else getItemSeason(item)) & seasonType:
                    seasonAndTabData = self._allSeasonAndTabFilterData[tabIndex][seasonType]
                    if groupName and groupName not in seasonAndTabData.allGroups:
                        seasonAndTabData.allGroups.append(groupName)
                    seasonAndTabData.itemCount += 1
                    if item.itemTypeID in (GUI_ITEM_TYPE.INSCRIPTION, GUI_ITEM_TYPE.EMBLEM, GUI_ITEM_TYPE.PERSONAL_NUMBER):
                        if not self.__hasSlots(anchorsData, item.itemTypeID):
                            continue
                    visibleTabs[seasonType].add(tabIndex)

        self._proxy.updateVisibleTabsList(visibleTabs)
        for tabIndex in C11nTabs.ALL:
            for seasonType in SeasonType.COMMON_SEASONS:
                seasonAndTabData = self._allSeasonAndTabFilterData[tabIndex][seasonType]
                seasonAndTabData.allGroups.append(_ms(VEHICLE_CUSTOMIZATION.CUSTOMIZATION_FILTER_ALLGROUPS))
                seasonAndTabData.selectedGroupIndex = len(seasonAndTabData.allGroups) - 1

    def _buildCustomizationItems(self):
        season = self._seasonID
        isBuy = self._proxy.isBuy
        requirement = createBaseRequirements(self._proxy, season)
        if not isBuy:
            requirement |= REQ_CRITERIA.CUSTOM(partial(isItemSuitableForTab, tabIndex=self._tabIndex))
        seasonAndTabData = self._allSeasonAndTabFilterData[self._tabIndex][season]
        allItemsGroup = len(seasonAndTabData.allGroups) - 1
        if seasonAndTabData.selectedGroupIndex != allItemsGroup:
            selectedGroup = seasonAndTabData.allGroups[seasonAndTabData.selectedGroupIndex]
            requirement |= REQ_CRITERIA.CUSTOM(lambda x: (x.groupUserName if isBuy else getGroupName(x)) == selectedGroup)
        if self._historicOnlyItems:
            requirement |= ~REQ_CRITERIA.CUSTOMIZATION.HISTORICAL
        applied = self._proxy.getAppliedItems(isOriginal=False)
        if self._onlyOwnedAndFreeItems and self._onlyAppliedItems:
            requirement |= REQ_CRITERIA.CUSTOM(lambda x: x.intCD in applied or self._proxy.getItemInventoryCount(x) > 0)
        elif self._onlyOwnedAndFreeItems:
            requirement |= REQ_CRITERIA.CUSTOM(lambda x: self._proxy.getItemInventoryCount(x) > 0)
        elif self._onlyAppliedItems:
            requirement |= REQ_CRITERIA.CUSTOM(lambda x: x.intCD in applied)
        allItems = {}
        for itemTypeId in TABS_ITEM_TYPE_MAPPING[self._tabIndex]:
            allItems.update(getItems(itemTypeId, self._proxy, requirement))
        self._customizationItems = []
        self._customizationBookmarks = []
        lastGroup = None
        for item in sorted(allItems.itervalues(), key=comparisonKey if isBuy else CSComparisonKey):
            if isBuy and item.isHiddenInUI():
                continue
            groupName = getGroupName(item)
            group = item.groupID if isBuy else groupName
            if item.intCD == self._selectIntCD:
                self._selectedIdx = self.itemCount
                self._selectIntCD = None
            if group != lastGroup:
                lastGroup = group
                self._customizationBookmarks.append(
                    CustomizationBookmarkVO((item.groupUserName if isBuy else groupName), self.itemCount).asDict())
            self._customizationItems.append(item.intCD)
            self._itemSizeData.append(item.isWide())

        self._proxy.setCarouselItems(self.collection)
        return


def isItemSuitableForTab(item, tabIndex):
    if item is None or tabIndex != TYPE_TO_TAB_IDX[item.itemTypeID]:
        return False
    if tabIndex in (C11nTabs.CAMOUFLAGE, C11nTabs.EMBLEM, C11nTabs.INSCRIPTION):
        return True
    vehicle = g_currentVehicle.item
    if tabIndex in (C11nTabs.STYLE, C11nTabs.PAINT, C11nTabs.EFFECT, C11nTabs.PROJECTION_DECAL):
        return not item.descriptor.filter or matchVehicleLevel(item.descriptor.filter, vehicle.descriptor.type)


def matchVehicleLevel(f, vehicleType):
    return not f.include or any((not node.levels or vehicleType.level in node.levels) for node in f.include)


def CSComparisonKey(item):
    return (TYPES_ORDER.index(item.itemTypeID), item.priceGroup == 'custom', g_config.isCamoGlobal(item.descriptor),
            item.isHidden, not item.isRare(), getGroupName(item), item.id)


def getGroupName(item):
    groupName = item.groupUserName
    nationIDs = []
    for filterNode in getattr(item.descriptor.filter, 'include', ()):
        nationIDs += filterNode.nations or []
    if len(nationIDs) == 1:
        nationUserName = _ms('#vehicle_customization:repaint/%s_base_color' % nations.NAMES[nationIDs[0]])
    elif len(nationIDs) > 1:
        nationUserName = g_config.i18n['flashCol_camoGroup_multinational']
    else:
        nationUserName = g_config.i18n['flashCol_camoGroup_special']
    if not groupName:
        groupName = g_config.i18n['flashCol_camoGroup_special']
    else:  # HangarPainter support
        nationUserName = nationUserName.replace('</font>', '')
        if ' ' in nationUserName.replace('<font ', ''):
            nationUserName = nationUserName.rsplit(' ', 1)[0]
        if '>' in groupName:
            groupName = groupName.split('>', 1)[1]
        groupName = nationUserName + ' / ' + groupName
    return groupName


def getItems(itemTypeID, ctx, criteria):
    if ctx.isBuy:
        return ctx.itemsCache.items.getItems(itemTypeID, criteria)
    if not isinstance(itemTypeID, tuple):
        itemTypeID = (itemTypeID,)
    result = ItemsCollection()
    itemGetter = ctx.itemsCache.items.getItemByCD
    itemTypes = g_cache.customization20().itemTypes
    for typeID in itemTypeID:
        for item in itemTypes[C11N_ITEM_TYPE_MAP[typeID]].itervalues():
            guiItem = itemGetter(item.compactDescr)
            if criteria(guiItem):
                result[guiItem.intCD] = guiItem
    return result


@overrideMethod(WGCarouselDataProvider, '__new__')
def new(base, cls, *a, **kw):
    if not g_config.data['enabled']:
        return base(cls, *a, **kw)
    return base(CustomizationCarouselDataProvider, *a, **kw)
