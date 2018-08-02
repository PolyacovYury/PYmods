from CurrentVehicle import g_currentVehicle
from PYmodsCore import overrideMethod, loadJson
from collections import defaultdict
from functools import partial
from gui import g_tankActiveCamouflage, SystemMessages
from gui.Scaleform.daapi.view.lobby.customization.customization_carousel import comparisonKey
from gui.Scaleform.daapi.view.lobby.customization.shared import C11nTabs, SEASON_TYPE_TO_IDX, SEASON_IDX_TO_TYPE, \
    SEASON_TYPE_TO_NAME, getOutfitWithoutItems, TYPE_TO_TAB_IDX
from gui.Scaleform.genConsts.SEASONS_CONSTANTS import SEASONS_CONSTANTS
from gui.Scaleform.locale.SYSTEM_MESSAGES import SYSTEM_MESSAGES
from gui.customization.context import CustomizationContext, CustomizationRegion, CaruselItemData
from gui.customization.shared import createCustomizationBaseRequestCriteria
from gui.shared.gui_items import GUI_ITEM_TYPE, GUI_ITEM_TYPE_NAMES
from gui.shared.gui_items.customization.outfit import Area
from gui.shared.gui_items.processors.common import OutfitApplier, StyleApplier, CustomizationsSeller
from gui.shared.utils.decorators import process
from items.components.c11n_constants import SeasonType
from shared_utils import nextTick, first, findFirst
from vehicle_systems.tankStructure import TankPartIndexes
from .carousel import CSComparisonKey, createBaseRequirements, isItemSuitableForTab, getItemSeason
from .shared import CSMode, CSTabs
from .. import g_config
from ..constants import RandMode

CustomizationContext.tabsData = property(lambda self: C11nTabs if self._mode == CSMode.BUY else CSTabs)
CustomizationContext.originalOutfits = property(
    lambda self: self._originalOutfits if self._mode == CSMode.BUY else self._originalCSOutfits)
CustomizationContext.modifiedOutfits = property(
    lambda self: self._modifiedOutfits if self._mode == CSMode.BUY else self._modifiedCSOutfits)
CustomizationContext.getSeasonIndices = lambda self: [
    SEASON_TYPE_TO_IDX[x] for x in SeasonType.COMMON_SEASONS if x & self._settingSeason]
CustomizationContext.changeAlly = lambda self, apply: (
    setattr(self, 'useForAlly', apply), _updateCurrentSettings(self), self.onCacheResync())
CustomizationContext.changeEnemy = lambda self, apply: (
    setattr(self, 'useForEnemy', apply), _updateCurrentSettings(self), self.onCacheResync())


@overrideMethod(CustomizationContext, 'modifiedStyle', decorator=property)
def modifiedStyle(_, self):
    return self._modifiedStyle if self._mode == CSMode.BUY else self._modifiedCSStyle


@overrideMethod(CustomizationContext, '__init__')
def _init(base, self):
    base(self)
    self._originalMode = CSMode.BUY
    self._mode = self._originalMode
    self._lastTab = {CSMode.BUY: C11nTabs.PAINT, CSMode.INSTALL: CSTabs.CAMO_SHOP, CSMode.SETUP: CSTabs.CAMO_SHOP}
    self._originalCSOutfits = {}
    self._modifiedCSOutfits = {}
    self._originalCSStyle = None
    self._modifiedCSStyle = None
    self._settingsOutfit = None
    self._currentSettings = {}
    self._settingSeason = None
    self._randMode = None
    self.useForAlly = False
    self.useForEnemy = False


@overrideMethod(CustomizationContext, 'refreshOutfit')
def refreshOutfit(_, self):
    if self._mode == CSMode.BUY:
        if self._tabIndex == C11nTabs.STYLE:
            if self._modifiedStyle:
                self._currentOutfit = self._modifiedStyle.getOutfit(self._currentSeason)
            else:
                self._currentOutfit = self.service.getEmptyOutfit()
        else:
            self._currentOutfit = self._modifiedOutfits[self._currentSeason]
    elif self._mode == CSMode.INSTALL:
        if self._tabIndex == CSTabs.STYLE:
            if self._modifiedCSStyle:
                self._currentOutfit = self._modifiedCSStyle.getOutfit(self._currentSeason)
            else:
                self._currentOutfit = self.service.getEmptyOutfit()
        else:
            self._currentOutfit = self._modifiedCSOutfits[self._currentSeason]
    else:  # self._mode == CSMode.SETUP
        self._currentOutfit = self._settingsOutfit
    self.service.tryOnOutfit(self._currentOutfit)
    g_tankActiveCamouflage[g_currentVehicle.item.intCD] = self._currentSeason


