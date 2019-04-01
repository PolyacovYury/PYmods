import nations
import re
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
        allItems = self.getItems(GUI_ITEM_TYPE.CUSTOMIZATIONS, requirement)
        for tabIndex in C11nTabs.ALL:
            self._allSeasonAndTabFilterData[tabIndex] = {}
            for season in SeasonType.COMMON_SEASONS:
                self._allSeasonAndTabFilterData[tabIndex][season] = CustomizationSeasonAndTypeFilterData()

        isBuy = self._proxy.isBuy
        for item in sorted(allItems.itervalues(), key=self.CSComparisonKey):
            if isBuy and item.isHiddenInUI():
                continue
            if item.itemTypeID == GUI_ITEM_TYPE.MODIFICATION and not item.mayInstall(g_currentVehicle.item):
                continue
            groupName = getGroupName(item, isBuy)
            tabIndex = TYPE_TO_TAB_IDX.get(item.itemTypeID)
            if not self.isItemSuitableForTab(tabIndex, anchorsData, item):
                continue
            for seasonType in SeasonType.COMMON_SEASONS:
                if (item.season if isBuy else getItemSeason(item)) & seasonType:
                    seasonAndTabData = self._allSeasonAndTabFilterData[tabIndex][seasonType]
                    for name in groupName.split(g_config.i18n['flashCol_camoGroup_separator']):
                        if name and name not in seasonAndTabData.allGroups:
                            seasonAndTabData.allGroups.append(name)
                    seasonAndTabData.itemCount += 1
                    visibleTabs[seasonType].add(tabIndex)
        for tabIndex in C11nTabs.ALL:
            for seasonType in SeasonType.COMMON_SEASONS:
                seasonAndTabData = self._allSeasonAndTabFilterData[tabIndex][seasonType]
                seasonAndTabData.allGroups.append(_ms(VEHICLE_CUSTOMIZATION.CUSTOMIZATION_FILTER_ALLGROUPS))
                seasonAndTabData.selectedGroupIndex = len(seasonAndTabData.allGroups) - 1
        self._proxy.updateVisibleTabsList(visibleTabs)

    def _buildCustomizationItems(self):
        season = self._seasonID
        isBuy = self._proxy.isBuy
        anchorsData = self._proxy.hangarSpace.getSlotPositions()
        requirement = createBaseRequirements(self._proxy, season)
        if not isBuy:
            requirement |= REQ_CRITERIA.CUSTOM(partial(self.isItemSuitableForTab, self._tabIndex, anchorsData))
        filterCriteria = REQ_CRITERIA.EMPTY
        seasonAndTabData = self._allSeasonAndTabFilterData[self._tabIndex][season]
        allItemsGroupIndex = len(seasonAndTabData.allGroups) - 1
        if seasonAndTabData.selectedGroupIndex != allItemsGroupIndex:
            selectedGroup = seasonAndTabData.allGroups[seasonAndTabData.selectedGroupIndex]
            filterCriteria |= REQ_CRITERIA.CUSTOM(lambda x: selectedGroup in getGroupName(x, isBuy))
        if self._historicOnlyItems:
            filterCriteria |= ~REQ_CRITERIA.CUSTOMIZATION.HISTORICAL
        if self._onlyOwnedAndFreeItems:
            filterCriteria |= REQ_CRITERIA.CUSTOM(lambda x: self._proxy.getItemInventoryCount(x) > 0)
        sub = REQ_CRITERIA.IN_CD_LIST(self._proxy.getAppliedItems(isOriginal=False))
        if self._onlyAppliedItems:
            filterCriteria |= sub
        else:
            filterCriteria ^= sub
        allItems = self.getItems(TABS_ITEM_TYPE_MAPPING[self._tabIndex], requirement | filterCriteria)
        self._customizationItems = []
        self._customizationBookmarks = []
        lastGroup = None
        for item in sorted(allItems.itervalues(), key=self.CSComparisonKey):
            if isBuy and item.isHiddenInUI():
                continue
            if item.itemTypeID == GUI_ITEM_TYPE.MODIFICATION and not item.mayInstall(g_currentVehicle.item):
                continue
            groupName = getGroupName(item, isBuy)
            group = item.groupID if isBuy else groupName
            if item.intCD == self._selectIntCD:
                self._selectedIdx = self.itemCount
                self._selectIntCD = None
            if group != lastGroup:
                lastGroup = group
                self._customizationBookmarks.append(CustomizationBookmarkVO(groupName, self.itemCount).asDict())
            self._customizationItems.append(item.intCD)
            self._itemSizeData.append(item.isWide())

        self._proxy.setCarouselItems(self.collection)
        return

    def isItemSuitableForTab(self, tabIndex, anchorsData, item):
        if item is None or tabIndex != TYPE_TO_TAB_IDX[item.itemTypeID]:
            return False
        typeID = item.itemTypeID
        if typeID == GUI_ITEM_TYPE.STYLE:
            return item.mayInstall(g_currentVehicle.item) if item.modelsSet else all(
                self.isItemSuitableForTab(TYPE_TO_TAB_IDX[x.itemTypeID], anchorsData, x) for season in
                SeasonType.COMMON_SEASONS for x in item.getOutfit(season).items())
        if typeID == GUI_ITEM_TYPE.MODIFICATION:
            return item.mayInstall(g_currentVehicle.item)
        if typeID == GUI_ITEM_TYPE.PERSONAL_NUMBER:
            typeID = GUI_ITEM_TYPE.INSCRIPTION
        return self.__hasSlots(anchorsData, typeID)

    def CSComparisonKey(self, item):
        return (TYPES_ORDER.index(item.itemTypeID), item.priceGroup == 'custom', g_config.isCamoGlobal(item.descriptor),
                item.isHidden, not item.isRare(), getGroupName(item, self._proxy.isBuy), item.id)

    def getItems(self, itemTypeID, criteria):
        if self._proxy.isBuy:
            return self.itemsCache.items.getItems(itemTypeID, criteria)
        if not isinstance(itemTypeID, tuple):
            itemTypeID = (itemTypeID,)
        result = ItemsCollection()
        itemGetter = self.itemsCache.items.getItemByCD
        itemTypes = g_cache.customization20().itemTypes
        for typeID in itemTypeID:
            for item in itemTypes[C11N_ITEM_TYPE_MAP[typeID]].itervalues():
                guiItem = itemGetter(item.compactDescr)
                if criteria(guiItem):
                    result[guiItem.intCD] = guiItem
        return result


def getGroupName(item, isBuy=False):
    groupName = item.groupUserName
    if isBuy:
        return groupName
    nationIDs = []
    for filterNode in getattr(item.descriptor.filter, 'include', ()):
        nationIDs += filterNode.nations or []
    if len(nationIDs) == 1:
        nation = _ms('#vehicle_customization:repaint/%s_base_color' % nations.NAMES[nationIDs[0]])
    elif len(nationIDs) > 1:
        nation = g_config.i18n['flashCol_camoGroup_multinational']
    else:
        nation = g_config.i18n['flashCol_camoGroup_special']
    if not groupName:
        groupName = g_config.i18n['flashCol_camoGroup_special']
    else:  # HangarPainter support
        groupName = re.sub(r'( [^ <>]+)(?![^ <>]*>)', '', nation) + g_config.i18n['flashCol_camoGroup_separator'] + groupName
    return groupName


@overrideMethod(WGCarouselDataProvider, '__new__')
def new(base, cls, *a, **kw):
    if not g_config.data['enabled']:
        return base(cls, *a, **kw)
    return base(CustomizationCarouselDataProvider, *a, **kw)
