from CurrentVehicle import g_currentVehicle
from PYmodsCore import overrideMethod
from collections import OrderedDict
from gui.Scaleform.daapi.view.lobby.customization.customization_carousel import (
    CustomizationBookmarkVO, CustomizationCarouselDataProvider as WGCarouselDP, CarouselData, CarouselCache as WGCache,
    ItemsData, FilterTypes)
from gui.Scaleform.daapi.view.lobby.customization.shared import (
    ITEM_TYPE_TO_TAB, CustomizationTabs, vehicleHasSlot, isItemLimitReached)
from gui.customization.constants import CustomizationModes
from gui.customization.shared import createCustomizationBaseRequestCriteria, C11N_ITEM_TYPE_MAP
from gui.shared.gui_items import GUI_ITEM_TYPE
from gui.shared.utils.requesters import REQ_CRITERIA
from gui.shared.utils.requesters.ItemsRequester import RequestCriteria
from items import vehicles
from items.components.c11n_constants import SeasonType, EMPTY_ITEM_ID
from .shared import getItemSeason, CSComparisonKey, getGroupName
from .. import g_config


class CustomizationCarouselDataProvider(WGCarouselDP):
    def onModeChanged(self, modeId, prevModeId):
        if CustomizationModes.EDITABLE_STYLE in (modeId, prevModeId):
            self.clearFilter()
            self.__selectedGroup.clear()
            self.invalidateFilteredItems()
        visibleTabs = self.getVisibleTabs()  # don't reset tab idx upon mode change, unless absolutely necessary
        if self.__ctx.mode.tabId not in visibleTabs:
            self.__ctx.mode.changeTab(visibleTabs[0])

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
            if not self.__ctx.isPurchase or not isItemLimitReached(item, outfits) or item.isStyleOnly:
                return item
            idx += shift
        return None

    def __initFilters(self):
        # noinspection PyUnresolvedReferences
        WGCarouselDP._CustomizationCarouselDataProvider__initFilters(self)
        self.__carouselFilters[FilterTypes.USED_UP]._SimpleCarouselFilter__criteria ^= REQ_CRITERIA.CUSTOM(
            lambda _: not self.__ctx.isPurchase)

    def __getSelectedGroupIdx(self):
        purchaseMode = self.__ctx.purchaseMode
        season, modeId, tabId = self.__ctx.season, self.__ctx.modeId, self.__ctx.mode.tabId
        selectedGroup = self.__selectedGroup.get(purchaseMode, {}).get(modeId, {}).get(season, {}).get(tabId)
        return selectedGroup

    def __setSelectedGroupIdx(self, index=None):
        purchaseMode = self.__ctx.purchaseMode
        season, modeId, tabId = self.__ctx.season, self.__ctx.modeId, self.__ctx.mode.tabId
        itemsData = self.__carouselCache.getItemsData()
        if index is not None and index >= len(itemsData.groups):
            index = None
        self.__selectedGroup.setdefault(purchaseMode, {}).setdefault(modeId, {}).setdefault(season, {})[tabId] = index

    def __createFilterCriteria(self):
        # noinspection PyUnresolvedReferences
        requirement = WGCarouselDP._CustomizationCarouselDataProvider__createFilterCriteria(self)
        isPurchase = self.__ctx.isPurchase
        groupIdx = self.__getSelectedGroupIdx()
        if groupIdx is not None:
            itemsData = self.__carouselCache.getItemsData()
            groupId = itemsData.groups.keys()[groupIdx]
            groupName = itemsData.groups[groupId]
            requirement = REQ_CRITERIA.CUSTOM(
                lambda item: groupName in getGroupName(item, isPurchase)) | RequestCriteria(*requirement.getConditions()[1:])
        return requirement