@overrideMethod(CustomizationContext, 'tabChanged')
def tabChanged(_, self, tabIndex):
    self._tabIndex = tabIndex
    if self._tabIndex == self.tabsData.EFFECT:
        self._selectedRegion = CustomizationRegion(slotType=GUI_ITEM_TYPE.MODIFICATION, areaId=Area.MISC, regionIdx=0)
    elif self._tabIndex == self.tabsData.STYLE:
        self._selectedRegion = CustomizationRegion(slotType=GUI_ITEM_TYPE.STYLE, areaId=Area.CHASSIS, regionIdx=0)
    else:
        self._selectedRegion = CustomizationRegion()
    self._selectedCaruselItem = CaruselItemData()
    self.onCustomizationTabChanged(tabIndex)


@overrideMethod(CustomizationContext, 'regionSelected')
def regionSelected(_, self, slotType, areaId, regionIdx):
    if self._mode == CSMode.SETUP or self._tabIndex in (self.tabsData.EFFECT, self.tabsData.STYLE):
        return
    self._selectedRegion = CustomizationRegion(slotType=slotType, areaId=areaId, regionIdx=regionIdx)
    self.onCustomizationRegionSelected(self._selectedRegion.slotType, self._selectedRegion.areaId,
                                       self._selectedRegion.regionIdx)
    if areaId != -1 and regionIdx != -1 and self._selectedCaruselItem.intCD != -1:
        self.installItem(self._selectedCaruselItem.intCD, areaId, slotType, regionIdx, SEASON_TYPE_TO_IDX[self.currentSeason])


@overrideMethod(CustomizationContext, 'installItem')
def installItem(_, self, intCD, areaId, slotType, regionId, seasonIdx, component=None):
    item = self.service.getItemByCD(intCD)
    if self._mode == CSMode.BUY and item.isHidden and not self.getItemInventoryCount(item):
        SystemMessages.pushI18nMessage(SYSTEM_MESSAGES.CUSTOMIZATION_PROHIBITED, type=SystemMessages.SM_TYPE.Warning,
                                       itemName=item.userName)
        return False
    if self._mode == CSMode.BUY:
        if slotType == GUI_ITEM_TYPE.STYLE:
            self._modifiedStyle = item
        else:
            season = SEASON_IDX_TO_TYPE.get(seasonIdx, self._currentSeason)
            outfit = self._modifiedOutfits[season]
            outfit.getContainer(areaId).slotFor(slotType).set(item, idx=regionId, component=component)
            outfit.invalidate()
    elif self._mode == CSMode.INSTALL:
        if slotType == GUI_ITEM_TYPE.STYLE:
            self._modifiedCSStyle = item
        else:
            season = SEASON_IDX_TO_TYPE.get(seasonIdx, self._currentSeason)
            outfit = self._modifiedCSOutfits[season]
            outfit.getContainer(areaId).slotFor(slotType).set(item, idx=regionId, component=component)
            outfit.invalidate()
    else:
        outfit = self._setupOutfit
        for areaId in xrange(1, 4):
            outfit.getContainer(areaId).slotFor(slotType).set(item, idx=regionId, component=component)
        itemSettings, _, itemSeasons, itemOrigSettings = getItemSettings(self, item)
        self._settingSeason = itemSeasons
        self._randMode = itemSettings.get('random_mode', itemOrigSettings.get('random_mode', RandMode.RANDOM))
        self.useForAlly = itemSettings.get('useForAlly', itemOrigSettings.get('useForAlly', True))
        self.useForEnemy = itemSettings.get('useForEnemy', itemOrigSettings.get('useForEnemy', True))

    self.refreshOutfit()
    self.onCustomizationItemInstalled()
    return True


@overrideMethod(CustomizationContext, 'removeItemFromRegion')
def removeItemFromRegion(self, season, areaId, slotType, regionId):
    outfit = (self._modifiedOutfits if self._mode == CSMode.BUY else self._modifiedCSOutfits)[season]
    slot = outfit.getContainer(areaId).slotFor(slotType)
    if slot.capacity() > regionId:
        slot.remove(idx=regionId)
    self.refreshOutfit()
    self.onCustomizationItemsRemoved()


