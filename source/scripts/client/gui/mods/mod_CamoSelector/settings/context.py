from CurrentVehicle import g_currentVehicle
from PYmodsCore import overrideMethod, loadJson
from functools import partial
from gui import g_tankActiveCamouflage, SystemMessages
from gui.Scaleform.daapi.view.lobby.customization.shared import C11nTabs, SEASON_TYPE_TO_IDX, SEASON_IDX_TO_TYPE, \
    SEASON_TYPE_TO_NAME, getOutfitWithoutItems, getItemInventoryCount, getStyleInventoryCount, OutfitInfo, \
    SEASONS_ORDER, getCustomPurchaseItems, getStylePurchaseItems
from gui.Scaleform.daapi.view.lobby.customization.vehicle_anchors_updater import VehicleAnchorsUpdater
from gui.Scaleform.genConsts.SEASONS_CONSTANTS import SEASONS_CONSTANTS
from gui.Scaleform.locale.SYSTEM_MESSAGES import SYSTEM_MESSAGES
from gui.customization import CustomizationService
from gui.customization.context import CustomizationContext as WGCtx, CaruselItemData
from gui.customization.shared import C11nId, getAppliedRegionsForCurrentHangarVehicle, appliedToFromSlotsIds
from gui.hangar_cameras.c11n_hangar_camera_manager import C11nHangarCameraManager
from gui.shared.gui_items import GUI_ITEM_TYPE, GUI_ITEM_TYPE_NAMES
from gui.shared.gui_items.customization.outfit import Area
from gui.shared.gui_items.processors.common import OutfitApplier, StyleApplier, CustomizationsSeller
from gui.shared.utils.decorators import process
from items.components.c11n_constants import SeasonType
from items.vehicles import g_cache
from shared_utils import nextTick, first
from soft_exception import SoftException
from vehicle_systems.tankStructure import TankPartIndexes
from .shared import CSMode, CSTabs, tabToItem
from .. import g_config
from ..constants import RandMode


