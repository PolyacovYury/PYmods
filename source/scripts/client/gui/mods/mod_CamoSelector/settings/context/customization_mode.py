from copy import deepcopy

import BigWorld
from CurrentVehicle import g_currentVehicle
from PYmodsCore import loadJson
from adisp import async, process
from constants import CLIENT_COMMAND_SOURCES
from gui import SystemMessages
from gui.Scaleform.daapi.view.lobby.customization.context.custom_mode import CustomMode as WGCustomMode
from gui.Scaleform.daapi.view.lobby.customization.shared import (
    CustomizationTabs, ITEM_TYPE_TO_SLOT_TYPE, OutfitInfo, fitOutfit, getCurrentVehicleAvailableRegionsMap,
    getCustomPurchaseItems, getEditableStyleOutfitDiff, getSlotDataFromSlot, getStylePurchaseItems,
    isItemsQuantityLimitReached, isSlotFilled, removeItemFromEditableStyle, removeUnselectedItemsFromEditableStyle,
)
from gui.Scaleform.locale.MESSENGER import MESSENGER
from gui.customization.constants import CustomizationModes
from gui.customization.shared import C11nId, SEASON_TYPE_TO_NAME, __isTurretCustomizable as isTurretCustom
from gui.shared.gui_items import GUI_ITEM_TYPE, GUI_ITEM_TYPE_NAMES
from gui.shared.gui_items.processors.common import OutfitApplier
from helpers import dependency
from items.components.c11n_constants import SeasonType
from items.customizations import EmptyComponent, FieldFlags
from items.vehicles import g_cache
from skeletons.account_helpers.settings_core import ISettingsCore
from vehicle_outfit.outfit import Area, Outfit
from vehicle_systems.camouflages import getStyleProgressionOutfit
from .item_remap import ItemSettingsRemap
from ... import g_config
from ...processors import applyOutfitCache, deleteEmpty