@overrideMethod(CustomizationContext, 'removeStyle')
def removeStyle(self, intCD):
    if self._mode == CSMode.BUY:
        if self._modifiedStyle and self._modifiedStyle.intCD == intCD:
            self._modifiedStyle = None
    elif self._mode == CSMode.INSTALL:
        if self._modifiedCSStyle and self._modifiedCSStyle.intCD == intCD:
            self._modifiedCSStyle = None
    self.refreshOutfit()
    self.onCustomizationItemsRemoved()


@overrideMethod(CustomizationContext, 'removeItems')
def removeItems(self, onlyCurrent, *intCDs):
    def intCdFilter(item):
        return item.intCD in intCDs

    if onlyCurrent:
        self.removeItemsFromOutfit(self._currentOutfit, intCdFilter, False)
    else:
        for outfit in self.modifiedOutfits.itervalues():
            self.removeItemsFromOutfit(outfit, intCdFilter, False)
    self.refreshOutfit()
    self.onCustomizationItemsRemoved()


@overrideMethod(CustomizationContext, 'switchToCustom')
def switchToCustom(_, self):
    changeMode(self, False)


@overrideMethod(CustomizationContext, 'switchToStyle')
def switchToStyle(_, self):
    changeMode(self, True)


def changeMode(self, wasLeft):
    self._lastTab[self._mode] = self._tabIndex
    self._mode = ((self._mode + 1) if wasLeft else (self._mode - 1 + len(CSMode.NAMES))) % len(CSMode.NAMES)
    self._tabIndex = self._lastTab[self._mode]
    self._CustomizationContext__updateVisibleTabsList()
    if self._tabIndex not in self.visibleTabs:
        self._tabIndex = first(self.visibleTabs, -1)
    self.refreshOutfit()
    self.onCustomizationModeChanged(self._mode)
    self.onCustomizationTabChanged(self._tabIndex)


@overrideMethod(CustomizationContext, 'cancelChanges')
def cancelChanges(_, self):
    if self._tabIndex == self.tabsData.STYLE:
        self._CustomizationContext__cancelModifiedStyle()
    elif self._mode == CSMode.SETUP:
        self._currentSettings.clear()
    else:
        self._CustomizationContext__cancelModifiedOufits()
    self.refreshOutfit()
    self.onChangesCanceled()


@overrideMethod(CustomizationContext, 'changeCamouflageColor')
def changeCamouflageColor(_, self, areaId, regionIdx, paletteIdx):
    if self._mode != CSMode.SETUP:
        component = self.currentOutfit.getContainer(areaId).slotFor(GUI_ITEM_TYPE.CAMOUFLAGE).getComponent(regionIdx)
        if component.palette != paletteIdx:
            component.palette = paletteIdx
            self.refreshOutfit()
            self.onCustomizationCamouflageColorChanged(areaId, regionIdx, paletteIdx)
    else:
        self._randMode = paletteIdx
        _updateCurrentSettings(self)
        self.onCacheResync()


@overrideMethod(CustomizationContext, 'changeCamouflageScale')
def changeCamouflageScale(_, self, areaId, regionIdx, scale, scaleIndex):
    if self._mode != CSMode.SETUP:
        component = self.currentOutfit.getContainer(areaId).slotFor(GUI_ITEM_TYPE.CAMOUFLAGE).getComponent(regionIdx)
        if component.patternSize != scale:
            component.patternSize = scale
            self.refreshOutfit()
            self.onCustomizationCamouflageScaleChanged(areaId, regionIdx, scale)
    else:
        item = self.currentOutfit.getContainer(areaId).slotFor(GUI_ITEM_TYPE.CAMOUFLAGE).getItem(regionIdx)
        itemSettings, itemSeasonsStr, _, _ = getItemSettings(self, item)
        self._settingSeason |= SEASON_IDX_TO_TYPE[scaleIndex]
        newSeasons = set(x for x in SEASONS_CONSTANTS.SEASONS if x in itemSeasonsStr)
        newSeasons.add(SEASON_TYPE_TO_NAME[SEASON_IDX_TO_TYPE[scaleIndex]])
        itemSettings['season'] = ','.join(x for x in SEASONS_CONSTANTS.SEASONS if x in newSeasons)
        self.onCacheResync()


