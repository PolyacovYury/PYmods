import operator

import Event
from CurrentVehicle import g_currentVehicle
from PYmodsCore import overrideMethod, loadJson
from gui.Scaleform.daapi.view.lobby.customization.customization_inscription_controller import PersonalNumEditCommands
from gui.Scaleform.daapi.view.lobby.customization.shared import C11nTabs, SEASON_TYPE_TO_NAME, C11nMode, TYPES_ORDER, \
    TABS_SLOT_TYPE_MAPPING, SEASONS_ORDER, getCustomPurchaseItems, getStylePurchaseItems, OutfitInfo, getItemInventoryCount, \
    getStyleInventoryCount
from gui.Scaleform.genConsts.SEASONS_CONSTANTS import SEASONS_CONSTANTS
from gui.customization.context import CustomizationContext as WGCtx, CaruselItemData
from gui.customization.shared import C11nId, __isTurretCustomizable as isTurretCustom
from gui.shared.gui_items import GUI_ITEM_TYPE, GUI_ITEM_TYPE_NAMES
from gui.shared.gui_items.customization.outfit import Area
from items.components.c11n_constants import SeasonType
from items.customizations import EmptyComponent
from items.vehicles import g_cache
from shared_utils import first
from .shared import CSMode
from .. import g_config
from ..constants import SelectionMode, SEASON_NAME_TO_TYPE