class CustomizationContext(WGCtx):
    @property
    def isBuy(self):
        return self._mode == CSMode.BUY

    @property
    def tabsData(self):
        return C11nTabs if self.isBuy else CSTabs

    @property
    def originalOutfit(self):
        return self.originalOutfits[self._currentSeason]

    @property
    def originalOutfits(self):
        return self._originalOutfits if self.isBuy else self._originalCSOutfits

    @property
    def modifiedOutfits(self):
        return self._modifiedOutfits if self.isBuy else self._modifiedCSOutfits

    def getSeasonIndices(self):
        return [SEASON_TYPE_TO_IDX[x] for x in SeasonType.COMMON_SEASONS if x & self._settingSeason]

    def changeAlly(self, apply):
        self.useFor_ally = apply
        self._updateCurrentSettings()
        self.onCacheResync()

    def changeEnemy(self, apply):
        self.useFor_enemy = apply
        self._updateCurrentSettings()
        self.onCacheResync()

    def getRandMode(self):
        return self._randMode

    @property
    def modifiedStyle(self):
        return self._modifiedStyle if self.isBuy else self._modifiedCSStyle

    def __init__(self):
        super(CustomizationContext, self).__init__()
        self._originalMode = CSMode.BUY
        self._mode = self._originalMode
        self._lastTab = {CSMode.BUY: C11nTabs.PAINT, CSMode.INSTALL: CSTabs.CAMO_SHOP, CSMode.SETUP: CSTabs.CAMO_SHOP}
        self._originalCSOutfits = {}
        self._modifiedCSOutfits = {}
        self._originalCSStyle = None
        self._modifiedCSStyle = None
        self._setupOutfit = None
        self._currentSettings = {'custom': {}, 'remap': {}}
        self._settingSeason = None
        self._randMode = None
        self.useFor_ally = False
        self.useFor_enemy = False
        self.isSwitcherIgnored = False

    def refreshOutfit(self):
        if self._mode == CSMode.SETUP:
            self._currentOutfit = self._setupOutfit
        elif self._tabIndex == self.tabsData.STYLE:
            if self.modifiedStyle:
                self._currentOutfit = self.modifiedStyle.getOutfit(self._currentSeason)
            else:
                self._currentOutfit = self.service.getEmptyOutfit()
        else:
            self._currentOutfit = self.modifiedOutfits[self._currentSeason]
        self.service.tryOnOutfit(self._currentOutfit)
        g_tankActiveCamouflage[g_currentVehicle.item.intCD] = self._currentSeason

    def tabChanged(self, tabIndex):
        self._tabIndex = tabIndex
        if self._tabIndex == self.tabsData.EFFECT:
            self._selectedAnchor = C11nId(areaId=Area.MISC, slotType=GUI_ITEM_TYPE.MODIFICATION, regionIdx=0)
        elif self._tabIndex == self.tabsData.STYLE:
            self._selectedAnchor = C11nId(areaId=Area.CHASSIS, slotType=GUI_ITEM_TYPE.STYLE, regionIdx=0)
        else:
            self._selectedAnchor = C11nId()
        self._selectedCaruselItem = CaruselItemData()
        self.onCustomizationTabChanged(tabIndex)

    def anchorSelected(self, slotType, areaId, regionIdx):
        if self._tabIndex in (self.tabsData.EFFECT, self.tabsData.STYLE):
            return False
        if self._mode == CSMode.SETUP:
            slotType = tabToItem(self._tabIndex, self.isBuy)
            areaId = Area.HULL
        prevSelectedAnchor = self._selectedAnchor
        self._selectedAnchor = C11nId(areaId=areaId, slotType=slotType, regionIdx=regionIdx)
        if prevSelectedAnchor != self._selectedAnchor:
            if self._vehicleAnchorsUpdater is not None and self.currentTab in C11nTabs.REGIONS:
                self._vehicleAnchorsUpdater.changeAnchorParams(prevSelectedAnchor, True, True)
        self.onCustomizationAnchorSelected(self._selectedAnchor.slotType, self._selectedAnchor.areaId,
                                           self._selectedAnchor.regionIdx)
        if areaId != -1 and regionIdx != -1 and self._selectedCaruselItem.intCD != -1:
            outfit = self._modifiedOutfits[self._currentSeason]
            slotId = self.__getFreeSlot(self._selectedAnchor, outfit)
            if slotId is None or not self.__isItemInstalledInOutfitSlot(slotId, self._selectedCaruselItem.intCD):
                item = self.service.getItemByCD(self._selectedCaruselItem.intCD)
                component = self.__getComponent(item.id, self.selectedAnchor)
                if self.installItem(self._selectedCaruselItem.intCD, slotId, SEASON_TYPE_TO_IDX[self.currentSeason],
                                    component):
                    return True
        return False

    def installItem(self, intCD, slotId, seasonIdx, component=None):
        if slotId is None:
            return False
        item = self.service.getItemByCD(intCD)
        inventoryCount = self.getItemInventoryCount(item)
        if self.isBuy and item.isHidden and not inventoryCount:
            SystemMessages.pushI18nMessage(SYSTEM_MESSAGES.CUSTOMIZATION_PROHIBITED, type=SystemMessages.SM_TYPE.Warning,
                                           itemName=item.userName)
            return False
        if self._mode != CSMode.SETUP:
            if slotId.slotType == GUI_ITEM_TYPE.STYLE:
                if self.isBuy:
                    self._modifiedStyle = item
                else:
                    self._modifiedCSStyle = item
            else:
                season = SEASON_IDX_TO_TYPE.get(seasonIdx, self._currentSeason)
                outfit = self.modifiedOutfits[season]
                outfit.getContainer(slotId.areaId).slotFor(slotId.slotType).set(
                    item, idx=slotId.regionIdx, component=component)
                outfit.invalidate()
        else:
            outfit = self._setupOutfit
            for areaId in xrange(1, 4):
                outfit.getContainer(areaId).slotFor(slotId.slotType).set(item, idx=slotId.regionIdx, component=component)
            itemSettings, _, itemSeasons, itemOrigSettings = self.getItemSettings(item)
            self._settingSeason = itemSeasons
            self._randMode = itemSettings.get('random_mode', itemOrigSettings.get('random_mode', RandMode.RANDOM))
            self.useFor_ally = itemSettings.get('useForAlly', itemOrigSettings.get('useForAlly', True))
            self.useFor_enemy = itemSettings.get('useForEnemy', itemOrigSettings.get('useForEnemy', True))

        self.refreshOutfit()
        buyLimitReached = self.isBuyLimitReached(item)
        self.onCustomizationItemInstalled(item, slotId, buyLimitReached)
        return True

    def removeItemFromSlot(self, season, slotId, refresh=True):
        outfit = self.modifiedOutfits[season]
        slot = outfit.getContainer(slotId.areaId).slotFor(slotId.slotType)
        if slot.capacity() > slotId.regionIdx:
            item = slot.getItem(slotId.regionIdx)
            if item is not None and not item.isHiddenInUI():
                slot.remove(idx=slotId.regionIdx)
        if refresh:
            self.refreshOutfit()
            self.onCustomizationItemsRemoved()

    def removeStyle(self, intCD):
        if self.isBuy:
            if self._modifiedStyle and self._modifiedStyle.intCD == intCD:
                self._modifiedStyle = None
        elif self._mode == CSMode.INSTALL:
            if self._modifiedCSStyle and self._modifiedCSStyle.intCD == intCD:
                self._modifiedCSStyle = None
        self.refreshOutfit()
        self.onCustomizationItemsRemoved()

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

    def switchToCustom(self):
        self.changeMode(False)

    def switchToStyle(self):
        self.changeMode(True)

    def changeMode(self, wasLeft):
        if self.isSwitcherIgnored:
            self.isSwitcherIgnored = False
            return
        self.isSwitcherIgnored = True  # the switcher just jumps backwards immediately. -_-
        self._lastTab[self._mode] = self._tabIndex
        self._mode = ((self._mode + 1) if wasLeft else (self._mode - 1)) % len(CSMode.NAMES)
        tabIndex = self._lastTab[self._mode]
        if tabIndex not in self.visibleTabs:
            tabIndex = first(self.visibleTabs, -1)
        self.refreshOutfit()
        self.onCustomizationModeChanged(self._mode)
        self.tabChanged(tabIndex)

    def cancelChanges(self):
        if self._tabIndex == self.tabsData.STYLE:
            self.__cancelModifiedStyle()
        elif self._mode == CSMode.SETUP:
            self._currentSettings = {'custom': {}, 'remap': {}}
        else:
            self.__cancelModifiedOufits()
        self.refreshOutfit()
        self.onChangesCanceled()

    def changeCamouflageScale(self, areaId, regionIdx, scale):
        if self._mode != CSMode.SETUP:
            component = self.currentOutfit.getContainer(areaId).slotFor(GUI_ITEM_TYPE.CAMOUFLAGE).getComponent(regionIdx)
            if component.patternSize != scale:
                component.patternSize = scale
                self.refreshOutfit()
                self.onCustomizationCamouflageScaleChanged(areaId, regionIdx, scale)
                self.itemDataChanged(areaId, GUI_ITEM_TYPE.CAMOUFLAGE, regionIdx)
        elif self._randMode != scale:
            self._randMode = scale
            self._updateCurrentSettings()
            self.onCacheResync()

    def toggleSeason(self, seasonIdx):
        item = self.currentOutfit.getContainer(1).slotFor(GUI_ITEM_TYPE.CAMOUFLAGE).getItem(0)
        itemSettings, itemSeasonsStr, _, _ = self.getItemSettings(item)
        self._settingSeason |= SEASON_IDX_TO_TYPE[seasonIdx]
        newSeasons = set(x for x in SEASONS_CONSTANTS.SEASONS if x in itemSeasonsStr)
        newSeasons.add(SEASON_TYPE_TO_NAME[SEASON_IDX_TO_TYPE[seasonIdx]])
        itemSettings['season'] = ','.join(x for x in SEASONS_CONSTANTS.SEASONS if x in newSeasons)

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
        settings['useForAlly'] = self.useFor_ally
        settings['useForEnemy'] = self.useFor_enemy
        settings['random_mode'] = self._randMode

    def _cleanSettings(self, allSettings, checkSeasons=True):
        camouflages = g_cache.customization20().camouflages
        for itemsKey in allSettings:
            itemSettings = allSettings[itemsKey]
            for camoID in itemSettings.keys():
                origSetting = g_config.camouflages[itemsKey].get(camoID, {})
                camoSetting = itemSettings[camoID]
                if 'season' in camoSetting:
                    if checkSeasons and itemsKey == 'remap' and not self.itemsCache.items.getItemByCD(
                            camouflages[camoID].compactDescr).isHidden:
                        print g_config.ID + ': in-shop camouflage season changing is disabled (id:', \
                            camoID + ', season setting was', (camoSetting['season'] or 'empty') + ')'
                        del camoSetting['season']
                        if 'season' in origSetting:
                            del origSetting['season']
                    elif 'season' not in origSetting:
                        itemSeasons = SeasonType.UNDEFINED
                        for season in SEASONS_CONSTANTS.SEASONS:
                            if season in camoSetting['season']:
                                itemSeasons |= getattr(SeasonType, season.upper())
                        camoSeason = camouflages[camoID].season
                        if itemSeasons == (camoSeason if camoSeason < 8 else camoSeason - 8):
                            del camoSetting['season']
                    elif origSetting['season'] == camoSetting['season']:
                        del camoSetting['season']
                for team in ('useForAlly', 'useForEnemy'):
                    if team in camoSetting:
                        if origSetting.get(team, True) == camoSetting[team]:
                            del camoSetting[team]
                if 'random_mode' in camoSetting:
                    if camoSetting['random_mode'] == origSetting.get('random_mode', RandMode.RANDOM):
                        del camoSetting['random_mode']
                if not camoSetting:
                    del itemSettings[camoID]
        return allSettings

    @classmethod
    def deleteEmpty(cls, settings):
        for key, value in settings.items():
            if key == 'camo':
                if g_currentVehicle.item.turret.isGunCarriage:
                    settings[key].pop('turret', None)
            else:
                if isinstance(settings[key], dict):
                    cls.deleteEmpty(settings[key])
                    if not settings[key]:
                        del settings[key]

    def getOutfitsInfo(self):
        outfitsInfo = {}
        for season in SEASONS_ORDER:
            outfitsInfo[season] = OutfitInfo(self.originalOutfits[season], self.modifiedOutfits[season])

        return outfitsInfo

    def getStyleInfo(self):
        return OutfitInfo(self._originalStyle, self._modifiedStyle)

    def getPurchaseItems(self):
        return getCustomPurchaseItems(
            self.getOutfitsInfo()) if self._tabIndex != self.tabsData.STYLE else getStylePurchaseItems(self.getStyleInfo())

    def getItemInventoryCount(self, item):
        return getItemInventoryCount(
            item, self.getOutfitsInfo()) if item.itemTypeID != GUI_ITEM_TYPE.STYLE else getStyleInventoryCount(
            item, self.getStyleInfo())

    def getModifiedOutfit(self, season):
        return self.modifiedOutfits.get(season)

    def getAppliedItems(self, isOriginal=True):
        if self._mode != CSMode.SETUP:
            outfits = self.originalOutfits if isOriginal else self.modifiedOutfits
            style = self.originalStyle if isOriginal else self.modifiedStyle
        else:
            return set(i.intCD for i in self.currentOutfit.items())
        seasons = SeasonType.COMMON_SEASONS if isOriginal else (self._currentSeason,)
        appliedItems = set()
        for seasonType in seasons:
            appliedItems.update(i.intCD for i in outfits[seasonType].items())
        if style:
            appliedItems.add(style.intCD)
        return appliedItems

    def isItemInOutfit(self, item):
        return any((outfit.has(item) for outfit in self.originalOutfits.itervalues())) or any(
            (outfit.has(item) for outfit in self.modifiedOutfits.itervalues()))

    def getNotModifiedItems(self, season):
        df = self.modifiedOutfits[season].diff(self.originalOutfits[season])
        notModifiedItems = df.diff(self.originalOutfits[self.currentSeason])
        return notModifiedItems

    @process('customizationApply')
    def applyItems(self, purchaseItems):
        yield super(CustomizationContext, self).applyItems(purchaseItems)
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
        self.itemsCache.onSyncCompleted -= self.__onCacheResync
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
        self.deleteEmpty(g_config.outfitCache)
        loadJson(g_config.ID, 'outfitCache', g_config.outfitCache, g_config.configPath, True)
        self.__onCacheResync()  # TODO: whip up style saving (and applying, for that measure)
        self.itemsCache.onSyncCompleted += self.__onCacheResync

    @process('sellItem')
    def sellItem(self, intCD, count):
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

    def init(self):
        if not g_currentVehicle.isPresent():
            raise SoftException('There is not vehicle in hangar for customization.')
        self._autoRentEnabled = g_currentVehicle.item.isAutoRentStyle
        self._vehicleAnchorsUpdater = VehicleAnchorsUpdater(self.service, self)
        self._vehicleAnchorsUpdater.startUpdater(self.settingsCore.interfaceScale.get())
        if self.hangarSpace.spaceInited:
            self._c11CameraManager = C11nHangarCameraManager(self.hangarSpace.space.getCameraManager())
            self._c11CameraManager.init()
        self.settingsCore.interfaceScale.onScaleExactlyChanged += self.__onInterfaceScaleChanged
        self.service.onOutfitChanged += self.__onOutfitChanged
        self.itemsCache.onSyncCompleted += self.__onCacheResync
        self.carveUpOutfits()
        currVehSeasonType = g_tankActiveCamouflage.get(g_currentVehicle.item.intCD, SeasonType.SUMMER)
        self._currentSeason = currVehSeasonType
        if self._originalStyle:
            self._tabIndex = self.tabsData.STYLE
        else:
            self._tabIndex = self.tabsData.PAINT
            notInst = all([ not self.originalOutfits[season].isInstalled() for season in SeasonType.COMMON_SEASONS ])
            if notInst and not self.isOutfitsEmpty(self.modifiedOutfits) and not self.modifiedStyle:
                self._tabIndex = self.tabsData.STYLE
        self._originalMode = self._mode
        self.refreshOutfit()

    def isOutfitsModified(self):  # TODO: fix this damn fuckery
        if self._mode == self._originalMode:
            if self.isBuy:
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

    def isSlotFilled(self, anchorId):
        if anchorId.slotType == GUI_ITEM_TYPE.STYLE:
            return self._modifiedStyle is not None
        else:
            slotId = self.getSlotIdByAnchorId(anchorId)
            if slotId is not None:
                outfit = self.modifiedOutfits[self._currentSeason]
                multiSlot = outfit.getContainer(slotId.areaId).slotFor(slotId.slotType)
                if multiSlot is not None:
                    item = multiSlot.getItem(slotId.regionIdx)
                    return item is not None
            return False

    def getEmptyRegions(self):
        emptyRegions = []
        slotType = tabToItem(self._tabIndex, self.isBuy)
        for areaId in Area.ALL:
            regionsIndexes = getAppliedRegionsForCurrentHangarVehicle(areaId, slotType)
            for regionIdx in regionsIndexes:
                outfit = self.getModifiedOutfit(self._currentSeason)
                item = outfit.getContainer(areaId).slotFor(slotType).getItem(regionIdx)
                if item is None:
                    emptyRegions.append((areaId, slotType, regionIdx))

        mask = appliedToFromSlotsIds(emptyRegions)
        return mask

    def __carveUpOutfits(self):
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
        # TODO: add CamoSelector style getter
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
        if self._mode == CSMode.SETUP:
            self._currentOutfit = self._setupOutfit
        elif self._tabIndex == self.tabsData.STYLE:
            self._currentOutfit = self.modifiedStyle.getOutfit(self._currentSeason)
        else:
            self._currentOutfit = self.modifiedOutfits[self._currentSeason]

    def __cancelModifiedOufits(self):
        for season in SeasonType.COMMON_SEASONS:
            self.modifiedOutfits[season] = self.originalOutfits[season].copy()

    def __cancelModifiedStyle(self):
        if self.isBuy:
            self._modifiedStyle = self._originalStyle
        else:
            self._modifiedCSStyle = self._originalCSStyle

    def __preserveState(self):
        self._state.update(
            modifiedStyle=self._modifiedStyle,
            modifiedOutfits={season: outfit.copy() for season, outfit in self._modifiedOutfits.iteritems()},
            modifiedCSStyle=self._modifiedCSStyle,
            modifiedCSOutfits={season: outfit.copy() for season, outfit in self._modifiedCSOutfits.iteritems()})

    def __restoreState(self):
        self._modifiedStyle = self._state.get('modifiedStyle')
        self._modifiedOutfits = self._state.get('modifiedOutfits')
        if self._modifiedStyle:
            self._modifiedStyle = self.service.getItemByCD(self._modifiedStyle.intCD)
        self._modifiedCSStyle = self._state.get('modifiedCSStyle')
        self._modifiedCSOutfits = self._state.get('modifiedCSOutfits')
        if self._modifiedCSStyle:
            self._modifiedCSStyle = self.service.getItemByCD(self._modifiedCSStyle.intCD)
        self._state.clear()

    def updateVisibleTabsList(self, visibleTabs):
        for seasonType in SeasonType.COMMON_SEASONS:
            self.__visibleTabs[seasonType] = sorted(visibleTabs[seasonType])
        tabIndex = first(self.visibleTabs, -1)
        self._lastTab[self._mode] = tabIndex
        self.tabChanged(tabIndex)

    def __isItemInstalledInOutfitSlot(self, slotId, itemIntCD):
        if slotId.slotType == GUI_ITEM_TYPE.STYLE:
            return self.modifiedStyle.intCD == itemIntCD
        else:
            outfit = self.modifiedOutfits[self._currentSeason]
            multiSlot = outfit.getContainer(slotId.areaId).slotFor(slotId.slotType)
            if multiSlot is not None:
                item = multiSlot.getItem(slotId.regionIdx)
                if item is not None:
                    return item.intCD == itemIntCD
            return False


@overrideMethod(CustomizationService, 'getCtx')
def new_getCtx(base, self):
    if not g_config.data['enabled']:
        return base(self)
    if not self._CustomizationService__customizationCtx:
        self._CustomizationService__customizationCtx = CustomizationContext()
        self._CustomizationService__customizationCtx.init()
    return self._CustomizationService__customizationCtx