def getItemSettings(self, item):
    itemName, itemKey = (item.descriptor.userKey, 'custom') if item.priceGroup == 'custom' else (item.id, 'remap')
    itemSettings = self._currentSettings[itemKey].setdefault(itemName, {})
    itemOrigSettings = g_config.camouflages[itemKey].get(itemName, {})
    itemSeasonsStr = itemSettings.get('season', itemOrigSettings.get('season', None))
    if itemSeasonsStr is not None:
        itemSeasons = SeasonType.UNDEFINED
        for season in SEASONS_CONSTANTS.SEASONS:
            if season in itemSeasonsStr:
                itemSeasons |= getattr(SeasonType, season.upper())
    else:
        itemSeasons = item.season
        itemSeasonsStr = itemSettings['season'] = ','.join(
            x for x in SEASONS_CONSTANTS.SEASONS if getattr(SeasonType, x.upper()) & itemSeasons)
    return itemSettings, itemSeasonsStr, itemSeasons, itemOrigSettings


def _updateCurrentSettings(self):
    item = self.currentOutfit.getContainer(1).slotFor(GUI_ITEM_TYPE.CAMOUFLAGE).getItem(0)
    itemName, itemKey = (item.descriptor.userKey, 'custom') if item.priceGroup == 'custom' else (item.id, 'remap')
    settings = self._currentSettings[itemKey].setdefault(itemName, {})
    settings['useForAlly'] = self._useForAlly
    settings['useForEnemy'] = self._useForEnemy
    settings['random_mode'] = self._randMode


@overrideMethod(CustomizationContext, 'getModifiedOutfit')
def getModifiedOutfit(_, self, season):
    return self.modifiedOutfits.get(season)


@overrideMethod(CustomizationContext, 'getAppliedItems')
def getAppliedItems(_, self, isOriginal=True):
    if self._mode == CSMode.BUY:
        outfits = self._originalOutfits if isOriginal else self._modifiedOutfits
        style = self._originalStyle if isOriginal else self._modifiedStyle
    elif self._mode == CSMode.INSTALL:
        outfits = self._originalCSOutfits if isOriginal else self._modifiedCSOutfits
        style = self._originalCSStyle if isOriginal else self._modifiedCSStyle
    else:
        return set(i.intCD for i in self.currentOutfit.items())
    seasons = SeasonType.COMMON_SEASONS if isOriginal else (self._currentSeason,)
    appliedItems = set()
    for seasonType in seasons:
        appliedItems.update(i.intCD for i in outfits[seasonType].items())
    if style:
        appliedItems.add(style.intCD)
    return appliedItems


@overrideMethod(CustomizationContext, 'isItemInOutfit')
def isItemInOutfit(_, self, item):
    return any((outfit.has(item) for outfit in self.originalOutfits.itervalues())) or any(
        (outfit.has(item) for outfit in self.modifiedOutfits.itervalues()))


@overrideMethod(CustomizationContext, 'getNotModifiedItems')
def getNotModifiedItems(self, season):
    df = self.modifiedOutfits[season].diff(self.originalOutfits[season])
    notModifiedItems = df.diff(self.originalOutfits[self.currentSeason])
    return notModifiedItems


