from PYmodsCore import overrideMethod
from collections import defaultdict
from functools import partial
from gui.Scaleform.daapi.view.lobby.customization.customization_carousel import CustomizationCarouselDataProvider, \
    CustomizationSeasonAndTypeFilterData, CustomizationBookmarkVO, comparisonKey
from gui.Scaleform.daapi.view.lobby.customization.shared import TYPE_TO_TAB_IDX
from gui.Scaleform.locale.VEHICLE_CUSTOMIZATION import VEHICLE_CUSTOMIZATION
from gui.shared.gui_items import GUI_ITEM_TYPE
from gui.shared.utils.requesters import REQ_CRITERIA
from helpers import i18n
from items.components.c11n_constants import SeasonType
from shared_utils import findFirst
from .shared import CSMode, CSTabs, tabToItem, createBaseRequirements, isItemSuitableForTab, getGroupName, CSComparisonKey, \
    getItemSeason, getItems


@overrideMethod(CustomizationCarouselDataProvider, '__init__')
def init(base, self, *a, **kw):
    base(self, *a, **kw)
    buildFilterData(self)


def buildFilterData(self):
    self._allSeasonAndTabFilterData = {}
    visibleTabs = defaultdict(set)
    c11nContext = self.service.getCtx()
    anchorsData = c11nContext.hangarSpace.getSlotPositions()
    requirement = createBaseRequirements(self._proxy)
    allItems = getItems(GUI_ITEM_TYPE.CUSTOMIZATIONS, self._proxy, requirement)
    for tabIndex in self._proxy.tabsData.ALL:
        self._allSeasonAndTabFilterData[tabIndex] = {}
        for season in SeasonType.COMMON_SEASONS:
            self._allSeasonAndTabFilterData[tabIndex][season] = CustomizationSeasonAndTypeFilterData()

    isBuy = self._proxy.isBuy
    for item in sorted(allItems.itervalues(), key=comparisonKey if isBuy else CSComparisonKey):
        groupName = item.groupUserName if isBuy else getGroupName(item)
        if isBuy:
            tabIndex = TYPE_TO_TAB_IDX.get(item.itemTypeID, -1)
        else:
            tabIndex = findFirst(partial(isItemSuitableForTab, item), CSTabs.ALL, -1)
        if tabIndex == -1:
            continue
        for seasonType in SeasonType.COMMON_SEASONS:
            if (item.season if isBuy else getItemSeason(item)) & seasonType:
                seasonAndTabData = self._allSeasonAndTabFilterData[tabIndex][seasonType]
                if groupName and groupName not in seasonAndTabData.allGroups:
                    seasonAndTabData.allGroups.append(groupName)
                seasonAndTabData.itemCount += 1
                if item.itemTypeID in (GUI_ITEM_TYPE.INSCRIPTION, GUI_ITEM_TYPE.EMBLEM):
                    for areaData in anchorsData.itervalues():
                        if areaData.get(item.itemTypeID):
                            hasSlots = True
                            break
                    else:
                        hasSlots = False

                    if not hasSlots:
                        continue
                visibleTabs[seasonType].add(tabIndex)

    c11nContext.updateVisibleTabsList(visibleTabs)
    for tabIndex in self._proxy.tabsData.ALL:
        for seasonType in SeasonType.COMMON_SEASONS:
            seasonAndTabData = self._allSeasonAndTabFilterData[tabIndex][seasonType]
            seasonAndTabData.allGroups.append(i18n.makeString(VEHICLE_CUSTOMIZATION.CUSTOMIZATION_FILTER_ALLGROUPS))
            seasonAndTabData.selectedGroupIndex = len(seasonAndTabData.allGroups) - 1


@overrideMethod(CustomizationCarouselDataProvider, '_buildCustomizationItems')
def _buildCustomizationItems(_, self):
    buildFilterData(self)
    season = self._seasonID
    isBuy = self._proxy.isBuy
    requirement = createBaseRequirements(self._proxy, season)
    if not isBuy:
        requirement |= REQ_CRITERIA.CUSTOM(partial(isItemSuitableForTab, tabIndex=self._tabIndex))
    seasonAndTabData = self._allSeasonAndTabFilterData[self._tabIndex][season]
    allItemsGroup = len(seasonAndTabData.allGroups) - 1
    if seasonAndTabData.selectedGroupIndex != allItemsGroup:
        selectedGroup = seasonAndTabData.allGroups[seasonAndTabData.selectedGroupIndex]
        requirement |= REQ_CRITERIA.CUSTOMIZATION.ONLY_IN_GROUP(selectedGroup)
    if self._historicOnlyItems:
        criteria = REQ_CRITERIA.CUSTOMIZATION.HISTORICAL
        if isBuy:
            criteria = ~criteria
        requirement |= criteria
    if self._onlyOwnedAndFreeItems:
        requirement |= REQ_CRITERIA.CUSTOM(lambda x: self._proxy.getItemInventoryCount(x) > 0)
    if self._onlyAppliedItems:
        appliedItems = self._proxy.getAppliedItems(isOriginal=False)
        requirement |= REQ_CRITERIA.CUSTOM(lambda x: x.intCD in appliedItems)
    allItems = getItems(tabToItem(self._tabIndex, self._proxy.isBuy), self._proxy, requirement)
    self._customizationItems = []
    self._customizationBookmarks = []
    lastGroup = None
    for idx, item in enumerate(sorted(allItems.itervalues(), key=comparisonKey if isBuy else CSComparisonKey)):
        groupName = getGroupName(item)
        groupID = item.groupID
        group = groupID if isBuy else groupName
        if item.intCD == self._selectIntCD:
            self._selectedIdx = len(self._customizationItems)
            self._selectIntCD = None
        if group != lastGroup:
            lastGroup = group
            self._customizationBookmarks.append(
                CustomizationBookmarkVO((item.groupUserName if isBuy else groupName), idx).asDict())
        self._customizationItems.append(item.intCD)
        self._itemSizeData.append(item.isWide())