class CarouselCache(WGCache):
    def getVisibleTabs(self):
        visibleTabs = WGCache.getVisibleTabs(self)
        season, modeId = self.__ctx.season, self.__ctx.modeId
        if modeId != CustomizationModes.EDITABLE_STYLE:
            visibleTabs = (self.__itemsData[CustomizationModes.CUSTOM][season].keys(
            ) + self.__itemsData[CustomizationModes.STYLED][season].keys())
        return visibleTabs

    def __getCarouselData(self, season=None, modeId=None, tabId=None):
        itemsData = self.getItemsData(season, modeId, tabId)
        filteredItems = filter(self.__createFilterCriteria(), itemsData.items)
        carouselData = CarouselData()
        lastGroupID = None
        for item in filteredItems:
            isPurchase = self.__ctx.isPurchase
            groupName = getGroupName(item, isPurchase)
            group = item.groupID if isPurchase else groupName
            if group != lastGroupID:
                lastGroupID = group
                bookmarkVO = CustomizationBookmarkVO(group, len(carouselData.items))
                carouselData.bookmarks.append(bookmarkVO._asdict())
            carouselData.items.append(item.intCD)
            carouselData.sizes.append(item.isWide())

        return carouselData

    def __initItemsData(self):
        self.__itemsData.clear()
        if self.__ctx.isPurchase:
            requirement = createCustomizationBaseRequestCriteria(
                g_currentVehicle.item, self.__eventsCache.questsProgress, self.__ctx.mode.getAppliedItems()
            ) | REQ_CRITERIA.CUSTOM(lambda _item: not _item.isHiddenInUI())
        else:
            requirement = REQ_CRITERIA.CUSTOM(lambda _i: _i.descriptor.parentGroup is not None and (
                True if _i.itemTypeID != GUI_ITEM_TYPE.STYLE or not _i.modelsSet else _i.mayInstall(g_currentVehicle.item)))
        itemTypes = []
        for tabId, slotType in CustomizationTabs.SLOT_TYPES.iteritems():
            if vehicleHasSlot(slotType):
                itemTypes.extend(CustomizationTabs.ITEM_TYPES[tabId])

        allItems = []
        customizationCache = vehicles.g_cache.customization20().itemTypes
        cTypes = set((C11N_ITEM_TYPE_MAP[iType] for iType in itemTypes if iType in C11N_ITEM_TYPE_MAP))
        for cType in cTypes:
            for itemID in customizationCache[cType]:
                if itemID == EMPTY_ITEM_ID:
                    continue
                intCD = vehicles.makeIntCompactDescrByID('customizationItem', cType, itemID)
                item = self.__service.getItemByCD(intCD)
                if requirement(item):
                    allItems.append(item)

        sortedItems = sorted(allItems, key=CSComparisonKey)
        customModeTabs = CustomizationTabs.MODES[CustomizationModes.CUSTOM]
        for item in sortedItems:
            tabId = ITEM_TYPE_TO_TAB[item.itemTypeID]
            modeId = CustomizationModes.CUSTOM if tabId in customModeTabs else CustomizationModes.STYLED
            groupName = getGroupName(item, self.__ctx.isPurchase)
            for season in SeasonType.COMMON_SEASONS:
                if not (item.season if self.__ctx.isPurchase else getItemSeason(item)) & season:
                    continue
                itemsDataStorage = self.__itemsData[modeId][season]
                if not itemsDataStorage or tabId != itemsDataStorage.keys()[-1]:
                    itemsDataStorage[tabId] = ItemsData()
                itemsData = itemsDataStorage.values()[-1]
                for name in groupName.split(g_config.i18n['flashCol_group_separator']):
                    if name and name not in itemsData.groups:
                        itemsData.groups[name] = name
                itemsData.items.append(item)

    def __initEditableStyleItemsData(self):
        style = self.__ctx.mode.style
        if CustomizationModes.EDITABLE_STYLE in self.__itemsData:
            self.__itemsData[CustomizationModes.EDITABLE_STYLE].clear()
        vehicleCD = g_currentVehicle.item.descriptor.makeCompactDescr()
        itemsFilter = style.descriptor.isItemInstallable
        for season in SeasonType.COMMON_SEASONS:
            itemsDataStorage = self.__itemsData[CustomizationModes.CUSTOM][season]
            styleBaseOutfit = style.getOutfit(season, vehicleCD)
            styleBaseItems = [self.__service.getItemByCD(intCD) for intCD in styleBaseOutfit.items()]
            for tabId, itemsData in itemsDataStorage.iteritems():
                itemTypes = CustomizationTabs.ITEM_TYPES[tabId]
                filteredItems = [item for item in itemsData.items if itemsFilter(item.descriptor)]
                alternateItems = []
                for itemType in itemTypes:
                    c11nType = C11N_ITEM_TYPE_MAP[itemType]
                    alternateItemIds = style.descriptor.alternateItems.get(c11nType, ())
                    buf = [self.__service.getItemByID(itemType, itemId) for itemId in alternateItemIds]
                    alternateItems.extend([i for i in buf if i.itemTypeID in itemTypes])

                allItems = [item for item in filteredItems + alternateItems if item.season & season]
                if not allItems:
                    continue
                baseItems = [item for item in styleBaseItems if item.itemTypeID in itemTypes and item.season & season]
                allItems += baseItems
                items = sorted(set(allItems), key=CSComparisonKey)
                groups = OrderedDict()
                for item in items:
                    groupName = getGroupName(item, self.__ctx.isPurchase)
                    for name in groupName.split(g_config.i18n['flashCol_group_separator']):
                        if name and name not in groups:
                            groups[name] = name

                self.__itemsData[CustomizationModes.EDITABLE_STYLE][season][tabId] = ItemsData(items, groups)

        self.__cachedEditableStyleId = style.id


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