@overrideMethod(CustomizationContext, 'applyItems')
@process('buyAndInstall')
def applyItems(base, self, purchaseItems):
    yield base(self, purchaseItems)
    self._currentSettings = self._cleanSettings(self._currentSettings)
    for itemsKey in self._currentSettings:
        for camoName in self._currentSettings[itemsKey]:
            g_config.camouflages[itemsKey].setdefault(camoName, {}).update(self._currentSettings[itemsKey][camoName])
    if self._currentSettings['remap']:
        newSettings = {'disable': g_config.disable,
                       'remap': g_config.camouflages['remap']}
        loadJson(g_config.ID, 'settings', newSettings, g_config.configPath, True)
    if self._currentSettings['custom']:
        for confFolderName in g_config.configFolders:
            configFolder = g_config.configFolders[confFolderName]
            loadJson(g_config.ID, 'settings', {key: g_config.camouflages['custom'][key] for key in configFolder},
                     g_config.configPath + 'camouflages/' + confFolderName + '/', True, False)
    if any(self._currentSettings.itervalues()):
        g_config.collectCamouflageData()
    self.itemsCache.onSyncCompleted -= self._CustomizationContext__onCacheResync
    boughtOutfits = {season: self.service.getCustomOutfit(season) for season in SeasonType.COMMON_SEASONS}
    nationName, vehicleName = g_currentVehicle.item.descriptor.name.split(':')
    vehConfig = g_config.outfitCache.get(nationName, {}).get(vehicleName, {})
    for pItem in (x for x in purchaseItems if x.selected):
        seasonName = SEASON_TYPE_TO_NAME[pItem.group]
        if pItem.slot == GUI_ITEM_TYPE.CAMOUFLAGE:
            bItem, bComp = boughtOutfits[pItem.group].getContainer(pItem.areaID).slotFor(pItem.slot)._items.get(
                pItem.regionID, (None, None))
            component = self._modifiedOutfits[pItem.group].getContainer(pItem.areaID).slotFor(pItem.slot).getComponent(
                pItem.regionID)
            if pItem.isDismantling and (not bItem or not bComp) or not pItem.isDismantling and pItem.item == bItem and \
                    component.palette == bComp.palette and component.patternSize == bComp.patternSize:
                vehConfig.get(seasonName, {}).get('camo', {}).pop(TankPartIndexes.getName(pItem.areaID), [])
            else:
                g_config.outfitCache.setdefault(nationName, {}).setdefault(vehicleName, {}).setdefault(
                    seasonName, {}).setdefault('camo', {})[TankPartIndexes.getName(pItem.areaID)] = (
                    [pItem.item.id, component.palette, component.patternSize] if not pItem.isDismantling else [])
            g_config.hangarCamoCache.get(nationName, {}).get(vehicleName, {}).get(seasonName, {}).pop(
                TankPartIndexes.getName(pItem.areaID), {})
        else:
            typeName = GUI_ITEM_TYPE_NAMES[pItem.slot]
            bItem = boughtOutfits[pItem.group].getContainer(pItem.areaID).slotFor(pItem.slot).getItem(pItem.regionID)
            if pItem.isDismantling and not bItem or not pItem.isDismantling and pItem.item == bItem:
                vehConfig.get(seasonName, {}).get(typeName, {}).get(
                    TankPartIndexes.getName(pItem.areaID) if pItem.areaID < 4 else 'misc',
                    {}).pop(str(pItem.regionID), None)
            else:
                g_config.outfitCache.setdefault(nationName, {}).setdefault(vehicleName, {}).setdefault(
                    seasonName, {}).setdefault(typeName, {}).setdefault(
                    TankPartIndexes.getName(pItem.areaID) if pItem.areaID < 4 else 'misc', {})[
                    str(pItem.regionID)] = (pItem.item.id if not pItem.isDismantling else None)
    for nationName in g_config.outfitCache.keys():
        for vehicleName in g_config.outfitCache[nationName].keys():
            for season in g_config.outfitCache[nationName][vehicleName].keys():
                for itemType in g_config.outfitCache[nationName][vehicleName][season].keys():
                    if itemType == 'camo':
                        if g_currentVehicle.item.turret.isGunCarriage:
                            g_config.outfitCache[nationName][vehicleName][season][itemType].pop('turret', None)
                    else:
                        for areaName in g_config.outfitCache[nationName][vehicleName][season][itemType].keys():
                            if not g_config.outfitCache[nationName][vehicleName][season][itemType][areaName]:
                                del g_config.outfitCache[nationName][vehicleName][season][itemType][areaName]
                    if not g_config.outfitCache[nationName][vehicleName][season][itemType]:
                        del g_config.outfitCache[nationName][vehicleName][season][itemType]
                if not g_config.outfitCache[nationName][vehicleName][season]:
                    del g_config.outfitCache[nationName][vehicleName][season]
            if not g_config.outfitCache[nationName][vehicleName]:
                del g_config.outfitCache[nationName][vehicleName]
        if not g_config.outfitCache[nationName]:
            del g_config.outfitCache[nationName]
    loadJson(g_config.ID, 'outfitCache', g_config.outfitCache, g_config.configPath, True)
    self._CustomizationContext__onCacheResync()
    self.itemsCache.onSyncCompleted += self._CustomizationContext__onCacheResync