class CustomizationContext(WGCtx):
    @property
    def isBuy(self):
        return self.actualMode == CSMode.BUY

    @property
    def _originalOutfits(self):
        return self.__originalOutfits if self.isBuy else self._originalModdedOutfits

    @_originalOutfits.setter
    def _originalOutfits(self, value):
        self.__originalOutfits = value

    @property
    def _modifiedOutfits(self):
        return self.__modifiedOutfits if self.isBuy else self._modifiedModdedOutfits

    @_modifiedOutfits.setter
    def _modifiedOutfits(self, value):
        self.__modifiedOutfits = value

    @property
    def _originalStyle(self):
        return self.__originalStyle if self.isBuy else self._originalModdedStyle

    @_originalStyle.setter
    def _originalStyle(self, value):
        self.__originalStyle = value

    @property
    def _modifiedStyle(self):
        return self.__modifiedStyle if self.isBuy else self._modifiedModdedStyle

    @_modifiedStyle.setter
    def _modifiedStyle(self, value):
        if self.isBuy:
            self.__modifiedStyle = value
        else:
            self._modifiedModdedStyle = value

    def __init__(self):
        self.actualMode = CSMode.BUY
        super(CustomizationContext, self).__init__()
        self.actualMode = CSMode.INSTALL
        self.onActualModeChanged = Event.Event(self._eventsManager)
        self.__switcherIgnored = False
        self._lastTab = {CSMode.BUY: C11nTabs.CAMOUFLAGE, CSMode.INSTALL: C11nTabs.CAMOUFLAGE}
        self._originalModdedOutfits = {}
        self._modifiedModdedOutfits = {}
        self._originalModdedStyle = None
        self._modifiedModdedStyle = None
        self.__originalOutfits = {}
        self.__modifiedOutfits = {}
        self.__originalStyle = None
        self.__modifiedStyle = None
        self._currentSettings = {'custom': {}, 'remap': {}}

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

    def _cleanSettings(self):
        camouflages = g_cache.customization20().camouflages
        for key, settings in self._currentSettings.iteritems():
            for ID, conf in settings.items():
                orig = g_config.camouflages[key].get(ID, {})
                if 'season' in conf and (
                        camouflages[ID].season & ~SeasonType.EVENT == reduce(
                            operator.ior, (SEASON_NAME_TO_TYPE[x] for x in conf['season']), SeasonType.UNDEFINED)
                        if 'season' not in orig else orig['season'] == conf['season']):
                    del conf['season']
                for team in ('ally', 'enemy'):
                    if team in conf and orig.get(team, True) == conf[team]:
                        del conf[team]
                if 'random_mode' in conf and conf['random_mode'] == orig.get('random_mode', SelectionMode.RANDOM):
                    del conf['random_mode']
                if not conf:
                    del settings[ID]

    @classmethod
    def deleteEmpty(cls, settings):
        for key, value in settings.items():
            if key == GUI_ITEM_TYPE_NAMES[GUI_ITEM_TYPE.CAMOUFLAGE] and not isTurretCustom(g_currentVehicle.item.descriptor):
                value.pop(Area.TURRET, None)
            elif isinstance(value, dict):
                cls.deleteEmpty(value)
                if not value:
                    del settings[key]

    def getModdedOutfitsInfo(self):
        outfitsInfo = {}
        for season in SEASONS_ORDER:
            outfitsInfo[season] = OutfitInfo(self._originalModdedOutfits[season], self._modifiedModdedOutfits[season])
        return outfitsInfo

    def getModdedPurchaseItems(self):
        if self._mode == C11nMode.CUSTOM:
            currentSeason = self.currentSeason
            order = [currentSeason] + [s for s in SEASONS_ORDER if s != currentSeason]
            return getCustomPurchaseItems(self.getModdedOutfitsInfo(), order)
        return getStylePurchaseItems(OutfitInfo(self._originalModdedStyle, self._modifiedModdedStyle))

    def applyModdedStuff(self):
        self.applyModdedSettings()
        self.applyModdedItems()

    def applyModdedSettings(self):
        self._cleanSettings()
        for itemsKey in self._currentSettings:
            for camoName in self._currentSettings[itemsKey]:
                g_config.camouflages[itemsKey].setdefault(camoName, {}).update(self._currentSettings[itemsKey][camoName])
        if self._currentSettings['remap']:
            newSettings = {'disable': g_config.disable, 'remap': g_config.camouflages['remap']}
            loadJson(g_config.ID, 'settings', newSettings, g_config.configPath, True)
        if self._currentSettings['custom']:
            for confFolderName in g_config.configFolders:
                configFolder = g_config.configFolders[confFolderName]
                loadJson(g_config.ID, 'settings', {key: g_config.camouflages['custom'][key] for key in configFolder},
                         g_config.configPath + 'camouflages/' + confFolderName + '/', True, False)
        if any(self._currentSettings.itervalues()):
            g_config.collectCamouflageData()

    def applyModdedItems(self):  # TODO: whip up style saving (and applying, for that measure)
        self.itemsCache.onSyncCompleted -= self.__onCacheResync
        nationName, vehicleName = g_currentVehicle.item.descriptor.name.split(':')
        vehConfig = g_config.outfitCache.setdefault(nationName, {}).setdefault(vehicleName, {})
        for p in (x for x in self.getModdedPurchaseItems() if x.selected):
            seasonName = SEASON_TYPE_TO_NAME[p.group]
            typeName = GUI_ITEM_TYPE_NAMES[p.slot]
            area = Area.getName(p.areaID) if p.areaID != Area.MISC else 'misc'
            conf = vehConfig.setdefault(seasonName, {}).setdefault(typeName, {}).setdefault(area, {})
            origComponent = self.__originalOutfits[p.group].getContainer(p.areaID).slotFor(p.slot).getComponent(p.regionID)
            reg = str(p.regionID)
            if not origComponent if p.isDismantling else p.component.weak_eq(origComponent):
                conf.pop(reg, None)
            else:
                conf[reg] = (({f: getattr(p.component, f) for f, fd in p.component.fields.items() if not fd.weakEqualIgnored}
                             if not isinstance(p.component, EmptyComponent) else {'id': p.item.id})
                             if not p.isDismantling else {'id': None})
        self.deleteEmpty(g_config.outfitCache)
        loadJson(g_config.ID, 'outfitCache', g_config.outfitCache, g_config.configPath, True)
        print g_config.hangarCamoCache
        self.__onCacheResync()
        print g_config.hangarCamoCache
        self.itemsCache.onSyncCompleted += self.__onCacheResync

    # noinspection PyMethodOverriding
    def tabChanged(self, tabIndex):
        if self.numberEditModeActive:
            self.sendNumberEditModeCommand(PersonalNumEditCommands.CANCEL_EDIT_MODE)
        self._tabIndex = tabIndex
        mode = self._mode
        self._mode = C11nMode.CUSTOM
        if self._tabIndex == C11nTabs.EFFECT:
            self._selectedAnchor = C11nId(areaId=Area.MISC, slotType=GUI_ITEM_TYPE.MODIFICATION, regionIdx=0)
        elif self._tabIndex == C11nTabs.STYLE:
            self._mode = C11nMode.STYLE
            self._selectedAnchor = C11nId(areaId=Area.MISC, slotType=GUI_ITEM_TYPE.STYLE, regionIdx=0)
        else:
            self._selectedAnchor = C11nId()
        self._selectedCarouselItem = CaruselItemData()
        if self._mode != mode:
            self.refreshOutfit()
        self.onCustomizationTabChanged(tabIndex)
        if self._mode != mode:
            self.onCustomizationModeChanged(self._mode)

    def isPossibleToInstallToAllTankAreas(self, season, slotType, currentSlotData):
        return not self.isBuy or super(CustomizationContext, self).isPossibleToInstallToAllTankAreas(
            season, slotType, currentSlotData)

    def isPossibleToInstallItemForAllSeasons(self, areaID, slotType, regionIdx, currentSlotData):
        return not self.isBuy or super(CustomizationContext, self).isPossibleToInstallItemForAllSeasons(
            areaID, slotType, regionIdx, currentSlotData)

    def removeStyle(self, intCD):
        if self.isBuy:
            if self.__modifiedStyle and self.__modifiedStyle.intCD == intCD:
                self.__modifiedStyle = None
        elif self.actualMode == CSMode.INSTALL:
            if self._modifiedModdedStyle and self._modifiedModdedStyle.intCD == intCD:
                self._modifiedModdedStyle = None
        self.refreshOutfit()
        self.onCustomizationItemsRemoved()

    def switchToCustom(self):
        self.switchToStyle()

    def switchToStyle(self):
        if self.__switcherIgnored:
            self.__switcherIgnored = False
            return
        self.__switcherIgnored = True
        if self.numberEditModeActive:
            self.sendNumberEditModeCommand(PersonalNumEditCommands.CANCEL_EDIT_MODE)
        self._lastTab[self.actualMode] = self._tabIndex
        self.actualMode = (self.actualMode + 1) % len(CSMode.NAMES)
        self.onActualModeChanged()  # this will cause the carousel to update, which will call onTabChanged anyway
        self.refreshOutfit()

    def cancelChanges(self):
        self._currentSettings = {'custom': {}, 'remap': {}}
        super(CustomizationContext, self).cancelChanges()

    def isOnly1ChangedNumberInEditMode(self):
        if self.numberEditModeActive and not g_currentVehicle.item.descriptor.type.hasCustomDefaultCamouflage:
            purchaseItems = [it for it in (self.getPurchaseItems() if self.isBuy else self.getModdedPurchaseItems())
                             if not it.isDismantling and it.group == self.currentSeason]
            return len(purchaseItems) == 1 and purchaseItems[0].item.itemTypeID == GUI_ITEM_TYPE.PERSONAL_NUMBER
        return False

    def getOutfitsInfo(self):
        outfitsInfo = {}
        for season in SEASONS_ORDER:
            outfitsInfo[season] = OutfitInfo(self.__originalOutfits[season], self.__modifiedOutfits[season])
        return outfitsInfo

    def getPurchaseItems(self):
        if self._mode == C11nMode.CUSTOM:
            currentSeason = self.currentSeason
            order = [currentSeason] + [s for s in SEASONS_ORDER if s != currentSeason]
            return getCustomPurchaseItems(self.getOutfitsInfo(), order)
        return getStylePurchaseItems(OutfitInfo(self.__originalStyle, self.__modifiedStyle), buyMore=self.__prolongStyleRent)

    def getItemInventoryCount(self, item):
        return (getItemInventoryCount(item, self.getOutfitsInfo()) if self._mode == C11nMode.CUSTOM else
                getStyleInventoryCount(item, OutfitInfo(self.__originalStyle, self.__modifiedStyle)))

    def prolongStyleRent(self, style):
        self._lastTab[CSMode.BUY] = C11nTabs.STYLE
        super(CustomizationContext, self).prolongStyleRent(style)

    def applyItems(self, purchaseItems):
        mode = self.actualMode
        self.actualMode = CSMode.BUY
        print g_config.hangarCamoCache
        super(CustomizationContext, self).applyItems(purchaseItems)
        self.actualMode = mode
        self.applyModdedStuff()

    def init(self):  # TODO: rewrite
        super(CustomizationContext, self).init()
        if self._originalStyle:
            self._mode = C11nMode.STYLE
            self._tabIndex = C11nTabs.STYLE
        else:
            self._mode = C11nMode.CUSTOM
            self._tabIndex = C11nTabs.PAINT
            notInst = all([not self._originalOutfits[season].isInstalled() for season in SeasonType.COMMON_SEASONS])
            if notInst and not self.isOutfitsEmpty(self._modifiedOutfits) and not self._modifiedStyle:
                self._mode = C11nMode.STYLE
        self._originalMode = self._mode
        self.refreshOutfit()

    def isOutfitsModified(self):  # TODO: rewrite
        if self._mode == self._originalMode:
            if self._mode == C11nMode.STYLE:
                if self._modifiedStyle and self._originalStyle:
                    return self._modifiedStyle.intCD != self._originalStyle.intCD or self._autoRentEnabled != g_currentVehicle.item.isAutoRentStyle
                return not (self._modifiedStyle is None and self._originalStyle is None)
            if self.numberEditModeActive and self.isOnly1ChangedNumberInEditMode() and self._numberIsEmpty:
                return False
            for season in SeasonType.COMMON_SEASONS:
                outfit = self._modifiedOutfits[season]
                currOutfit = self._originalOutfits[season]
                if not currOutfit.isEqual(outfit) or not outfit.isEqual(currOutfit):
                    return True

            return False
        else:
            if self._mode == C11nMode.CUSTOM:
                if self.isOutfitsEmpty(self._modifiedOutfits) and self._originalStyle is None:
                    return False
            elif self._modifiedStyle is None and self.isOutfitsEmpty(self._originalOutfits):
                return False
            return True

    def isBuyLimitReached(self, item):
        return self.isBuy and super(CustomizationContext, self).isBuyLimitReached(item)

    def __carveUpOutfits(self):
        for season in SeasonType.COMMON_SEASONS:
            outfit = self.service.getCustomOutfit(season)
            self.__modifiedOutfits[season] = outfit.copy()
            if outfit.isInstalled():
                self.__originalOutfits[season] = outfit.copy()
            else:
                self.__originalOutfits[season] = self.service.getEmptyOutfit()
            for slot in self.__modifiedOutfits[season].slots():
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
            applyCamoCache(outfit, vehName, seasonCache.get(GUI_ITEM_TYPE_NAMES[GUI_ITEM_TYPE.CAMOUFLAGE], {}))
            applyPlayerCache(outfit, vehName, seasonCache)
            self._originalModdedOutfits[season] = outfit.copy()
            applyCamoCache(outfit, vehName, g_config.hangarCamoCache.get(nationName, {}).get(vehName, {}).get(seasonName, {}))
            self._modifiedModdedOutfits[season] = outfit.copy()
        # TODO: add CamoSelector style getter
        style = self.service.getCurrentStyle()
        if self.service.isCurrentStyleInstalled():
            self.__originalStyle = style
            self.__modifiedStyle = style
        else:
            self.__originalStyle = None
            if style and style.isHidden and style.fullInventoryCount(g_currentVehicle.item) == 0:
                self.__modifiedStyle = None
            else:
                self.__modifiedStyle = style
        if self._tabIndex == C11nTabs.STYLE:
            self._currentOutfit = style.getOutfit(self._currentSeason)
        else:
            self._currentOutfit = self._modifiedOutfits[self._currentSeason]

    # noinspection SpellCheckingInspection
    def __cancelModifiedOufits(self):
        for season in SeasonType.COMMON_SEASONS:
            self.__modifiedOutfits[season] = self.__originalOutfits[season].copy()
            self._modifiedModdedOutfits[season] = self._originalModdedOutfits[season].copy()

    def __cancelModifiedStyle(self):
        self.__modifiedStyle = self.__originalStyle
        self._modifiedModdedStyle = self._originalModdedStyle

    def __preserveState(self):
        self._state.update(
            modifiedStyle=self.__modifiedStyle,
            modifiedOutfits={season: outfit.copy() for season, outfit in self.__modifiedOutfits.iteritems()},
            modifiedModdedStyle=self._modifiedModdedStyle,
            modifiedModdedOutfits={season: outfit.copy() for season, outfit in self._modifiedModdedOutfits.iteritems()})

    def __restoreState(self):
        self.__modifiedStyle = self._state.get('modifiedStyle')
        self.__modifiedOutfits = self._state.get('modifiedOutfits')
        if self.__modifiedStyle:
            self.__modifiedStyle = self.service.getItemByCD(self.__modifiedStyle.intCD)
        self._modifiedModdedStyle = self._state.get('modifiedModdedStyle')
        self._modifiedModdedOutfits = self._state.get('modifiedModdedOutfits')
        if self._modifiedModdedStyle:
            self._modifiedModdedStyle = self.service.getItemByCD(self._modifiedModdedStyle.intCD)
        self._state.clear()

    # noinspection PyMethodOverriding
    def updateVisibleTabsList(self, visibleTabs):
        for s in SeasonType.COMMON_SEASONS:
            self.__visibleTabs[s] = sorted(visibleTabs[s], key=lambda it: TYPES_ORDER.index(TABS_SLOT_TYPE_MAPPING[it]))
        tabIndex = self._lastTab[self.actualMode]
        if tabIndex not in self.visibleTabs:
            tabIndex = first(self.visibleTabs, -1)
        self._lastTab[self.actualMode] = tabIndex
        self.tabChanged(tabIndex)


@overrideMethod(WGCtx, '__new__')
def new(base, cls, *a, **kw):
    if not g_config.data['enabled']:
        return base(cls, *a, **kw)
    return base(CustomizationContext, *a, **kw)
