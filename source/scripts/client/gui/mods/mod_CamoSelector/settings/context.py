import operator

import Event
from CurrentVehicle import g_currentVehicle
from PYmodsCore import overrideMethod, loadJson
from gui import SystemMessages
from gui.Scaleform.daapi.view.lobby.customization.customization_inscription_controller import PersonalNumEditCommands
from gui.Scaleform.daapi.view.lobby.customization.shared import C11nTabs, SEASON_TYPE_TO_NAME, C11nMode, TYPES_ORDER, \
    TABS_SLOT_TYPE_MAPPING, SEASONS_ORDER, getCustomPurchaseItems, getStylePurchaseItems, OutfitInfo, getItemInventoryCount, \
    getStyleInventoryCount, AdditionalPurchaseGroups, SEASON_TYPE_TO_IDX
from gui.Scaleform.genConsts.SEASONS_CONSTANTS import SEASONS_CONSTANTS
from gui.Scaleform.locale.MESSENGER import MESSENGER
from gui.SystemMessages import SM_TYPE
from gui.customization.context import CustomizationContext as WGCtx, CaruselItemData
from gui.customization.shared import C11nId, __isTurretCustomizable as isTurretCustom, \
    getAppliedRegionsForCurrentHangarVehicle
from gui.shared.gui_items import GUI_ITEM_TYPE, GUI_ITEM_TYPE_NAMES
from gui.shared.gui_items.customization.outfit import Area
from items.components.c11n_constants import SeasonType
from items.customizations import EmptyComponent
from items.vehicles import g_cache
from shared_utils import first
from .shared import CSMode
from .. import g_config
from ..constants import SelectionMode, SEASON_NAME_TO_TYPE
from ..processors import deleteEmpty, applyOutfitCache


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
        self.__originalMode = {CSMode.BUY: C11nMode.CUSTOM, CSMode.INSTALL: C11nMode.CUSTOM}
        self.actualMode = CSMode.INSTALL
        self.onActualModeChanged = Event.Event(self._eventsManager)
        self.__switcherIgnored = False
        self._lastTab = {CSMode.BUY: C11nTabs.PAINT, CSMode.INSTALL: C11nTabs.CAMOUFLAGE}
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

    def installStyleItemsToModifiedOutfits(self, proceed):
        if not proceed:
            return
        for season in SEASONS_ORDER:
            outfit = self._modifiedStyle.getOutfit(season).copy()
            self._modifiedModdedOutfits[season] = newOutfit = self.service.getEmptyOutfit()
            for slotType in GUI_ITEM_TYPE.CUSTOMIZATIONS_WITHOUT_STYLE:
                for areaId in Area.ALL:
                    regionsIndexes = getAppliedRegionsForCurrentHangarVehicle(areaId, slotType)
                    fromSlot = outfit.getContainer(areaId).slotFor(slotType)
                    toSlot = newOutfit.getContainer(areaId).slotFor(slotType)
                    for regionIdx in regionsIndexes:
                        currentSlotData = fromSlot.getSlotData(regionIdx)
                        toSlot.set(currentSlotData.item, idx=regionIdx, component=currentSlotData.component)
            newOutfit.invalidate()
        self.tabChanged(C11nTabs.CAMOUFLAGE)

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

    def getModdedOutfitsInfo(self):
        outfitsInfo = {}
        for season in SEASONS_ORDER:
            outfitsInfo[season] = OutfitInfo(self._originalModdedOutfits[season], self._modifiedModdedOutfits[season])
        return outfitsInfo

    def getModdedPurchaseItems(self):
        if self._lastTab[CSMode.INSTALL] != C11nTabs.STYLE:
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
            SystemMessages.pushI18nMessage(g_config.i18n['flashCol_serviceMessage_settings'], type=SM_TYPE.Information)

    def applyModdedItems(self):
        self.itemsCache.onSyncCompleted -= self.__onCacheResync
        vDesc = g_currentVehicle.item.descriptor
        nationName, vehicleName = vDesc.name.split(':')
        isTurretCustomisable = isTurretCustom(vDesc)
        vehCache = g_config.outfitCache.setdefault(nationName, {}).setdefault(vehicleName, {})
        anything = False
        for p in (x for x in self.getModdedPurchaseItems() if x.selected):
            anything = True
            if p.group == AdditionalPurchaseGroups.STYLES_GROUP_ID:
                vehCache.setdefault('style', {}).update(intCD=p.item.intCD if not p.isDismantling else None, applied=True)
                break  # there will only ever be one, but just to make sure...
            else:
                vehCache.get('style', {}).update(applied=False)
            typeName = GUI_ITEM_TYPE_NAMES[p.slot]
            seasonName = SEASON_TYPE_TO_NAME[p.group]
            area = Area.getName(p.areaID) if p.areaID != Area.MISC else 'misc'
            conf = vehCache.setdefault(seasonName, {}).setdefault(typeName, {}).setdefault(area, {})
            origComponent = self.__originalOutfits[p.group].getContainer(p.areaID).slotFor(p.slot).getComponent(p.regionID)
            reg = str(p.regionID)
            if p.slot == GUI_ITEM_TYPE.CAMOUFLAGE:
                seasonCache = g_config.hangarCamoCache.get(nationName, {}).get(vehicleName, {}).get(seasonName, {})
                seasonCache.get(typeName, {}).get(area, {}).pop(reg, None)
                deleteEmpty(seasonCache, isTurretCustomisable)
            if not origComponent if p.isDismantling else p.component.weak_eq(origComponent):
                conf.pop(reg, None)
            else:
                conf[reg] = (({f: getattr(p.component, f) for f, fd in p.component.fields.items() if not fd.weakEqualIgnored}
                              if not isinstance(p.component, EmptyComponent) else {'id': p.item.id})
                             if not p.isDismantling else {'id': None})
        if not anything and self._mode != self.__originalMode[self.actualMode]:
            vehCache.get('style', {}).update(applied=False)  # if an "empty" style is applied - 'anything' is already true
            anything = True
        if vehCache.get('style', {}) == {'intCD': None, 'applied': False}:
            vehCache.pop('style', None)
        if anything:
            SystemMessages.pushI18nMessage(
                MESSENGER.SERVICECHANNELMESSAGES_SYSMSG_CONVERTER_CUSTOMIZATIONS, type=SM_TYPE.Information)
        deleteEmpty(g_config.outfitCache, isTurretCustomisable)
        loadJson(g_config.ID, 'outfitCache', g_config.outfitCache, g_config.configPath, True)
        self.__onCacheResync()
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
        self._lastTab[self.actualMode] = self._tabIndex
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
        if self.numberEditModeActive:
            self.sendNumberEditModeCommand(PersonalNumEditCommands.CANCEL_NUMBER)
        origMode = self.actualMode
        for actualMode in CSMode.INSTALL, CSMode.BUY:
            self.actualMode = actualMode
            if self._lastTab[self.actualMode] == C11nTabs.STYLE:
                self.__cancelModifiedStyle()
            else:
                self.__cancelModifiedOufits()
        self.actualMode = origMode
        self.refreshOutfit()
        self.clearStoredPersonalNumber()
        self.onChangesCanceled()

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
        import inspect
        if not self.isBuy and inspect.stack()[1][0].f_code.co_name == 'buildList':
            return self.getModdedPurchaseItems()
        if self._lastTab[CSMode.BUY] != C11nTabs.STYLE:
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
        super(CustomizationContext, self).applyItems(purchaseItems)
        self.actualMode = mode
        self.applyModdedStuff()

    def init(self):
        super(CustomizationContext, self).init()
        origMode = self.actualMode
        for mode in CSMode.BUY, CSMode.INSTALL:
            self.actualMode = mode
            notInst = all([not self._originalOutfits[season].isInstalled() for season in SeasonType.COMMON_SEASONS])
            if self._originalStyle or notInst and not self.isOutfitsEmpty(self._modifiedOutfits) and not self._modifiedStyle:
                self.__originalMode[mode] = C11nMode.STYLE
                self._lastTab[mode] = C11nTabs.STYLE
            else:
                self.__originalMode[mode] = C11nMode.CUSTOM
        nation, vehName = g_currentVehicle.item.descriptor.name.split(':')
        for season in SeasonType.COMMON_SEASONS:
            outfit = self._modifiedModdedOutfits[season]
            seasonName = SEASON_TYPE_TO_NAME[season]
            applyOutfitCache(outfit, g_config.hangarCamoCache.get(nation, {}).get(vehName, {}).get(seasonName, {}))
        self.actualMode = origMode
        self._mode = self.__originalMode[origMode]
        self._tabIndex = self._lastTab[origMode]
        self.refreshOutfit()
        from functools import partial
        import BigWorld
        BigWorld.callback(0, partial(self.onCustomizationModeChanged, self._mode))  # because bottom_panel updates too early

    def isOutfitsModified(self):
        self._cleanSettings()
        if any(self._currentSettings.itervalues()):
            return True
        result = False
        origActualMode = self.actualMode
        origMode = self._mode
        for actualMode in CSMode.BUY, CSMode.INSTALL:
            self.actualMode = actualMode
            self._mode = C11nMode.STYLE if self._lastTab[actualMode] == C11nTabs.STYLE else C11nMode.CUSTOM
            self._originalMode = self.__originalMode[actualMode]
            result |= super(CustomizationContext, self).isOutfitsModified()
        self.actualMode = origActualMode
        self._mode = origMode
        return result

    def isBuyLimitReached(self, item):
        return self.isBuy and super(CustomizationContext, self).isBuyLimitReached(item)

    def __carveUpOutfits(self):
        origMode = self.actualMode
        self.actualMode = CSMode.BUY
        # noinspection PyUnresolvedReferences
        super(CustomizationContext, self)._CustomizationContext__carveUpOutfits()
        self.actualMode = origMode
        nationName, vehName = g_currentVehicle.item.descriptor.name.split(':')
        vehCache = g_config.outfitCache.get(nationName, {}).get(vehName, {})
        styleCache = vehCache.get('style', {'intCD': None, 'applied': False})
        for season in SeasonType.COMMON_SEASONS:
            outfit = self.service.getOutfit(season)
            if not outfit or outfit.modelsSet:
                outfit = self.service.getEmptyOutfit()
            else:
                outfit = outfit.copy()
            applyOutfitCache(outfit, vehCache.get(SEASON_TYPE_TO_NAME[season], {}))
            outfit._isInstalled = (outfit.isInstalled() or not outfit.isEmpty()) and not styleCache['applied']
            self._originalModdedOutfits[season] = outfit.copy()
            self._modifiedModdedOutfits[season] = outfit.copy()
        origStyle = self.service.getCurrentStyle()
        moddedStyle = None if styleCache['intCD'] is None else self.service.getItemByCD(styleCache['intCD'])
        if not moddedStyle and not styleCache['applied'] and self.service.isCurrentStyleInstalled():
            self._originalModdedStyle = origStyle
            self._modifiedModdedStyle = origStyle
        elif moddedStyle:
            self._modifiedModdedStyle = moddedStyle
            self._originalModdedStyle = moddedStyle if styleCache['applied'] else None
        if self._modifiedStyle:
            self._currentOutfit = self._modifiedStyle.getOutfit(self._currentSeason)
        else:
            self._currentOutfit = self._modifiedOutfits[self._currentSeason]

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