@overrideMethod(CustomizationContext, 'sellItem')
@process('sellItem')
def sellItem(_, self, intCD, count):
    if not count:
        return
    item = self.service.getItemByCD(intCD)
    if item.fullInventoryCount(g_currentVehicle.item) < count:
        if item.itemTypeID != GUI_ITEM_TYPE.STYLE:
            for season, outfit in getOutfitWithoutItems(self.getOutfitsInfo(), intCD, count):
                yield OutfitApplier(g_currentVehicle.item, outfit, season).request()

        else:
            yield StyleApplier(g_currentVehicle.item).request()
    yield CustomizationsSeller(g_currentVehicle.item, item, count).request()
    nextTick(self.refreshOutfit)()
    nextTick(partial(self.onCustomizationItemSold, item=item, count=count))()


@overrideMethod(CustomizationContext, 'init')
def init(_, self):
    self.service.onOutfitChanged += self._CustomizationContext__onOutfitChanged
    self.itemsCache.onSyncCompleted += self._CustomizationContext__onCacheResync
    self.carveUpOutfits()
    self._CustomizationContext__updateVisibleTabsList()
    self._originalMode = self._mode
    self.refreshOutfit()


@overrideMethod(CustomizationContext, '_CustomizationContext__carveUpOutfits')
def __carveUpOutfits(_, self):
    for season in SeasonType.COMMON_SEASONS:
        outfit = self.service.getCustomOutfit(season)
        self._modifiedOutfits[season] = outfit.copy()
        if outfit.isInstalled():
            self._originalOutfits[season] = outfit.copy()
        else:
            self._originalOutfits[season] = self.service.getEmptyOutfit()
        for slot in self._modifiedOutfits[season].slots():
            for idx in range(slot.capacity()):
                item = slot.getItem(idx)
                if item and item.isHidden and item.fullInventoryCount(g_currentVehicle.item) == 0:
                    slot.remove(idx)

    from ..processors import applyCamoCache, applyPlayerCache
    self._setupOutfit = self.service.getEmptyOutfit()
    descriptor = g_currentVehicle.item.descriptor
    nationName, vehName = descriptor.name.split(':')
    for season in SeasonType.COMMON_SEASONS:
        outfit = self.service.getCustomOutfit(season).copy()
        seasonName = SEASON_TYPE_TO_NAME[season]
        seasonCache = g_config.outfitCache.get(nationName, {}).get(vehName, {}).get(seasonName, {})
        applyCamoCache(outfit, vehName, seasonCache.get('camo', {}))
        applyPlayerCache(outfit, vehName, seasonCache)
        self._originalCSOutfits[season] = outfit.copy()
        applyCamoCache(outfit, vehName, g_config.hangarCamoCache.get(nationName, {}).get(vehName, {}).get(seasonName, {}))
        self._modifiedCSOutfits[season] = outfit.copy()

    style = self.service.getCurrentStyle()
    if self.service.isCurrentStyleInstalled():
        self._originalStyle = style
        self._modifiedStyle = style
    else:
        self._originalStyle = None
        if style and style.isHidden and style.fullInventoryCount(g_currentVehicle.item) == 0:
            self._modifiedStyle = None
        else:
            self._modifiedStyle = style
    if self._mode == CSMode.BUY:
        if style:
            self._currentOutfit = style.getOutfit(self._currentSeason)
        else:
            self._currentOutfit = self._modifiedOutfits[self._currentSeason]
    elif self._mode == CSMode.INSTALL:
        self._currentOutfit = self._modifiedCSOutfits[self._currentSeason]
    else:
        self._currentOutfit = self._setupOutfit


@overrideMethod(CustomizationContext, '_CustomizationContext__cancelModifiedOufits')
def __cancelModifiedOufits(_, self):
    for season in SeasonType.COMMON_SEASONS:
        self.modifiedOutfits[season] = self.originalOutfits[season].copy()


@overrideMethod(CustomizationContext, '_CustomizationContext__cancelModifiedStyle')
def __cancelModifiedStyle(_, self):
    if self._mode == CSMode.BUY:
        self._modifiedStyle = self._originalStyle
    else:
        self._modifiedCSStyle = self._originalCSStyle


