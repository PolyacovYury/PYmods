from CurrentVehicle import g_currentVehicle
from OpenModsCore import overrideMethod
from gui.Scaleform.daapi.view.lobby.customization.customization_carousel import (
    CarouselCache as WGCache, CarouselData, CustomizationBookmarkVO, CustomizationCarouselDataProvider as WGCarouselDP,
    FilterTypes, ItemsData, _logger,
)
from gui.Scaleform.daapi.view.lobby.customization.shared import (
    CustomizationTabs, ITEM_TYPE_TO_TAB, isItemLimitReached, vehicleHasSlot,
)
from gui.customization.constants import CustomizationModes
from gui.customization.shared import C11N_ITEM_TYPE_MAP, createCustomizationBaseRequestCriteria
from gui.shared.gui_items import GUI_ITEM_TYPE
from gui.shared.utils.requesters import REQ_CRITERIA
from gui.shared.utils.requesters.ItemsRequester import RequestCriteria
from items import vehicles
from items.components.c11n_constants import EMPTY_ITEM_ID, SeasonType
from .shared import CSComparisonKey, getCriteria, getGroupName, getItemSeason
from .. import g_config
# noinspection PyUnresolvedReferences
from ..constants import CUSTOM_GROUP_NAME


class CustomizationCarouselDataProvider(WGCarouselDP):
    def getVisibleTabsForPurchase(self):
        return self.__carouselCache.getVisibleTabsForPurchase()

    def onModeChanged(self, modeId, prevModeId):
        visibleTabs = self.getVisibleTabs()  # don't reset tab idx upon mode change, unless absolutely necessary
        tabId = None
        if CustomizationModes.EDITABLE_STYLE in (modeId, prevModeId):
            self.clearFilter()
            self.__selectedGroup.clear()
            self.invalidateFilteredItems()
            if self.__ctx.mode.getDependenciesData():
                if CustomizationTabs.CAMOUFLAGES in visibleTabs:
                    tabId = CustomizationTabs.CAMOUFLAGES
                else:
                    _logger.warning('Style with dependencies have to open Camouflages tab, but this tab is not found!')
        if self.__ctx.mode.tabId not in visibleTabs or tabId is not None:
            self.__ctx.mode.changeTab(tabId or visibleTabs[0])

    def getNextItem(self, reverse):
        if self.__selectedItem.idx == -1:
            return None
        outfits = self.__ctx.mode.getModifiedOutfits()
        shift = -1 if reverse else 1
        itemsCount = len(self.collection)
        idx = self.__selectedItem.idx + shift
        while 0 <= idx < itemsCount:
            intCD = self.collection[idx]
            item = self.__service.getItemByCD(intCD)
            if (not self.__ctx.isPurchase or
                    not isItemLimitReached(item, outfits) or item.isStyleOnly and not self.processDependentParams(item)[1]):
                return item
            idx += shift
        return None

    def clearFilter(self):
        WGCarouselDP.clearFilter(self)
        self.__carouselFilters[FilterTypes.USED_UP].update(True)

    def __initFilters(self):
        # noinspection PyUnresolvedReferences
        WGCarouselDP._CustomizationCarouselDataProvider__initFilters(self)
        usedUpFilter = self.__carouselFilters[FilterTypes.USED_UP]
        usedUpFilter._SimpleCarouselFilter__criteria ^= REQ_CRITERIA.CUSTOM(lambda _: not self.__ctx.isPurchase)
        usedUpFilter.update(True)

    def __createFilterCriteria(self):
        # noinspection PyUnresolvedReferences
        requirement = WGCarouselDP._CustomizationCarouselDataProvider__createFilterCriteria(self)
        isPurchase = self.__ctx.isPurchase
        groupIdx = self.__getSelectedGroupIdx()
        if groupIdx is not None and groupIdx != -1:
            itemsData = self.__carouselCache.getItemsData()
            groupId = itemsData.groups.keys()[groupIdx]
            groupName = itemsData.groups[groupId]
            requirement = REQ_CRITERIA.CUSTOM(
                lambda item: groupName in getGroupName(item, isPurchase)) | RequestCriteria(*requirement.getConditions()[1:])
        if not isPurchase:
            requirement |= REQ_CRITERIA.CUSTOM(lambda item: item.intCD in self.__ctx.mode.getAppliedItems(False) or (
                item.season if self.__ctx.isPurchase else getItemSeason(item)) & self.__ctx.season)
        return requirement