class CustomMode(WGCustomMode, ItemSettingsRemap):
    modeId = CustomizationModes.CAMO_SELECTOR
    _tabs = CustomizationTabs.ALL
    _settingsCore = dependency.descriptor(ISettingsCore)
    STYLE_SLOT = C11nId(areaId=Area.MISC, slotType=GUI_ITEM_TYPE.STYLE, regionIdx=0)
    __SELF_INSTALL_ITEM_TYPES = {
        GUI_ITEM_TYPE.MODIFICATION: C11nId(areaId=Area.MISC, slotType=GUI_ITEM_TYPE.MODIFICATION, regionIdx=0),
        GUI_ITEM_TYPE.STYLE: STYLE_SLOT,
        GUI_ITEM_TYPE.INSIGNIA: C11nId(areaId=Area.GUN, slotType=GUI_ITEM_TYPE.INSIGNIA, regionIdx=0)}

    def __init__(self, ctx):
        WGCustomMode.__init__(self, ctx)
        self.__originalStyle = None
        self.__modifiedStyle = None
        self._cache = deepcopy(g_config.getHangarCache())

    @property
    def originalStyle(self):
        return self.__originalStyle

    @property
    def modifiedStyle(self):
        raise NotImplementedError
        return self.__modifiedStyle

    def isAutoRentEnabled(self):
        return False

    def changeAutoRent(self, source=CLIENT_COMMAND_SOURCES.UNDEFINED):
        pass

    def getStyleInfo(self):
        raise NotImplementedError
        return OutfitInfo(self.__originalStyle, self.__modifiedStyle)

    def getDependenciesData(self):
        raise NotImplementedError
        return self.__modifiedStyle.getDependenciesIntCDs() if self.__modifiedStyle else {}

    def isPossibleToInstallToAllTankAreas(self, intCD, slotType):
        return True

    def isPossibleToInstallItemForAllSeasons(self, slotId, intCD):
        return True

    def getItemInventoryCount(self, item, excludeBase=False):
        return 10  # should be enough to plaster any vehicle

    def _validateItem(self, item, slotId, season):
        return []

    def _selectInsignia(self, *_):
        if self._tabId == 8:
            BigWorld.callback(0, lambda: self.selectSlot(C11nId(Area.GUN, GUI_ITEM_TYPE.INSIGNIA, 0)))

    def changeTab(self, tabId, itemCD=None):
        if self._tabId != tabId == 8:
            BigWorld.callback(0, self._selectInsignia)
        WGCustomMode.changeTab(self, tabId, itemCD)

    def _onStart(self):
        WGCustomMode._onStart(self)
        self._events.onSeasonChanged += self._selectInsignia

    def _onStop(self):
        self._events.onSeasonChanged -= self._selectInsignia
        WGCustomMode._onStop(self)

    def getPurchaseItems(self):
        raise NotImplementedError
        return (getStylePurchaseItems(
            self.__modifiedStyle, self.getModifiedOutfits(), progressionLevel=self.getStyleProgressionLevel())
                if self.__modifiedStyle is not None else
                getCustomPurchaseItems(self._ctx.season, self.getModifiedOutfits()))

    def removeItemsFromSeason(self, season=None, filterMethod=None, refresh=True):
        season = season or self.season
        outfit = self._modifiedOutfits[season]
        for intCD, _, regionIdx, container, _ in outfit.itemsFull():
            item = self._service.getItemByCD(intCD)
            if filterMethod is None or filterMethod(item):
                areaId = container.getAreaID()
                slotType = ITEM_TYPE_TO_SLOT_TYPE[item.itemTypeID]
                slotId = C11nId(areaId, slotType, regionIdx)
                self.removeItem(slotId, season, refresh=False)
        if refresh:
            self._ctx.refreshOutfit(season)
            self._events.onItemsRemoved()

    def removeStyle(self, intCD):
        raise NotImplementedError
        if self.__modifiedStyle is not None and self.__modifiedStyle.intCD == intCD:
            self.removeItem(self.STYLE_SLOT)

    def changeStyleProgressionLevel(self, toLevel):
        for seasonID in SeasonType.COMMON_SEASONS:
            self._modifiedOutfits[seasonID] = getStyleProgressionOutfit(self._modifiedOutfits[seasonID], toLevel, seasonID)
        self._fitOutfits(modifiedOnly=True)
        self._ctx.refreshOutfit()
        self._events.onComponentChanged(self.STYLE_SLOT, True)

    def getStyleProgressionLevel(self):
        raise NotImplementedError
        return self._modifiedOutfits[
            self.season].progressionLevel if self.__modifiedStyle and self.__modifiedStyle.isProgressive else -1

    def clearStyle(self):
        raise NotImplementedError
        style = self.__modifiedStyle
        if style is None:
            return
        vehicleCD = g_currentVehicle.item.descriptor.makeCompactDescr()
        for season in SeasonType.COMMON_SEASONS:
            outfit = style.getOutfit(season, vehicleCD=vehicleCD)
            self._modifiedOutfits[season] = outfit.copy()

        self._fitOutfits(modifiedOnly=True)
        self._ctx.refreshOutfit()
        self._ctx.events.onItemsRemoved()

    def _fillOutfits(self):
        raise NotImplementedError
        # styled
        styleId = self._service.getStyledOutfit(self.season).id
        style = self._service.getItemByID(GUI_ITEM_TYPE.STYLE, styleId) if styleId else None
        isInstalled = self._service.isStyleInstalled()
        if not isInstalled:
            if style is not None and style.isHidden and style.fullInventoryCount(g_currentVehicle.item.intCD) == 0:
                style = None
        self.__originalStyle = style
        self.__modifiedStyle = style
        vehicleCD = g_currentVehicle.item.descriptor.makeCompactDescr()
        diffs = self._ctx.stylesDiffsCache.getDiffs(style) if style is not None else {}
        for season in SeasonType.COMMON_SEASONS:
            if style is None:
                outfit = self._service.getEmptyOutfit()
            else:
                diff = diffs.get(season)
                if not isInstalled and diff is not None:
                    diffOutfit = Outfit(strCompactDescr=diff, vehicleCD=vehicleCD)
                    self._removeHiddenFromOutfit(diffOutfit, g_currentVehicle.item.intCD)
                    diff = diffOutfit.pack().makeCompDescr()
                outfit = style.getOutfit(season, vehicleCD=vehicleCD, diff=diff)
            self._originalOutfits[season] = outfit.copy()
            self._modifiedOutfits[season] = outfit.copy()
        # custom
        isInstalled = not self._service.isStyleInstalled()
        for season in SeasonType.COMMON_SEASONS:
            outfit = self._service.getCustomOutfit(season)
            if not isInstalled:
                self._removeHiddenFromOutfit(outfit, g_currentVehicle.item.intCD)
            if outfit is not None:
                self._originalOutfits[season] = outfit.copy()
                self._modifiedOutfits[season] = outfit.copy()
            self._originalOutfits[season] = self._service.getEmptyOutfit()
            self._modifiedOutfits[season] = self._service.getEmptyOutfit()
        # modded custom
        vehCache = g_config.getOutfitCache()
        fromOutfits = self.__getBaseOutfits()
        for season in SeasonType.COMMON_SEASONS:
            fromOutfit = fromOutfits[season]
            seasonName = SEASON_TYPE_TO_NAME[season]
            applyOutfitCache(fromOutfit, vehCache.get(seasonName, {}), False)
            self._originalOutfits[season] = fromOutfit.copy()
            applyOutfitCache(fromOutfit, self._cache.get(seasonName, {}))
            self._modifiedOutfits[season] = fromOutfit.copy()
        self._fitOutfits()
        # modded styled
        vehicleCD = g_currentVehicle.item.descriptor.makeCompactDescr()
        vehCache = g_config.getOutfitCache()
        styleCache = vehCache.get('style', {'intCD': None, 'applied': False})
        baseMode = self._ctx.getMode(CustomizationModes.STYLED)
        style = baseMode.originalStyle
        self._moddedStyle = None if styleCache['intCD'] is None else self._service.getItemByCD(styleCache['intCD'])
        if self._moddedStyle:
            style = self._moddedStyle
        self.__originalStyle = style
        self.__modifiedStyle = style
        for season in SeasonType.COMMON_SEASONS:
            if style is None:
                outfit = self._service.getEmptyOutfit()
            elif self._moddedStyle is None or (
                    style == baseMode.originalStyle
                    and self.getStyleProgressionLevel() == baseMode.getStyleProgressionLevel()):
                outfit = baseMode.getModifiedOutfit(season).copy()
            else:
                outfit = style.getOutfit(season, vehicleCD=vehicleCD).copy()
            if outfit.style and outfit.style.isProgression:
                progressionLevel = styleCache.get('level', 1)
                outfit = getStyleProgressionOutfit(outfit, progressionLevel, season)
            self._originalOutfits[season] = outfit.copy()
            self._modifiedOutfits[season] = outfit.copy()

    def _restoreState(self):
        raise NotImplementedError
        WGCustomMode._restoreState(self)
        styleId = self._modifiedOutfits[SeasonType.SUMMER].id
        self.__modifiedStyle = self._service.getItemByID(GUI_ITEM_TYPE.STYLE, styleId) if styleId else None

    def _unselectItem(self):
        if self._selectedItem is not None:
            if self._selectedItem.itemTypeID == GUI_ITEM_TYPE.STYLE:
                return False
            self._selectedItem = None
            self.__storedProgressionLevel = 0
            return True
        return False

    def _installItem(self, intCD, slotId, season=None, component=None):
        raise NotImplementedError
        item = self._service.getItemByCD(intCD)
        if item.itemTypeID == GUI_ITEM_TYPE.STYLE:
            # styled
            self.__modifiedStyle = item
            self._fitOutfits(modifiedOnly=True)
            self.isOutfitsModified()
            return True
        # custom
        outfit = self.currentOutfit if season is None else self._modifiedOutfits[season]
        if isItemsQuantityLimitReached(outfit, slotId.slotType) and not isSlotFilled(outfit, slotId):
            return False
        component = component or self._getComponent(item, slotId)
        multiSlot = outfit.getContainer(slotId.areaId).slotFor(slotId.slotType)
        multiSlot.set(item.intCD, idx=slotId.regionIdx, component=component)
        return True

    def _removeItem(self, slotId, season=None):
        raise NotImplementedError
        # custom
        outfit = self.currentOutfit if season is None else self._modifiedOutfits[season]
        multiSlot = outfit.getContainer(slotId.areaId).slotFor(slotId.slotType)
        multiSlot.remove(slotId.regionIdx)
        # styled
        if self.__modifiedStyle is None:
            return
        elif slotId == self.STYLE_SLOT:
            self.__modifiedStyle = None
            self._modifiedOutfits = {s: self._service.getEmptyOutfit() for s in SeasonType.COMMON_SEASONS}
        else:
            season = season or self.season
            outfit = self._modifiedOutfits[season]
            vehicleCD = g_currentVehicle.item.descriptor.makeCompactDescr()
            baseOutfit = self.__modifiedStyle.getOutfit(season, vehicleCD=vehicleCD)
            fitOutfit(baseOutfit, getCurrentVehicleAvailableRegionsMap())
            removeItemFromEditableStyle(outfit, baseOutfit, slotId)
            diff = getEditableStyleOutfitDiff(outfit, baseOutfit)
            self._ctx.stylesDiffsCache.saveDiff(self.__modifiedStyle, season, diff)
        # modded custom adds
        self.__addDefaultInsignia(self.getModifiedOutfit(season))

    @async
    @process
    def _applyItems(self, purchaseItems, isModeChanged, callback):
        raise NotImplementedError
        # custom
        modifiedOutfits = {season: outfit.copy() for season, outfit in self._modifiedOutfits.iteritems()}
        originalOutfits = self._ctx.startMode.getOriginalOutfits()
        for pItem in purchaseItems:
            if not pItem.selected:
                if pItem.slotType:
                    season = pItem.group
                    slot = modifiedOutfits[season].getContainer(pItem.areaID).slotFor(pItem.slotType)
                    slot.remove(pItem.regionIdx)

        if isModeChanged:
            modifiedSeasons = SeasonType.COMMON_SEASONS
        else:
            modifiedSeasons = tuple((season for season in SeasonType.COMMON_SEASONS if
                                     not modifiedOutfits[season].isEqual(self._originalOutfits[season])))
        self._soundEventChecker.lockPlayingSounds()
        yield OutfitApplier(
            g_currentVehicle.item, [(self._service.getEmptyOutfit(), season) for season in modifiedSeasons]).request()
        results = []
        requestData = []
        for season in modifiedSeasons:
            outfit = modifiedOutfits[season]
            if outfit.isEmpty():
                continue
            requestData.append((outfit, season))

        if requestData:
            result = yield OutfitApplier(g_currentVehicle.item, requestData).request()
            results.append(result)
        self._soundEventChecker.unlockPlayingSounds()
        if self.isInited:
            self._events.onItemsBought(originalOutfits, purchaseItems, results)
        callback(self)
        # styled
        results = []
        style = self.__modifiedStyle
        vehicleCD = g_currentVehicle.item.descriptor.makeCompactDescr()
        originalOutfits = self._ctx.startMode.getOriginalOutfits()
        if style is not None:
            baseStyleOutfits = {}
            modifiedStyleOutfits = {}
            for season in SeasonType.COMMON_SEASONS:
                diff = self._ctx.stylesDiffsCache.getDiffs(style).get(season)
                baseStyleOutfits[season] = style.getOutfit(season, vehicleCD=vehicleCD)
                modifiedStyleOutfits[season] = style.getOutfit(season, vehicleCD=vehicleCD, diff=diff)

            removeUnselectedItemsFromEditableStyle(modifiedStyleOutfits, baseStyleOutfits, purchaseItems)
            result = yield OutfitApplier(
                g_currentVehicle.item, [(outfit, season) for season, outfit in modifiedStyleOutfits.iteritems()]).request()
            results.append(result)
        else:
            outfit = self._modifiedOutfits[self.season]
            result = yield OutfitApplier(g_currentVehicle.item, ((outfit, SeasonType.ALL),)).request()
            results.append(result)
        if self.isInited:
            self._events.onItemsBought(originalOutfits, purchaseItems, results)
        callback(self)
        # modded custom
        vDesc = g_currentVehicle.item.descriptor
        nation, vehName = vDesc.name.split(':')
        isTurretCustomisable = isTurretCustom(vDesc)
        if self.isOutfitsModified() or isModeChanged:
            fromOutfits = self.__getBaseOutfits()
            SystemMessages.pushI18nMessage(
                MESSENGER.SERVICECHANNELMESSAGES_SYSMSG_CONVERTER_CUSTOMIZATIONS, type=SystemMessages.SM_TYPE.Information)
            cache = {}
            for season in SeasonType.COMMON_SEASONS:
                seasonName = SEASON_TYPE_TO_NAME[season]
                cache[seasonName] = seasonCache = self.computeDiff(fromOutfits[season], self.getModifiedOutfit(season))
                for typeName, typeCache in seasonCache.items():
                    if typeName != GUI_ITEM_TYPE_NAMES[GUI_ITEM_TYPE.CAMOUFLAGE]:
                        continue
                    for area, areaCache in typeCache.items():
                        for reg in areaCache:
                            g_config.getHangarCache().get(seasonName, {}).get(typeName, {}).get(area, {}).pop(reg, None)
            deleteEmpty(g_config.getHangarCache(), isTurretCustomisable)
            deleteEmpty(g_config.hangarCamoCache)
            deleteEmpty(cache, isTurretCustomisable)
            styleCache = g_config.getOutfitCache().get('style', {})
            orig_style = self._ctx.getMode(CustomizationModes.STYLED).modifiedStyle
            styleCache.setdefault('intCD', orig_style and orig_style.intCD)
            if styleCache['intCD'] is None:
                styleCache.pop('level', None)
            styleCache['applied'] = False
            if styleCache != {'intCD': None, 'applied': False} and cache:
                cache['style'] = styleCache
            g_config.outfitCache.setdefault(nation, {})[vehName] = cache
            deleteEmpty(cache, isTurretCustomisable)
            deleteEmpty(g_config.outfitCache)
            loadJson(g_config.ID, 'outfitCache', g_config.outfitCache, g_config.configPath, True)
            self._events.onItemsBought({}, [], [])
        callback(self)
        # modded styled
        vDesc = g_currentVehicle.item.descriptor
        nation, vehName = vDesc.name.split(':')
        isTurretCustomisable = isTurretCustom(vDesc)
        vehCache = g_config.outfitCache.setdefault(nation, {}).setdefault(vehName, {})
        if self.__originalStyle != self.__modifiedStyle or self._moddedStyle != self.__modifiedStyle or (
                self.__modifiedStyle and self.__modifiedStyle.isProgressive
                and self._originalOutfits[self.season].progressionLevel != self._modifiedOutfits[self.season].progressionLevel
        ) or isModeChanged:
            vehCache.setdefault('style', {}).update(intCD=self.__modifiedStyle and self.__modifiedStyle.intCD, applied=True)
            if self.__modifiedStyle:
                baseMode = self._ctx.getMode(CustomizationModes.STYLED)
                testCache = {'intCD': baseMode.modifiedStyle and baseMode.modifiedStyle.intCD, 'applied': True}
                g_config.getHangarCache().clear()
                deleteEmpty(g_config.hangarCamoCache)
                progressionLevel = self.getStyleProgressionLevel()
                if progressionLevel != -1:
                    vehCache['style']['level'] = progressionLevel
                    origLevel = baseMode.getStyleProgressionLevel()
                    if origLevel != -1:
                        testCache['level'] = origLevel
                if vehCache == {'style': testCache}:
                    vehCache.pop('style', None)
            else:
                vehCache['style'].pop('level', None)
            SystemMessages.pushI18nMessage(
                MESSENGER.SERVICECHANNELMESSAGES_SYSMSG_CONVERTER_CUSTOMIZATIONS, type=SystemMessages.SM_TYPE.Information)
            self._events.onItemsBought({}, [], [])
        deleteEmpty(vehCache, isTurretCustomisable)
        deleteEmpty(g_config.outfitCache)
        loadJson(g_config.ID, 'outfitCache', g_config.outfitCache, g_config.configPath, True)
        callback(self)
        # also
        self.applySettings()

    def _cancelChanges(self):
        raise NotImplementedError
        ItemSettingsRemap.cancelChanges(self)
        self.__modifiedStyle = self.__originalStyle
        self._cache.clear()
        WGCustomMode._cancelChanges(self)

    def _getAppliedItems(self, isOriginal=True):
        raise NotImplementedError
        appliedItems = WGCustomMode._getAppliedItems(self, isOriginal)
        style = self.__originalStyle if isOriginal else self.__modifiedStyle
        if style is not None:
            appliedItems.add(style.intCD)
        return appliedItems

    def iterOutfit(self, outfit):
        for container in outfit.containers():
            for slot in container.slots():
                for regionIdx in range(slot.capacity()):
                    slotData = slot.getSlotData(regionIdx)
                    if slotData and slotData.intCD:
                        yield container, slot, regionIdx, slotData.intCD, slotData.component
                    else:
                        yield container, slot, regionIdx, None, None

    def computeDiff(self, original, modified):
        self.__addDefaultInsignia(original)
        self.__addDefaultInsignia(modified)
        seasonCache = {}
        for container, slot, regionIdx, o_intCD, o_component in self.iterOutfit(original):
            slotType = ITEM_TYPE_TO_SLOT_TYPE.get(slot.getTypes()[0])  # checks that this slot is not for attachments
            if slotType is None:
                continue
            areaID = container.getAreaID()
            m = getSlotDataFromSlot(modified, C11nId(areaID, slotType, regionIdx))
            area = Area.getName(areaID) if areaID != Area.MISC else 'misc'
            seasonCache.setdefault(GUI_ITEM_TYPE_NAMES[slotType], {}).setdefault(area, {})[str(regionIdx)] = item_data = {}
            if not m.intCD:
                if o_component:
                    item_data['id'] = None
            elif o_intCD != m.intCD or not m.component.weak_eq(o_component):
                if isinstance(m.component, EmptyComponent):
                    item_data['id'] = self._service.getItemByCD(m.intCD).id
                else:
                    item_data.update({
                        f: getattr(m.component, f) for f, fd in m.component.fields.items()
                        if not fd.flags & (FieldFlags.DEPRECATED | FieldFlags.WEAK_EQUAL_IGNORED)})
        deleteEmpty(seasonCache)
        return seasonCache

    def __addDefaultInsignia(self, outfit):
        cache = g_cache.customization20()
        if not outfit.gun.slotFor(GUI_ITEM_TYPE.INSIGNIA).getItemCD():
            outfit.gun.slotFor(GUI_ITEM_TYPE.INSIGNIA).set(
                cache.insignias[cache.defaultInsignias[
                    g_currentVehicle.item.descriptor.type.customizationNationID]].compactDescr)
            outfit.gun.unpack(outfit.pack())

    def __getBaseOutfits(self):
        outfits = self._ctx.getMode(self._ctx.purchaseModeId).getModifiedOutfits()
        for outfit in outfits.itervalues():
            self.__addDefaultInsignia(outfit)
        return outfits

    def safe_getOutfitFromStyle(self, vehicleCD, season, style, level, baseStyle, baseOutfit):
        if style is None:
            return self._service.getEmptyOutfit()
        level = level or 1
        if style == baseStyle:
            if style.isProgressive and level != baseOutfit.progressionLevel:
                return getStyleProgressionOutfit(baseOutfit, level, season).copy()
            return baseOutfit.copy()
        outfit = style.getOutfit(season, vehicleCD=vehicleCD)
        if style.isProgressive:
            return getStyleProgressionOutfit(outfit, level, season).copy()
        return outfit.copy()

    def _isOutfitsModified(self):
        raise NotImplementedError
        # custom
        for season in SeasonType.COMMON_SEASONS:
            modifiedOutfit = self._modifiedOutfits[season]
            originalOutfit = self._originalOutfits[season]
            for _, component, _, _, _ in originalOutfit.diff(modifiedOutfit).itemsFull():
                if component.isFilled():
                    return True

            for _, component, _, _, _ in modifiedOutfit.diff(originalOutfit).itemsFull():
                if component.isFilled():
                    return True
        # styled
        isStyleChanged = any((not self._originalOutfits[season].isEqual(self._modifiedOutfits[season]) for season in
                              SeasonType.COMMON_SEASONS))
        if self.__modifiedStyle and self.__modifiedStyle.isProgressive:
            modifiedOutfit = self._modifiedOutfits[self.season]
            originalOutfit = self._originalOutfits[self.season]
            isInstalled = originalOutfit.id == modifiedOutfit.id and self._service.isStyleInstalled()
            modifiedProgression = modifiedOutfit.progressionLevel
            if g_currentVehicle and g_currentVehicle.item:
                originalProgression = self.__modifiedStyle.getLatestOpenedProgressionLevel(g_currentVehicle.item)
            else:
                originalProgression = originalOutfit.progressionLevel
            isProgressionReachable = self.__modifiedStyle.isProgressionPurchasable(modifiedProgression)
            isProgressionReachable = isProgressionReachable or modifiedProgression == originalProgression
            if (not isInstalled or modifiedProgression != originalProgression) and not isProgressionReachable:
                return False
            if not isInstalled:
                return True
        return isStyleChanged
        # modded custom
        vehCache = g_config.getOutfitCache()
        fromOutfits = self.__getBaseOutfits()
        self._cache.clear()
        for season in SeasonType.COMMON_SEASONS:
            seasonName = SEASON_TYPE_TO_NAME[season]
            original = self._originalOutfits[season]
            modified = self._modifiedOutfits[season]
            self._cache[seasonName] = self.computeDiff(original, modified)
            fromOutfit = fromOutfits[season]
            applyOutfitCache(fromOutfit, vehCache.get(seasonName, {}), False)
            self._originalOutfits[season] = fromOutfit.copy()
            applyOutfitCache(fromOutfit, self._cache[seasonName])
            self._modifiedOutfits[season] = fromOutfit.copy()
        self._fitOutfits()
        return any(self._cache.values())
        # modded styled
        vehicleCD = g_currentVehicle.item.descriptor.makeCompactDescr()
        style = self._baseMode.modifiedStyle
        if self.__modifiedStyle == self.__originalStyle and self._baseMode.originalStyle == self._moddedStyle:
            self.__modifiedStyle = style
            self.__originalStyle = style
        else:
            self.__originalStyle = self._moddedStyle or style
        season = self.season
        oldLevel = self._originalOutfits[season].progressionLevel
        newLevel = self._modifiedOutfits[season].progressionLevel
        for s in SeasonType.COMMON_SEASONS:
            self._originalOutfits[s] = self.safe_getOutfitFromStyle(
                vehicleCD, s, self.originalStyle, oldLevel, self._baseMode.originalStyle, self._baseMode.getOriginalOutfit(s))
            self._modifiedOutfits[s] = self.safe_getOutfitFromStyle(
                vehicleCD, s, self.modifiedStyle, newLevel, self._baseMode.modifiedStyle, self._baseMode.getModifiedOutfit(s))
        return bool(self.__originalStyle != self.__modifiedStyle or (
                self.__modifiedStyle and self.__modifiedStyle.isProgressive
                and self._originalOutfits[season].progressionLevel != self._modifiedOutfits[season].progressionLevel))
        # also
        return ItemSettingsRemap.isOutfitsModified(self)

    def __getItemProgressionLevel(self, item):
        return item.getLatestOpenedProgressionLevel(
            g_currentVehicle.item) if self._ctx.isPurchase else item.getMaxProgressionLevel()

    def __configureProjectionDecalComponentProgression(self, component, item, prevItem):
        if not item.isProgressive:
            component.progressionLevel = 0
            return
        achievedLevel = self.__getItemProgressionLevel(item)
        if achievedLevel == -1:
            component.progressionLevel = 0
            return
        if prevItem is not None and prevItem != item:
            if not prevItem.isProgressive:
                progressionLevel = 0
            else:
                prevLevel = component.progressionLevel
                prevLevel = prevLevel or self.__getItemProgressionLevel(prevItem)
                progressionLevel = min(prevLevel, achievedLevel)
        else:
            progressionLevel = min(self.__storedProgressionLevel, achievedLevel)
        if progressionLevel == 0:  # stored level is 0
            progressionLevel = 1
        component.progressionLevel = progressionLevel
