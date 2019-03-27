from CurrentVehicle import g_currentVehicle
from PYmodsCore import overrideMethod, loadJson
from gui import SystemMessages, g_tankActiveCamouflage
from gui.Scaleform.daapi.view.lobby.customization.customization_inscription_controller import PersonalNumEditCommands
from gui.Scaleform.daapi.view.lobby.customization.shared import C11nTabs, SEASON_IDX_TO_TYPE, \
    SEASON_TYPE_TO_NAME, C11nMode
from gui.Scaleform.genConsts.SEASONS_CONSTANTS import SEASONS_CONSTANTS
from gui.Scaleform.locale.SYSTEM_MESSAGES import SYSTEM_MESSAGES
from gui.customization import CustomizationService
from gui.customization.context import CustomizationContext as WGCtx, CaruselItemData
from gui.customization.shared import C11nId
from gui.shared.gui_items import GUI_ITEM_TYPE, GUI_ITEM_TYPE_NAMES
from gui.shared.gui_items.customization.outfit import Area
from gui.shared.utils.decorators import process
from items.components.c11n_constants import SeasonType
from items.vehicles import g_cache
from shared_utils import first
from vehicle_systems.tankStructure import TankPartIndexes
from .shared import CSMode
from .. import g_config
from ..constants import SelectionMode, SEASON_NAME_TO_TYPE