class CarouselCache(WGCache):
    def getVisibleTabs(self):
        if self.__ctx.isPurchase and self.__ctx.modeId != CustomizationModes.EDITABLE_STYLE:
            return self.getVisibleTabsForPurchase()
        return WGCache.getVisibleTabs(self)

    def getVisibleTabsForPurchase(self):
        self.__initCache()
        return sum((self.__itemsData[mode][self.__ctx.season].keys() for mode in (
            CustomizationModes.CUSTOM, CustomizationModes.STYLED)), [])

    def __getCarouselData(self, season=None, modeId=None, tabId=None):
        itemsData = self.getItemsData(season, modeId, tabId)
        filteredItems = filter(self.__createFilterCriteria(), itemsData.items)
        sortCriteria = self.__createSortCriteria()
        if sortCriteria:
            filteredItems.sort(key=sortCriteria)
        carouselData = CarouselData()
        lastGroupID = None
        for item in filteredItems:
            carouselData.items.append(item.intCD)
            carouselData.sizes.append(item.isWide())
            if sortCriteria:
                continue
            isPurchase = self.__ctx.isPurchase
            groupName = getGroupName(item, isPurchase)
            group = item.groupID if isPurchase else groupName
            if group != lastGroupID:
                lastGroupID = group
                bookmarkVO = CustomizationBookmarkVO(group, len(carouselData.items) - 1)
                carouselData.bookmarks.append(bookmarkVO._asdict())
        return carouselData

    def __initItemsData(self):
        self.__itemsData.clear()
        purchaseRequirement = createCustomizationBaseRequestCriteria(
            g_currentVehicle.item, self.__eventsCache.questsProgress, self.__ctx.getMode().getAppliedItems()
        ) | REQ_CRITERIA.CUSTOM(lambda _item: not _item.isHiddenInUI())
        moddedRequirement = REQ_CRITERIA.CUSTOM(lambda _i: (
                _i.descriptor.parentGroup is not None and
                (_i.itemTypeID != GUI_ITEM_TYPE.STYLE or not _i.modelsSet or _i.mayInstall(g_currentVehicle.item))))
        itemTypes = []
        for tabId, slotType in CustomizationTabs.SLOT_TYPES.iteritems():
            if vehicleHasSlot(slotType):
                itemTypes.extend(CustomizationTabs.ITEM_TYPES[tabId])
        if self.__ctx._hangarSpace.space.getVehicleEntity().appearance._getThisVehicleDossierInsigniaRank():
            itemTypes.append(GUI_ITEM_TYPE.INSIGNIA)
        purchaseItems = []
        moddedItems = []
        customizationCache = vehicles.g_cache.customization20().itemTypes
        cTypes = set((C11N_ITEM_TYPE_MAP[iType] for iType in itemTypes if iType in C11N_ITEM_TYPE_MAP))
        for cType in cTypes:
            for itemID in customizationCache[cType]:
                if itemID == EMPTY_ITEM_ID:
                    continue
                item = self.__itemsCache.items.getItem(GUI_ITEM_TYPE.CUSTOMIZATION, cType, itemID)
                if purchaseRequirement(item):
                    purchaseItems.append(item)
                if moddedRequirement(item):
                    moddedItems.append(item)

        customModeTabs = CustomizationTabs.MODES[CustomizationModes.CUSTOM]
        for idx, sortedItems in enumerate((
                sorted(purchaseItems, key=CSComparisonKey(True, None)),
                sorted(moddedItems, key=CSComparisonKey(False, getCriteria(self.__ctx)))
        )):
            for item in sortedItems:
                tabId = ITEM_TYPE_TO_TAB[item.itemTypeID]
                modeId = CustomizationModes.CAMO_SELECTOR if idx else (
                    CustomizationModes.CUSTOM if tabId in customModeTabs else CustomizationModes.STYLED)
                groupName = getGroupName(item, not idx)
                for season in SeasonType.COMMON_SEASONS:
                    if not idx and not item.season & season:
                        continue
                    itemsDataStorage = self.__itemsData[modeId][season]
                    if not itemsDataStorage or tabId != itemsDataStorage.keys()[-1]:
                        itemsDataStorage[tabId] = ItemsData()
                    itemsData = itemsDataStorage.values()[-1]
                    for name in groupName.split(g_config.i18n['flashCol_group_separator']):
                        if name and name not in itemsData.groups:
                            itemsData.groups[name] = name
                    itemsData.items.append(item)


@overrideMethod(WGCarouselDP, '__new__')
def new(base, cls, *a, **kw):
    if not g_config.data['enabled']:
        return base(cls, *a, **kw)
    return base(CustomizationCarouselDataProvider, *a, **kw)


@overrideMethod(WGCache, '__new__')
def new(base, cls, *a, **kw):
    if not g_config.data['enabled']:
        return base(cls, *a, **kw)
    return base(CarouselCache, *a, **kw)