@overrideMethod(CustomizationContext, 'isOutfitsModified')
def isOutfitsModified(_, self):
    if self._mode == self._originalMode:
        if self._mode == CSMode.BUY:
            currentStyle = self.service.getCurrentStyle()
            if self._modifiedStyle and currentStyle:
                return self._modifiedStyle.intCD != currentStyle.intCD
            if not (self._modifiedStyle is None and currentStyle is None):
                return True
            for season in SeasonType.COMMON_SEASONS:
                outfit = self._modifiedOutfits[season]
                currOutfit = self._originalOutfits[season]
                if not currOutfit.isEqual(outfit) or not outfit.isEqual(currOutfit):
                    return True
        if self._mode == CSMode.INSTALL:
            currentStyle = self.service.getCurrentStyle()  # TODO: change to CamoSelector's style getter
            if self._modifiedCSStyle and currentStyle:
                return self._modifiedCSStyle.intCD != currentStyle.intCD
            if not (self._modifiedCSStyle is None and currentStyle is None):
                return True
            for season in SeasonType.COMMON_SEASONS:
                outfit = self._modifiedCSOutfits[season]
                currOutfit = self._originalCSOutfits[season]
                if not currOutfit.isEqual(outfit) or not outfit.isEqual(currOutfit):
                    return True

        return False
    else:
        if (self.isOutfitsEmpty(self._modifiedOutfits) and self._originalStyle is None) or (
                self._modifiedStyle is None and self.isOutfitsEmpty(self._originalOutfits)):
            return False
        return True


@overrideMethod(CustomizationContext, '_CustomizationContext__preserveState')
def __preserveState(_, self):
    self._state.update(
        modifiedStyle=self._modifiedStyle,
        modifiedOutfits={season: outfit.copy() for season, outfit in self._modifiedOutfits.iteritems()},
        modifiedCSStyle=self._modifiedCSStyle,
        modifiedCSOutfits={season: outfit.copy() for season, outfit in self._modifiedCSOutfits.iteritems()})


@overrideMethod(CustomizationContext, '_CustomizationContext__restoreState')
def __restoreState(_, self):
    self._modifiedStyle = self._state.get('modifiedStyle')
    self._modifiedOutfits = self._state.get('modifiedOutfits')
    if self._modifiedStyle:
        self._modifiedStyle = self.service.getItemByCD(self._modifiedStyle.intCD)
    self._modifiedCSStyle = self._state.get('modifiedCSStyle')
    self._modifiedCSOutfits = self._state.get('modifiedCSOutfits')
    if self._modifiedCSStyle:
        self._modifiedCSStyle = self.service.getItemByCD(self._modifiedCSStyle.intCD)
    self._state.clear()


@overrideMethod(CustomizationContext, '_CustomizationContext__updateVisibleTabsList')
def __updateVisibleTabsList(_, self):
    visibleTabs = defaultdict(set)
    anchorsData = g_currentVehicle.hangarSpace.getSlotPositions()
    if self._mode == CSMode.BUY:
        requirement = createCustomizationBaseRequestCriteria(g_currentVehicle.item, self.eventsCache.randomQuestsProgress,
                                                             self.getAppliedItems())
        items = self.service.getItems(GUI_ITEM_TYPE.CUSTOMIZATIONS, criteria=requirement)
    else:
        items = self.itemsCache.items.getItems(GUI_ITEM_TYPE.CUSTOMIZATIONS, createBaseRequirements())
    for item in sorted(items.itervalues(), key=(comparisonKey if self._mode == CSMode.BUY else CSComparisonKey)):
        if self._mode == CSMode.BUY:
            tabIndex = TYPE_TO_TAB_IDX.get(item.itemTypeID)
        else:
            tabIndex = findFirst(partial(isItemSuitableForTab, item), CSTabs.ALL, -1)
        if tabIndex not in self.tabsData.VISIBLE or (
                self._mode == CSMode.BUY and tabIndex == C11nTabs.CAMOUFLAGE and
                g_currentVehicle.item.descriptor.type.hasCustomDefaultCamouflage) or (
                self._mode == CSMode.SETUP and tabIndex not in CSTabs.CAMO):
            continue
        for seasonType in SeasonType.COMMON_SEASONS:
            if (item.season if self._mode == CSMode.BUY else getItemSeason(item)) & seasonType:
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

    self._CustomizationContext__visibleTabs = visibleTabs