class CustomizationContext(WGCtx):
    @property
    def isBuy(self):
        return self._actualMode == CSMode.BUY

    @property
    def _originalOutfits(self):
        return self.__originalOutfits if self.isBuy else self._originalCSOutfits

    @_originalOutfits.setter
    def _originalOutfits(self, value):
        self.__originalOutfits = value

    @property
    def _modifiedOutfits(self):
        return self.__modifiedOutfits if self.isBuy else self._modifiedCSOutfits

    @_modifiedOutfits.setter
    def _modifiedOutfits(self, value):
        self.__modifiedOutfits = value

    @property
    def _modifiedStyle(self):
        return self.__modifiedStyle if self.isBuy else self._modifiedCSStyle

    @_modifiedStyle.setter
    def _modifiedStyle(self, value):
        self.__modifiedStyle = value

    def __init__(self):
        super(CustomizationContext, self).__init__()
        self._lastTab = {CSMode.BUY: C11nTabs.STYLE, CSMode.INSTALL: C11nTabs.CAMOUFLAGE}
        self._originalCSOutfits = {}
        self._modifiedCSOutfits = {}
        self._originalCSStyle = None
        self._modifiedCSStyle = None
        self.__originalOutfits = {}
        self.__modifiedOutfits = {}
        self.__modifiedStyle = None
        self._currentSettings = {'custom': {}, 'remap': {}}
        self._actualMode = CSMode.INSTALL

    @property
    def numberEditModeActive(self):
        return self._numberEditModeActive

    @numberEditModeActive.setter
    def numberEditModeActive(self, value):
        self._numberEditModeActive = value

    def getItemSettings(self, item):
        name, key = (item.descriptor.userKey, 'custom') if item.priceGroup == 'custom' else (item.id, 'remap')
        settings = self._currentSettings[key].setdefault(name, {})
        origSettings = g_config.camouflages[key].get(name, {})
        settings.setdefault('season', origSettings.get('season', []) or [
            x for x in SEASONS_CONSTANTS.SEASONS if SEASON_NAME_TO_TYPE[x] & item.season])
        settings.setdefault('random_mode', origSettings.get('random_mode', SelectionMode.RANDOM))
        settings.setdefault('ally', origSettings.get('ally', True))
        settings.setdefault('enemy', origSettings.get('enemy', True))
        return settings

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
                        if camoSeason & ~SeasonType.EVENT == itemSeasons:
                            del camoSetting['season']
                    elif origSetting['season'] == camoSetting['season']:
                        del camoSetting['season']
                for team in ('ally', 'enemy'):
                    if team in camoSetting:
                        if origSetting.get(team, True) == camoSetting[team]:
                            del camoSetting[team]
                if 'random_mode' in camoSetting:
                    if camoSetting['random_mode'] == origSetting.get('random_mode', SelectionMode.RANDOM):
                        del camoSetting['random_mode']
                if not camoSetting:
                    del itemSettings[camoID]
        return allSettings

    @classmethod
    def deleteEmpty(cls, settings):
        for key, value in settings.items():
            if key == 'camo' and g_currentVehicle.item.turret.isGunCarriage:
                value.pop('turret', None)
            elif isinstance(value, dict):
                cls.deleteEmpty(value)
                if not value:
                    del settings[key]

    def refreshOutfit(self):
        if self._mode == C11nMode.STYLE:
            if self._modifiedStyle:
                self._currentOutfit = self._modifiedStyle.getOutfit(self._currentSeason)
            else:
                self._currentOutfit = self.service.getEmptyOutfit()
        else:
            self._currentOutfit = self._modifiedOutfits[self._currentSeason]
        self.service.tryOnOutfit(self._currentOutfit)
        g_tankActiveCamouflage[g_currentVehicle.item.intCD] = self._currentSeason

    def tabChanged(self, tabIndex, update=False):
        if self.numberEditModeActive:
            self.sendNumberEditModeCommand(PersonalNumEditCommands.CANCEL_EDIT_MODE)
        self._tabIndex = tabIndex
        self._mode = C11nMode.CUSTOM
        if self._tabIndex == C11nTabs.EFFECT:
            self._selectedAnchor = C11nId(areaId=Area.MISC, slotType=GUI_ITEM_TYPE.MODIFICATION, regionIdx=0)
        elif self._tabIndex == C11nTabs.STYLE:
            self._mode = C11nMode.STYLE
            self._selectedAnchor = C11nId(areaId=Area.MISC, slotType=GUI_ITEM_TYPE.STYLE, regionIdx=0)
        else:
            self._selectedAnchor = C11nId()
        self._selectedCarouselItem = CaruselItemData()
        if update:
            self.onCustomizationTabsUpdated(tabIndex)
        else:
            self.onCustomizationTabChanged(tabIndex)
        self.onCustomizationModeChanged(self._mode)

    def installItem(self, intCD, slotId, seasonIdx, component=None):
        if slotId is None:
            return False
        item = self.service.getItemByCD(intCD)
        prevItem = self.getItemFromRegion(slotId)
        if prevItem is None or prevItem != item and self.isBuy and self.isBuyLimitReached(item):
            SystemMessages.pushI18nMessage(SYSTEM_MESSAGES.CUSTOMIZATION_PROHIBITED, type=SystemMessages.SM_TYPE.Warning,
                                           itemName=item.userName)
            return False
        if slotId.slotType == GUI_ITEM_TYPE.STYLE:
            if self.isBuy:
                self._modifiedStyle = item
            else:
                self._modifiedCSStyle = item
        else:
            season = SEASON_IDX_TO_TYPE.get(seasonIdx, self._currentSeason)
            outfit = self._modifiedOutfits[season]
            if self.numberEditModeActive and item.itemTypeID != GUI_ITEM_TYPE.PERSONAL_NUMBER:
                self.sendNumberEditModeCommand(PersonalNumEditCommands.CANCEL_BY_INSCRIPTION_SELECT)
            outfit.getContainer(slotId.areaId).slotFor(slotId.slotType).set(
                item, idx=slotId.regionIdx, component=component)
            outfit.invalidate()
        self.refreshOutfit()
        buyLimitReached = self.isBuyLimitReached(item)
        self.onCustomizationItemInstalled(item, component, slotId, buyLimitReached)
        return True

    def isPossibleToInstallToAllTankAreas(self, season, slotType, currentSlotData):
        return not self.isBuy or super(CustomizationContext, self).isPossibleToInstallToAllTankAreas(
            season, slotType, currentSlotData)

    def isPossibleToInstallItemForAllSeasons(self, areaID, slotType, regionIdx, currentSlotData):
        return not self.isBuy or super(CustomizationContext, self).isPossibleToInstallItemForAllSeasons(
            areaID, slotType, regionIdx, currentSlotData)

    def getLockedProjectionDecalSeasons(self, regionIdx):
        return [] if not self.isBuy else super(CustomizationContext, self).getLockedProjectionDecalSeasons(regionIdx)

    def removeStyle(self, intCD):
        if self.isBuy:
            if self._modifiedStyle and self._modifiedStyle.intCD == intCD:
                self._modifiedStyle = None
        elif self._mode == CSMode.INSTALL:
            if self._modifiedCSStyle and self._modifiedCSStyle.intCD == intCD:
                self._modifiedCSStyle = None
        self.refreshOutfit()
        self.onCustomizationItemsRemoved()

    def switchToCustom(self):
        pass

    def switchToStyle(self):
        if self.numberEditModeActive:
            self.sendNumberEditModeCommand(PersonalNumEditCommands.CANCEL_EDIT_MODE)
        self._lastTab[self._actualMode] = self._tabIndex
        self._actualMode = (self._mode + 1) % len(CSMode.NAMES)
        self.refreshOutfit()
        self.tabChanged(self._lastTab[self._actualMode])
        self.onCustomizationModeChanged(self._mode)

    def cancelChanges(self):
        self._currentSettings = {'custom': {}, 'remap': {}}
        super(CustomizationContext, self).cancelChanges()

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
        if self._tabIndex == C11nTabs.STYLE:
            self._currentOutfit = style.getOutfit(self._currentSeason)
        else:
            self._currentOutfit = self._modifiedOutfits[self._currentSeason]

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

    # noinspection PyMethodOverriding
    def updateVisibleTabsList(self, visibleTabs):
        for seasonType in SeasonType.COMMON_SEASONS:
            self.__visibleTabs[seasonType] = sorted(visibleTabs[seasonType])
        tabIndex = self._lastTab[self._mode]
        if tabIndex not in self.visibleTabs:
            tabIndex = first(self.visibleTabs, -1)
        self._lastTab[self._actualMode] = tabIndex
        self._tabIndex = tabIndex
        self.tabChanged(tabIndex, update=True)


@overrideMethod(CustomizationService, 'getCtx')
def new_getCtx(base, self):
    if not g_config.data['enabled']:
        return base(self)
    if not self._CustomizationService__customizationCtx:
        self._CustomizationService__customizationCtx = CustomizationContext()
        self._CustomizationService__customizationCtx.init()
    return self._CustomizationService__customizationCtx
