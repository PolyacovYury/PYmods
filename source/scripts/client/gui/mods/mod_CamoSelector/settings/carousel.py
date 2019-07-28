import nations
import re
from CurrentVehicle import g_currentVehicle
from PYmodsCore import overrideMethod
from collections import defaultdict
from functools import partial
from gui.Scaleform.daapi.view.lobby.customization.customization_carousel import CustomizationBookmarkVO, \
    CustomizationCarouselDataProvider as WGCarouselDataProvider, CustomizationSeasonAndTypeFilterData
from gui.Scaleform.daapi.view.lobby.customization.shared import TABS_ITEM_TYPE_MAPPING, TYPE_TO_TAB_IDX, TYPES_ORDER, \
    C11nTabs, TABS_SLOT_TYPE_MAPPING
from gui.Scaleform.locale.VEHICLE_CUSTOMIZATION import VEHICLE_CUSTOMIZATION
from gui.shared.gui_items import GUI_ITEM_TYPE
from gui.shared.utils.requesters import REQ_CRITERIA
from helpers.i18n import makeString as _ms
from items.components.c11n_constants import SeasonType, ProjectionDecalFormTags
from .shared import getItemSeason
from .. import g_config


class CustomizationCarouselDataProvider(WGCarouselDataProvider):
    def __init__(self, currentVehicle, carouselItemWrapper, proxy):
        super(CustomizationCarouselDataProvider, self).__init__(currentVehicle, carouselItemWrapper, proxy)
        self._selectedIdx = -1

    def updateTabGroups(self):
        self.invalidateCache()
        self.invalidateFiltered()
        self._allSeasonAndTabFilterData.clear()
        self._formfactorGroupsFilterByTabIndex.clear()
        availableTabs = set()
        visibleTabs = defaultdict(set)
        isBuy = self._proxy.isBuy
        requirement = self._createBaseRequestCriteriaBySeason(None)
        allItems = self.itemsCache.items.getItems(GUI_ITEM_TYPE.CUSTOMIZATIONS, requirement, onlyWithPrices=isBuy)
        for tabIndex in C11nTabs.ALL:
            self._allSeasonAndTabFilterData[tabIndex] = {}
            if tabIndex == C11nTabs.PROJECTION_DECAL:
                self._formfactorGroupsFilterByTabIndex[tabIndex] = dict.fromkeys(ProjectionDecalFormTags.ALL, False)
            else:
                self._formfactorGroupsFilterByTabIndex[tabIndex] = {}
            for season in SeasonType.COMMON_SEASONS:
                self._allSeasonAndTabFilterData[tabIndex][season] = CustomizationSeasonAndTypeFilterData()

            slotType = TABS_SLOT_TYPE_MAPPING[tabIndex]
            if self.__hasSlots(slotType):
                availableTabs.add(tabIndex)

        for item in sorted(allItems.itervalues(), key=self.CSComparisonKey):
            if isBuy and item.isHiddenInUI():
                continue
            groupName = getGroupName(item, isBuy)
            tabIndex = TYPE_TO_TAB_IDX.get(item.itemTypeID)
            if tabIndex not in availableTabs or not self.isItemSuitableForTab(tabIndex, item):
                continue
            for seasonType in SeasonType.COMMON_SEASONS:
                if (item.season if isBuy else getItemSeason(item)) & seasonType:
                    seasonAndTabData = self._allSeasonAndTabFilterData[tabIndex][seasonType]
                    for name in groupName.split(g_config.i18n['flashCol_group_separator']):
                        if name and name not in seasonAndTabData.allGroups:
                            seasonAndTabData.allGroups.append(name)
                    seasonAndTabData.itemCount += 1
                    visibleTabs[seasonType].add(tabIndex)
        for tabIndex in C11nTabs.ALL:
            for seasonType in SeasonType.COMMON_SEASONS:
                seasonAndTabData = self._allSeasonAndTabFilterData[tabIndex][seasonType]
                seasonAndTabData.allGroups.append(_ms(VEHICLE_CUSTOMIZATION.CUSTOMIZATION_FILTER_ALLGROUPS))
                seasonAndTabData.selectedGroupIndex = len(seasonAndTabData.allGroups) - 1

        self.clear()
        self._proxy.updateVisibleTabsList(visibleTabs)

    def _applyFilter(self, items, season):
        isBuy = self._proxy.isBuy
        requirement = REQ_CRITERIA.EMPTY
        seasonAndTabData = self._allSeasonAndTabFilterData[self._tabIndex][season]
        allItemsGroup = len(seasonAndTabData.allGroups) - 1
        if seasonAndTabData.selectedGroupIndex != allItemsGroup:
            selectedGroup = seasonAndTabData.allGroups[seasonAndTabData.selectedGroupIndex]
            requirement |= REQ_CRITERIA.CUSTOM(lambda item: selectedGroup in getGroupName(item, isBuy))
        if self._historicOnlyItems:
            requirement |= ~REQ_CRITERIA.CUSTOMIZATION.HISTORICAL
        if self._onlyOwnedAndFreeItems:
            requirement |= REQ_CRITERIA.CUSTOM(lambda item: self._proxy.getItemInventoryCount(item) > 0)
        sub = REQ_CRITERIA.IN_CD_LIST(self._proxy.getAppliedItems(isOriginal=False))
        if self._onlyAppliedItems:
            requirement |= sub
        else:
            requirement ^= sub
        if any(self._formfactorGroupsFilterByTabIndex[self._tabIndex].itervalues()):
            formfactors = [formfactorGroup for formfactorGroup, value in
                           self._formfactorGroupsFilterByTabIndex[self._tabIndex].iteritems() if value]
            requirement |= REQ_CRITERIA.CUSTOM(lambda item: not hasattr(item, 'formfactor') or item.formfactor in formfactors)
        if self._propertySheetShow:
            slot = self.__ctx.selectedAnchor
            if slot.slotType == GUI_ITEM_TYPE.PROJECTION_DECAL:
                anchor = self._currentVehicle.item.getAnchorBySlotId(slot.slotType, slot.areaId, slot.regionIdx)
                requirement |= REQ_CRITERIA.CUSTOM(
                    lambda item: not hasattr(item, 'formfactor') or item.formfactor in anchor.formfactors)
        requirement |= REQ_CRITERIA.CUSTOM(lambda item: not self._proxy.isBuy or not item.isHiddenInUI())
        filteredItems = {k: v for k, v in items.iteritems() if requirement(v)}
        return filteredItems

    def _buildCustomizationItems(self):
        seasonID = self._seasonID
        tabIndex = self._tabIndex
        builtAllCustomizationItems = self._builtAllCustomizationItems
        if seasonID not in builtAllCustomizationItems or tabIndex not in builtAllCustomizationItems[seasonID]:
            allCustomizationItems = {}
            builtAllCustomizationItems.setdefault(seasonID, {})[tabIndex] = allCustomizationItems
            requirement = self._createBaseRequestCriteriaBySeason(seasonID)
            if not self._proxy.isBuy:
                requirement |= REQ_CRITERIA.CUSTOM(partial(self.isItemSuitableForTab, self._tabIndex))
            allCustomizationItems.update(self.itemsCache.items.getItems(
                TABS_ITEM_TYPE_MAPPING[tabIndex], requirement, onlyWithPrices=self._proxy.isBuy))

        items = self._builtCustomizationItems
        if seasonID not in items or tabIndex not in items[seasonID]:
            filteredItems = self._applyFilter(builtAllCustomizationItems[seasonID][tabIndex], self._seasonID)
            customizationItems = []
            customizationBookmarks = []
            itemSizeData = []
            isBuy = self._proxy.isBuy
            lastGroup = None
            for item in sorted(filteredItems.itervalues(), key=self.CSComparisonKey):
                groupName = getGroupName(item, isBuy)
                group = item.groupID if isBuy else groupName
                if group != lastGroup:
                    lastGroup = group
                    customizationBookmarks.append(CustomizationBookmarkVO(groupName, len(customizationItems)).asDict())
                customizationItems.append(item.intCD)
                itemSizeData.append(item.isWide())

            self._customizationItems = customizationItems
            self._customizationBookmarks = customizationBookmarks
            self._itemSizeData = itemSizeData
            items.setdefault(self._seasonID, {})[self._tabIndex] = (customizationItems, customizationBookmarks, itemSizeData)
        else:
            self._customizationItems, self._customizationBookmarks, self._itemSizeData = items[self._seasonID][self._tabIndex]
        self._selectedIdx = -1
        if self._selectIntCD in self._customizationItems:
            self._selectedIdx = self._customizationItems.index(self._selectIntCD)
        self._proxy.setCarouselItems(self.collection)

    def _createBaseRequestCriteriaBySeason(self, season):
        if self._proxy.isBuy:
            return super(CustomizationCarouselDataProvider, self)._createBaseRequestCriteriaBySeason(season)
        return REQ_CRITERIA.CUSTOM(lambda item: getItemSeason(item) & (season or SeasonType.ALL))

    def isItemSuitableForTab(self, tabIndex, item):
        if item is None or tabIndex != TYPE_TO_TAB_IDX[item.itemTypeID]:
            return False
        if item.itemTypeID == GUI_ITEM_TYPE.STYLE and item.modelsSet:
            return item.mayInstall(g_currentVehicle.item)
        return True

    def CSComparisonKey(self, item):
        nationIDs = [n for filterNode in getattr(item.descriptor.filter, 'include', ()) for n in filterNode.nations or []]
        is3D, isVictim, isGlobal = False, False, False
        if item.itemTypeID == GUI_ITEM_TYPE.STYLE:
            if item.modelsSet:
                is3D = True
            if any('Victim' in tag for tag in item.tags):
                isVictim = True
        if item.itemTypeID == GUI_ITEM_TYPE.CAMOUFLAGE:
            if 'victim' in item.descriptor.userKey:
                isVictim = True
            isGlobal = g_config.isCamoGlobal(item.descriptor)
        return (TYPES_ORDER.index(item.itemTypeID), not is3D, item.priceGroup == 'custom', item.isHidden, isVictim,
                not isGlobal, len(nationIDs) != 1, getGroupName(item, self._proxy.isBuy), item.isRare(), item.id)


