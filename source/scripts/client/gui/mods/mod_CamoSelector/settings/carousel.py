import nations
import re
from CurrentVehicle import g_currentVehicle
from PYmodsCore import overrideMethod
from collections import OrderedDict
from gui.Scaleform.daapi.view.lobby.customization.customization_carousel import (
    CustomizationBookmarkVO, CustomizationCarouselDataProvider as WGCarouselDP, CarouselData, CarouselCache as WGCache,
    ItemsData)
from gui.Scaleform.daapi.view.lobby.customization.shared import (
    ITEM_TYPE_TO_TAB, TYPES_ORDER, CustomizationTabs, vehicleHasSlot)
from gui.customization.constants import CustomizationModes
from gui.customization.shared import createCustomizationBaseRequestCriteria, C11N_ITEM_TYPE_MAP
from gui.shared.gui_items import GUI_ITEM_TYPE
from gui.shared.utils.requesters import REQ_CRITERIA
from gui.shared.utils.requesters.ItemsRequester import PredicateCondition
from helpers import dependency
from helpers.i18n import makeString as _ms
from items import vehicles
from items.components.c11n_constants import SeasonType, ProjectionDecalFormTags, ItemTags, EMPTY_ITEM_ID
from skeletons.gui.customization import ICustomizationService
from .. import g_config


class CustomizationCarouselDataProvider(WGCarouselDP):
    def onModeChanged(self, modeId, prevModeId):
        if CustomizationModes.EDITABLE_STYLE in (modeId, prevModeId):
            self.clearFilter()
            self.__selectedGroup.clear()
            self.invalidateFilteredItems()
        self.getVisibleTabs()  # don't reset tab idx upon mode change

    def __createFilterCriteria(self):
        # noinspection PyUnresolvedReferences
        requirement = WGCarouselDP._CustomizationCarouselDataProvider__createFilterCriteria(self)
        isBuy = self.__ctx.isBuy
        groupIdx = self.__getSelectedGroupIdx()
        if groupIdx is not None:
            itemsData = self.__carouselCache.getItemsData()
            groupId = itemsData.groups.keys()[groupIdx]
            groupName = itemsData.groups[groupId]
            requirement._contitions[0] = PredicateCondition(lambda item: groupName in getGroupName(item, isBuy))
        return requirement


class CarouselCache(WGCache):
    def getVisibleTabs(self):
        visibleTabs = super(CarouselCache, self).getVisibleTabs()
        season, modeId = self.__ctx.season, self.__ctx.modeId
        if not self.__ctx.isBuy and modeId != CustomizationModes.EDITABLE_STYLE:
            visibleTabs = (self.__itemsData[CustomizationModes.CUSTOM][season].keys(
            ) + self.__itemsData[CustomizationModes.STYLED][season].keys())
        return visibleTabs

    def __getCarouselData(self, season=None, modeId=None, tabId=None):
        itemsData = self.getItemsData(season, modeId, tabId)
        filteredItems = filter(self.__createFilterCriteria(), itemsData.items)
        carouselData = CarouselData()
        lastGroupID = None
        for item in filteredItems:
            if item.groupID != lastGroupID:
                lastGroupID = item.groupID
                bookmarkVO = CustomizationBookmarkVO(getGroupName(item, self.__ctx.isBuy), len(carouselData.items))
                carouselData.bookmarks.append(bookmarkVO._asdict())
            carouselData.items.append(item.intCD)
            carouselData.sizes.append(item.isWide())

        return carouselData

    def __initItemsData(self):
        self.__itemsData.clear()
        if self.__ctx.isBuy:
            requirement = createCustomizationBaseRequestCriteria(
                g_currentVehicle.item, self.__eventsCache.questsProgress, self.__ctx.mode.getAppliedItems()
            ) | REQ_CRITERIA.CUSTOM(lambda _item: not _item.isHiddenInUI())
        else:
            requirement = REQ_CRITERIA.CUSTOM(lambda _item: _item.parentGroup is not None)
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
            for season in SeasonType.COMMON_SEASONS:
                if not item.season & season:
                    continue
                itemsDataStorage = self.__itemsData[modeId][season]
                if not itemsDataStorage or tabId != itemsDataStorage.keys()[-1]:
                    itemsDataStorage[tabId] = ItemsData()
                itemsData = itemsDataStorage.values()[-1]
                if not itemsData.groups or item.groupID != itemsData.groups.keys()[-1]:
                    itemsData.groups[item.groupID] = getGroupName(item, self.__ctx.isBuy)
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
                    if not groups or item.groupID != groups.keys()[-1]:
                        groups[item.groupID] = getGroupName(item, self.__ctx.isBuy)

                self.__itemsData[CustomizationModes.EDITABLE_STYLE][season][tabId] = ItemsData(items, groups)

        self.__cachedEditableStyleId = style.id


@dependency.replace_none_kwargs(service=ICustomizationService)
def CSComparisonKey(item, service=None):
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
    return (TYPES_ORDER.index(item.itemTypeID) if item.itemTypeID in TYPES_ORDER else 0, not is3D,
            ItemTags.NATIONAL_EMBLEM not in item.tags, item.priceGroup == 'custom', item.isHidden, isVictim, not isGlobal,
            len(nationIDs) != 1, getGroupName(item, service.getCtx().isBuy), item.isRare(),
            0 if not hasattr(item, 'formfactor') else ProjectionDecalFormTags.ALL.index(item.formfactor), item.id)


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


@overrideMethod(WGCarouselDP, '__new__')
def new(base, cls, *a, **kw):
    if not g_config.data['enabled']:
        return base(cls, *a, **kw)
    return base(CustomizationCarouselDataProvider, *a, **kw)
