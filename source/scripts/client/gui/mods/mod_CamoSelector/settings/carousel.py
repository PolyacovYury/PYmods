import nations
from gui.Scaleform.daapi.view.lobby.customization.customization_carousel import CustomizationBookmarkVO, \
    CustomizationSeasonAndTypeFilterData, comparisonKey
from gui.Scaleform.framework.entities.DAAPIDataProvider import SortableDAAPIDataProvider
from gui.Scaleform.genConsts.SEASONS_CONSTANTS import SEASONS_CONSTANTS
from gui.Scaleform.locale.VEHICLE_CUSTOMIZATION import VEHICLE_CUSTOMIZATION
from gui.shared.gui_items import GUI_ITEM_TYPE
from gui.shared.utils.requesters import REQ_CRITERIA
from helpers import dependency
from helpers.i18n import makeString as _ms
from items.components.c11n_constants import SeasonType
from items.vehicles import g_cache
from skeletons.gui.shared import IItemsCache
from . import g_config
from .shared import C11nTabs, isCamoInternational, tabToItem, ITEM_TO_TABS


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


def _createBaseRequirements(season=None):
    season = season or SeasonType.ALL
    return REQ_CRITERIA.CUSTOM(lambda item: getItemSeason(item) & season)


class CustomizationCarouselDataProvider(SortableDAAPIDataProvider):
    itemsCache = dependency.descriptor(IItemsCache)

    def __init__(self, currentVehicle, carouselItemWrapper, proxy):
        super(CustomizationCarouselDataProvider, self).__init__()
        self._currentVehicle = currentVehicle
        self._tabIndex = 0
        self._seasonID = SeasonType.SUMMER
        self._onlyOwnedAndFreeItems = False
        self._historicOnlyItems = False
        self._onlyAppliedItems = False
        self._selectIntCD = None
        self.setItemWrapper(carouselItemWrapper)
        self._proxy = proxy
        self._currentlyApplied = set()
        self._allSeasonAndTabFilterData = {}
        allItems = self._getAllItems(_createBaseRequirements())
        for tabIndex in C11nTabs.ALL:
            self._allSeasonAndTabFilterData[tabIndex] = {}
            for season in SeasonType.COMMON_SEASONS:
                self._allSeasonAndTabFilterData[tabIndex][season] = CustomizationSeasonAndTypeFilterData()

        for item in sorted(allItems.itervalues(), key=comparisonKey):
            groupName = getGroupName(item)
            for tabIndex in C11nTabs.ALL:
                if self.isItemSuitableForTab(item, tabIndex):
                    for seasonType in SeasonType.COMMON_SEASONS:
                        if item.season & seasonType:
                            seasonAndTabData = self._allSeasonAndTabFilterData[tabIndex][seasonType]
                            if groupName and groupName not in seasonAndTabData.allGroups:
                                seasonAndTabData.allGroups.append(groupName)
                            seasonAndTabData.itemCount += 1

        for tabIndex in C11nTabs.ALL:
            for seasonType in SeasonType.COMMON_SEASONS:
                seasonAndTabData = self._allSeasonAndTabFilterData[tabIndex][seasonType]
                seasonAndTabData.allGroups.append(_ms(VEHICLE_CUSTOMIZATION.CUSTOMIZATION_FILTER_ALLGROUPS))
                seasonAndTabData.selectedGroupIndex = len(seasonAndTabData.allGroups) - 1

        self._customizationItems = []
        self._itemSizeData = []
        self._customizationBookmarks = []
        self._selectedIdx = -1

    def clear(self):
        del self._customizationItems[:]
        del self._itemSizeData[:]
        del self._customizationBookmarks[:]
        self._selectedIdx = -1

    def fini(self):
        self.clear()
        self.destroy()

    def pyGetSelectedIdx(self):
        return self._selectedIdx

    @property
    def collection(self):
        return self._customizationItems

    def emptyItem(self):
        return None

    def getItemSizeData(self):
        return self._itemSizeData

    def getSeasonAndTabData(self, tabIndex, seasonType):
        return self._allSeasonAndTabFilterData[tabIndex][seasonType]

    def getBookmarkData(self):
        return self._customizationBookmarks

    @property
    def itemCount(self):
        return len(self._customizationItems)

    @property
    def totalItemCount(self):
        seasonAndTabData = self._allSeasonAndTabFilterData[self._tabIndex][self._seasonID]
        return seasonAndTabData.itemCount

    def clearFilter(self):
        self._onlyOwnedAndFreeItems = False
        self._historicOnlyItems = False
        self._onlyAppliedItems = False
        seasonAndTabData = self._allSeasonAndTabFilterData[self._tabIndex][self._seasonID]
        seasonAndTabData.selectedGroupIndex = len(seasonAndTabData.allGroups) - 1
        self.buildList(self._tabIndex, self._seasonID)

    def selectItem(self, item=None):
        """ Select a Customization Item by item itself.
        """
        if not item:
            self._selectIntCD = None
        else:
            self._selectIntCD = item.intCD

    def selectItemIdx(self, itemIndex):
        """ Select a Customization Item by index.

        :param itemIndex: index in the carousel of the selected item
        """
        self._selectedIdx = itemIndex
        self.refresh()

    def refresh(self):
        self._currentlyApplied = self._proxy.getAppliedItems(isOriginal=False)
        super(CustomizationCarouselDataProvider, self).refresh()

    def getFilterData(self):
        seasonAndTabData = self._allSeasonAndTabFilterData[self._tabIndex][self._seasonID]
        return {'purchasedEnabled': self._onlyOwnedAndFreeItems,
                'historicEnabled': self._historicOnlyItems,
                'appliedEnabled': self._onlyAppliedItems,
                'groups': seasonAndTabData.allGroups,
                'selectedGroup': seasonAndTabData.selectedGroupIndex,
                'groupCount': len(seasonAndTabData.allGroups)}

    def getCurrentlyApplied(self):
        return self._currentlyApplied

    def buildList(self, tabIndex, season, refresh=True):
        self._tabIndex = tabIndex
        self._seasonID = season
        self.clear()
        self._buildCustomizationItems()
        if refresh:
            self.refresh()

    def setActiveGroupIndex(self, index):
        seasonAndTabData = self._allSeasonAndTabFilterData[self._tabIndex][self._seasonID]
        seasonAndTabData.selectedGroupIndex = index

    def setHistoricalFilter(self, value):
        self._historicOnlyItems = value

    def setOwnedFilter(self, value):
        self._onlyOwnedAndFreeItems = value

    def setAppliedFilter(self, value):
        self._onlyAppliedItems = value

    def getOwnedFilter(self):
        return self._onlyOwnedAndFreeItems

    def getAppliedFilter(self):
        return self._onlyAppliedItems

    def _dispose(self):
        del self._customizationItems[:]
        del self._itemSizeData[:]
        del self._customizationBookmarks[:]
        super(CustomizationCarouselDataProvider, self)._dispose()

    def _getAllItems(self, requirement):
        paints = g_cache.customization20().paints.values()
        camouflages = g_cache.customization20().camouflages.values()
        decals = g_cache.customization20().decals.values()
        effects = g_cache.customization20().modifications.values()
        return {item.intCD: item for item in
                (self.itemsCache.items.getItemByCD(item.compactDescr) for item in paints + camouflages + decals + effects) if
                requirement(item)}

    def isItemSuitableForTab(self, item, tabIndex):
        if item is None:
            return False
        ct = C11nTabs
        if tabIndex not in ct.PAINT + ct.CAMO:
            return item.itemTypeID in (GUI_ITEM_TYPE.EMBLEM, GUI_ITEM_TYPE.INSCRIPTION, GUI_ITEM_TYPE.MODIFICATION) and \
                   tabIndex in ITEM_TO_TABS[item.itemTypeID]
        vehicle = self._currentVehicle.item
        if tabIndex in ct.PAINT:
            return item.itemTypeID == GUI_ITEM_TYPE.PAINT and item.mayInstall(vehicle) and (tabIndex == ct.PAINT_SHOP) == \
                   (item.priceGroup != 'custom')
        isInter = isCamoInternational(item.descriptor)
        return (item.itemTypeID == GUI_ITEM_TYPE.CAMOUFLAGE) and not (
                (tabIndex == ct.CAMO_SHOP and (item.isHidden or item.priceGroup == 'custom')) or
                (tabIndex == ct.CAMO_HIDDEN and (not item.isHidden or isInter or item.priceGroup == 'custom')) or
                (tabIndex == ct.CAMO_GLOBAL and not isInter) or
                (tabIndex == ct.CAMO_CUSTOM and item.priceGroup != 'custom'))

    def _buildCustomizationItems(self):
        season = self._seasonID
        requirement = _createBaseRequirements(season) | REQ_CRITERIA.CUSTOM(
            lambda i: self.isItemSuitableForTab(i, self._tabIndex))
        seasonAndTabData = self._allSeasonAndTabFilterData[self._tabIndex][self._seasonID]
        allItemsGroup = len(seasonAndTabData.allGroups) - 1
        if seasonAndTabData.selectedGroupIndex != allItemsGroup:
            selectedGroup = seasonAndTabData.allGroups[seasonAndTabData.selectedGroupIndex]
            requirement |= REQ_CRITERIA.CUSTOMIZATION.ONLY_IN_GROUP(selectedGroup)
        if self._historicOnlyItems:
            requirement |= REQ_CRITERIA.CUSTOMIZATION.HISTORICAL
        if self._onlyOwnedAndFreeItems:
            requirement |= REQ_CRITERIA.CUSTOM(lambda x: self._proxy.getItemInventoryCount(x) > 0)
        if self._onlyAppliedItems:
            appliedItems = self._proxy.getAppliedItems(isOriginal=False)
            requirement |= REQ_CRITERIA.CUSTOM(lambda x: x.intCD in appliedItems)
        allItems = self._getAllItems(requirement)
        self._customizationItems = []
        self._customizationBookmarks = []
        lastGroupName = None
        for idx, item in enumerate(sorted(allItems.itervalues(), key=comparisonKey)):
            groupName = getGroupName(item)
            if item.intCD == self._selectIntCD:
                self._selectedIdx = len(self._customizationItems)
                self._selectIntCD = None
            if groupName != lastGroupName:
                lastGroupName = groupName
                self._customizationBookmarks.append(CustomizationBookmarkVO(groupName, idx).asDict())
            self._customizationItems.append(item.intCD)
            self._itemSizeData.append(item.isWide())


def getGroupName(item):
    groupName = item.groupUserName
    nationIDs = []
    if item.descriptor.filter:
        for filterNode in item.descriptor.filter.include:
            if filterNode.nations:
                nationIDs += filterNode.nations
    if len(nationIDs) == 1:
        nationUserName = _ms('#vehicle_customization:repaint/%s_base_color' % nations.NAMES[nationIDs[0]])
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
        groupName = ' / '.join((nationUserName, groupName))
    return groupName
