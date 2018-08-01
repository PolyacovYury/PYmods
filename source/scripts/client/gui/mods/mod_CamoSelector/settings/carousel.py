import nations
from CurrentVehicle import g_currentVehicle
from PYmodsCore import overrideMethod
from gui.Scaleform.daapi.view.lobby.customization.customization_carousel import CustomizationCarouselDataProvider, \
    CustomizationSeasonAndTypeFilterData, CustomizationBookmarkVO
from gui.Scaleform.daapi.view.lobby.customization.shared import TYPES_ORDER
from gui.Scaleform.genConsts.SEASONS_CONSTANTS import SEASONS_CONSTANTS
from gui.Scaleform.locale.VEHICLE_CUSTOMIZATION import VEHICLE_CUSTOMIZATION
from gui.shared.gui_items import GUI_ITEM_TYPE
from gui.shared.utils.requesters import REQ_CRITERIA
from helpers import i18n
from items.components.c11n_constants import SeasonType
from .. import g_config
from .shared import CSMode, CSTabs, ITEM_TO_TABS, tabToItem


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


def createBaseRequirements(season=None):
    season = season or SeasonType.ALL
    return REQ_CRITERIA.CUSTOM(lambda item: getItemSeason(item) & season)


def isItemSuitableForTab(item, tabIndex):
    if item is None or tabIndex not in ITEM_TO_TABS[item.itemTypeID]:
        return False
    if tabIndex in (CSTabs.EMBLEM, CSTabs.INSCRIPTION):
        return True
    vehicle = g_currentVehicle.item
    if tabIndex in (CSTabs.PAINT, CSTabs.EFFECT):
        return item.mayInstall(vehicle)
    isGlobal = g_config.isCamoGlobal(item.descriptor)
    return not (
        (tabIndex == CSTabs.CAMO_SHOP and (item.isHidden or item.priceGroup == 'custom')) or
        (tabIndex == CSTabs.CAMO_HIDDEN and (not item.isHidden or isGlobal or item.priceGroup == 'custom')) or
        (tabIndex == CSTabs.CAMO_GLOBAL and not isGlobal) or
        (tabIndex == CSTabs.CAMO_CUSTOM and item.priceGroup != 'custom'))



@overrideMethod(CustomizationCarouselDataProvider, '__init__')
def init(base, self, *a, **kw):
    base(self, *a, **kw)
    if self._proxy.mode == CSMode.BUY:
        return
    self._allSeasonAndTabFilterData = {}
    allItems = self.itemsCache.items.getItems(GUI_ITEM_TYPE.CUSTOMIZATIONS, createBaseRequirements())
    for tabIndex in CSTabs.ALL:
        self._allSeasonAndTabFilterData[tabIndex] = {}
        for season in SeasonType.COMMON_SEASONS:
            self._allSeasonAndTabFilterData[tabIndex][season] = CustomizationSeasonAndTypeFilterData()

        for item in sorted(allItems.itervalues(), key=CSComparisonKey):
            groupName = getGroupName(item)
            if isItemSuitableForTab(item, tabIndex):
                for seasonType in SeasonType.COMMON_SEASONS:
                    if getItemSeason(item) & seasonType:
                        seasonAndTabData = self._allSeasonAndTabFilterData[tabIndex][seasonType]
                        if groupName and groupName not in seasonAndTabData.allGroups:
                            seasonAndTabData.allGroups.append(groupName)
                        seasonAndTabData.itemCount += 1

        for seasonType in SeasonType.COMMON_SEASONS:
            seasonAndTabData = self._allSeasonAndTabFilterData[tabIndex][seasonType]
            seasonAndTabData.allGroups.append(i18n.makeString(VEHICLE_CUSTOMIZATION.CUSTOMIZATION_FILTER_ALLGROUPS))
            seasonAndTabData.selectedGroupIndex = len(seasonAndTabData.allGroups) - 1


@overrideMethod(CustomizationCarouselDataProvider, '_buildCustomizationItems')
def _buildCustomizationItems(base, self):
    if self._proxy.mode == CSMode.BUY:
        return base(self)
    season = self._seasonID
    requirement = createBaseRequirements(season) | REQ_CRITERIA.CUSTOM(
        lambda i: isItemSuitableForTab(i, self._tabIndex))
    seasonAndTabData = self._allSeasonAndTabFilterData[self._tabIndex][season]
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
    allItems = self.itemsCache.items.getItems(tabToItem(self._tabIndex), requirement)
    self._customizationItems = []
    self._customizationBookmarks = []
    lastGroupName = None
    for idx, item in enumerate(sorted(allItems.itervalues(), key=CSComparisonKey)):
        groupName = getGroupName(item)
        if item.intCD == self._selectIntCD:
            self._selectedIdx = len(self._customizationItems)
            self._selectIntCD = None
        if groupName != lastGroupName:
            lastGroupName = groupName
            self._customizationBookmarks.append(CustomizationBookmarkVO(groupName, idx).asDict())
        self._customizationItems.append(item.intCD)
        self._itemSizeData.append(item.isWide())
