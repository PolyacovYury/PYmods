import nations
import re
from CurrentVehicle import g_currentVehicle
from PYmodsCore import overrideMethod
from collections import defaultdict
from functools import partial
from gui.Scaleform.daapi.view.lobby.customization.customization_carousel import CustomizationBookmarkVO, \
    CustomizationCarouselDataProvider as WGCarouselDataProvider, CustomizationSeasonAndTypeFilterData
from gui.Scaleform.daapi.view.lobby.customization.shared import TABS_ITEM_TYPE_MAPPING, TYPE_TO_TAB_IDX, TYPES_ORDER, \
    C11nTabs, TABS_SLOT_TYPE_MAPPING, getAllParentProjectionSlots
from gui.Scaleform.locale.VEHICLE_CUSTOMIZATION import VEHICLE_CUSTOMIZATION
from gui.customization.shared import createCustomizationBaseRequestCriteria, C11N_ITEM_TYPE_MAP
from gui.shared.gui_items import GUI_ITEM_TYPE, ItemsCollection
from gui.shared.utils.requesters import REQ_CRITERIA
from helpers.i18n import makeString as _ms
from items.components.c11n_constants import SeasonType, ProjectionDecalFormTags
from items.vehicles import g_cache
from .shared import getItemSeason
from .. import g_config


class CustomizationCarouselDataProvider(WGCarouselDataProvider):
    def __init__(self, currentVehicle, carouselItemWrapper, proxy):
        super(CustomizationCarouselDataProvider, self).__init__(currentVehicle, carouselItemWrapper, proxy)
        self._selectedIdx = -1

    def updateTabGroups(self):
        self._allSeasonAndTabFilterData.clear()
        self._formfactorGroupsFilterByTabIndex.clear()
        availableTabs = set()
        visibleTabs = defaultdict(set)
        requirement = self._createBaseRequestCriteriaBySeason(None)
        allItems = self.getItems(GUI_ITEM_TYPE.CUSTOMIZATIONS, requirement)
        for tabIndex in C11nTabs.ALL:
            self._allSeasonAndTabFilterData[tabIndex] = {}
            if tabIndex == C11nTabs.PROJECTION_DECAL:
                self._formfactorGroupsFilterByTabIndex[tabIndex] = dict.fromkeys(ProjectionDecalFormTags.ALL_FACTORS, False)
            else:
                self._formfactorGroupsFilterByTabIndex[tabIndex] = {}
            for season in SeasonType.COMMON_SEASONS:
                self._allSeasonAndTabFilterData[tabIndex][season] = CustomizationSeasonAndTypeFilterData()

            slotType = TABS_SLOT_TYPE_MAPPING[tabIndex]
            if self.__hasSlots(slotType):
                availableTabs.add(tabIndex)

        isBuy = self._proxy.isBuy
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

        del self._customizationItems[:]
        del self._itemSizeData[:]
        del self._customizationBookmarks[:]
        self._selectedIdx = -1
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
        if self.service.getCtx().currentTab == C11nTabs.PROJECTION_DECAL:
            allFormsSet = set(ProjectionDecalFormTags.ALL_FACTORS)
            denyForms = [slot.getUnsupportedForms(self._currentVehicle.item) for slot in
                         getAllParentProjectionSlots(self._currentVehicle)]
            for form in denyForms:
                allFormsSet.intersection_update(form)

            requirement |= REQ_CRITERIA.CUSTOM(lambda x: not hasattr(x, 'formfactor') or x.formfactor not in allFormsSet)
        filteredItems = {k: v for k, v in items.iteritems() if requirement(v)}
        return filteredItems

    def _buildCustomizationItems(self):
        requirement = self._createBaseRequestCriteriaBySeason(self._seasonID)
        if not self._proxy.isBuy:
            requirement |= REQ_CRITERIA.CUSTOM(partial(self.isItemSuitableForTab, self._tabIndex))
        if self._allCustomizationItems is None:
            self._allCustomizationItems = {}
        else:
            self._allCustomizationItems.clear()
        self._allCustomizationItems.update(self.getItems(TABS_ITEM_TYPE_MAPPING[self._tabIndex], requirement))

        self._updateCustomizationItems()

    def _updateCustomizationItems(self):
        if self._allCustomizationItems is None:
            self._buildCustomizationItems()
            return
        filteredItems = self._applyFilter(self._allCustomizationItems, self._seasonID)
        del self._customizationItems[:]
        del self._customizationBookmarks[:]
        del self._itemSizeData[:]
        isBuy = self._proxy.isBuy
        lastGroup = None
        for item in sorted(filteredItems.itervalues(), key=self.CSComparisonKey):
            if isBuy and item.isHiddenInUI():
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

    def _createBaseRequestCriteriaBySeason(self, season):
        if self._proxy.isBuy:
            return createCustomizationBaseRequestCriteria(
                self._currentVehicle.item, self.eventsCache.questsProgress, self._proxy.getAppliedItems(), season)
        return REQ_CRITERIA.CUSTOM(lambda item: getItemSeason(item) & (season or SeasonType.ALL))

    def isItemSuitableForTab(self, tabIndex, item):
        if item is None or tabIndex != TYPE_TO_TAB_IDX[item.itemTypeID]:
            return False
        typeID = item.itemTypeID
        if typeID == GUI_ITEM_TYPE.STYLE:
            return item.mayInstall(g_currentVehicle.item) if item.modelsSet else all(
                self.isItemSuitableForTab(TYPE_TO_TAB_IDX[x.itemTypeID], x) for season in
                SeasonType.COMMON_SEASONS for x in item.getOutfit(season).items())
        if typeID == GUI_ITEM_TYPE.MODIFICATION:
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
        return (TYPES_ORDER.index(item.itemTypeID), item.priceGroup == 'custom', item.isHidden, isVictim, not is3D,
                not isGlobal, len(nationIDs) != 1, getGroupName(item, self._proxy.isBuy), item.isRare(), item.id)

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