def getGroupName(item, isBuy=False):
    group = item.groupUserName
    if isBuy:
        return group
    if item.itemTypeID == GUI_ITEM_TYPE.STYLE:
        if item.modelsSet:
            group = _ms('#vehicle_customization:styles/unique_styles')
        if any('Victim' in tag for tag in item.tags):
            group = _ms('#vehicle_customization:victim_style/default')
    if item.itemTypeID == GUI_ITEM_TYPE.CAMOUFLAGE:
        if 'victim' in item.descriptor.userKey:
            group = _ms('#vehicle_customization:victim_style/default')
    nationIDs = [n for filterNode in getattr(item.descriptor.filter, 'include', ()) for n in filterNode.nations or []]
    nation = ''
    if len(nationIDs) == 1:
        nation = _ms('#vehicle_customization:repaint/%s_base_color' % nations.NAMES[nationIDs[0]])
    elif len(nationIDs) > 1:
        nation = g_config.i18n['flashCol_group_multinational']
    if group and nation:  # HangarPainter support
        group = re.sub(r'( [^ <>]+)(?![^ <>]*>)', '', nation) + g_config.i18n['flashCol_group_separator'] + group
    return group


@overrideMethod(WGCarouselDataProvider, '__new__')
def new(base, cls, *a, **kw):
    if not g_config.data['enabled']:
        return base(cls, *a, **kw)
    return base(CustomizationCarouselDataProvider, *a, **kw)
