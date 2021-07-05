from copy import deepcopy

import BigWorld
from CurrentVehicle import g_currentVehicle
from PYmodsCore import loadJson
from adisp import async
from constants import CLIENT_COMMAND_SOURCES
from gui import SystemMessages
from gui.Scaleform.daapi.view.lobby.customization.context.context import CustomizationContext
from gui.Scaleform.daapi.view.lobby.customization.context.custom_mode import CustomMode as WGCustomMode
from gui.Scaleform.daapi.view.lobby.customization.shared import (
    CustomizationSlotUpdateVO, CustomizationTabs, ITEM_TYPE_TO_SLOT_TYPE, customizationSlotIdToUid,
    fitOutfit, getCurrentVehicleAvailableRegionsMap, getEditableStyleOutfitDiffComponent, getSlotDataFromSlot,
)
from gui.Scaleform.locale.MESSENGER import MESSENGER
from gui.customization.constants import CustomizationModes
from gui.customization.shared import (
    AdditionalPurchaseGroups, C11nId, PurchaseItem, SEASON_TYPE_TO_NAME, __isTurretCustomizable as isTurretCustom,
)
from gui.shared.gui_items import GUI_ITEM_TYPE, GUI_ITEM_TYPE_NAMES
from helpers import dependency
from items.components.c11n_constants import EMPTY_ITEM_ID, SeasonType
from items.customizations import EmptyComponent, FieldFlags
from skeletons.account_helpers.settings_core import ISettingsCore
from vehicle_outfit.outfit import Area
from vehicle_systems.camouflages import getStyleProgressionOutfit
from .item_remap import ItemSettingsRemap
from ..shared import addDefaultInsignia, getDefaultItemCDs
from ... import g_config
from ...constants import SEASON_NAME_TO_TYPE
from ...processors import applyOutfitCache, applyStyleOverride, createEmptyOutfit, deleteEmpty, getStyleFromId


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
        ItemSettingsRemap.__init__(self)
        WGCustomMode.__init__(self, ctx)
        self.__originalStyles = {s: None for s in SeasonType.COMMON_SEASONS}
        self.__originalStyleSeasons = {s: s for s in SeasonType.COMMON_SEASONS}
        self.__modifiedStyles = {s: None for s in SeasonType.COMMON_SEASONS}
        self.__modifiedStyleSeasons = {s: s for s in SeasonType.COMMON_SEASONS}
        self.__preservedStyleSeasons = {s: s for s in SeasonType.COMMON_SEASONS}
        self._cache = deepcopy(g_config.getHangarCache())
        self.__preservedCache = {}

    @property
    def modifiedStyle(self):
        return self.__modifiedStyles[self.season]

    @property
    def modifiedStyleSeason(self):
        return self.__modifiedStyleSeasons[self.season]

    def getModifiedStyle(self, season):
        return self.__modifiedStyles[season]

    def getModifiedStyleSeason(self, season):
        return self.__modifiedStyleSeasons[season]

    def isAutoRentEnabled(self):
        return False

    def changeAutoRent(self, source=CLIENT_COMMAND_SOURCES.UNDEFINED):
        pass

    def getDependenciesData(self):
        return self.modifiedStyle.getDependenciesIntCDs() if self.modifiedStyle else {}

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
        self._invalidateCache()

    def _onStop(self):
        self._events.onSeasonChanged -= self._selectInsignia
        WGCustomMode._onStop(self)

    def getPurchaseItems(self):
        with self._ctx.overrideMode(self._ctx.purchaseModeId):
            return self._ctx.getMode().getPurchaseItems() if CustomizationContext.isOutfitsModified(self._ctx) else []

    def getCustomPurchaseItems(self, season):
        return [PurchaseItem(
            self._service.getItemByCD(intCD), price=None, areaID=container.getAreaID(),
            slotType=ITEM_TYPE_TO_SLOT_TYPE[self._service.getItemByCD(intCD).itemTypeID], regionIdx=idx, selected=True,
            group=season, component=component)
            for intCD, component, idx, container, _ in self._modifiedOutfits[season].itemsFull()
            if self._service.getItemByCD(intCD).itemTypeID in ITEM_TYPE_TO_SLOT_TYPE]

    def getStylePurchaseItems(self, style, modifiedOutfit, season, styleSeason, progressionLevel):
        purchaseItems = [PurchaseItem(
            style, None, areaID=None, slotType=None, regionIdx=None, selected=True, component=styleSeason,
            group=AdditionalPurchaseGroups.STYLES_GROUP_ID, locked=True, progressionLevel=progressionLevel)]
        vehicleCD = g_currentVehicle.item.descriptor.makeCompactDescr()
        if style.isProgressive:
            modifiedOutfit = self._service.removeAdditionalProgressionData(modifiedOutfit, style, vehicleCD, styleSeason)
        baseOutfit = style.getOutfit(styleSeason, vehicleCD)
        addDefaultInsignia(baseOutfit, modifiedOutfit)
        for intCD, component, regionIdx, container, _ in modifiedOutfit.itemsFull():
            item = self._service.getItemByCD(intCD)
            slotType = ITEM_TYPE_TO_SLOT_TYPE.get(item.itemTypeID)
            if slotType is None:
                continue
            slotId = C11nId(container.getAreaID(), slotType, regionIdx)
            purchaseItems.append(PurchaseItem(
                item, price=None, areaID=slotId.areaId, slotType=slotId.slotType, regionIdx=slotId.regionIdx, selected=True,
                group=season, component=component, isEdited=intCD != getSlotDataFromSlot(baseOutfit, slotId).intCD))
        return purchaseItems

    def getActualPurchaseItems(self, season):
        return (
            self.getCustomPurchaseItems(season) if self.__modifiedStyles[season] is None else self.getStylePurchaseItems(
                self.__modifiedStyles[season], self.getModifiedOutfit(season), season, self.__modifiedStyleSeasons[season],
                self.getStyleProgressionLevel()))

    def removeItems(self, onlyCurrent, *intCDs):  # only called from context menu, but still
        styles, others = [], []
        for intCD in intCDs:
            (styles if self._service.getItemByCD(intCD).itemTypeID == GUI_ITEM_TYPE.STYLE else others).append(intCD)
        for season in (self.season,) if onlyCurrent else SeasonType.COMMON_SEASONS:  # onlyCurrent is always true
            for intCD in styles:
                style = self.__modifiedStyles[season]
                if style and style.intCD == intCD:
                    self.removeItem(self.STYLE_SLOT, season, refresh=False)
                    break
            self.removeItemsFromSeason(season, lambda item: item.intCD in others, refresh=False)
            self._ctx.refreshOutfit(season)
        self._events.onItemsRemoved()

    def removeItemsFromSeason(self, season=None, filterMethod=None, refresh=True):
        season = season or self.season  # called from above and prop sheet to clean projection decals
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
        if self.modifiedStyle is not None and self.modifiedStyle.intCD == intCD:
            self.removeItem(self.STYLE_SLOT)

    def changeStyleProgressionLevel(self, toLevel):
        for seasonID in SeasonType.COMMON_SEASONS:
            self._modifiedOutfits[seasonID] = getStyleProgressionOutfit(self._modifiedOutfits[seasonID], toLevel, seasonID)
        self._fitOutfits(modifiedOnly=True)
        self._invalidateCache()
        self._ctx.refreshOutfit()
        self._events.onComponentChanged(self.STYLE_SLOT, True)

    def getStyleProgressionLevel(self):
        return self.currentOutfit.progressionLevel if self.modifiedStyle and self.modifiedStyle.isProgressive else -1

    def clearStyle(self):
        style = self.modifiedStyle
        if style is None:
            return
        self._modifiedOutfits[self.season] = style.getOutfit(
            self.season, vehicleCD=g_currentVehicle.item.descriptor.makeCompactDescr()).copy()
        self.__modifiedStyleSeasons[self.season] = self.season
        self._fitOutfits(modifiedOnly=True)
        self._invalidateCache()
        self._ctx.refreshOutfit()
        self._ctx.events.onItemsRemoved()

    def _invalidateCache(self):
        vDesc = g_currentVehicle.item.descriptor
        vehCache = g_config.getOutfitCache()
        fromOutfits = self._ctx.getMode().getModifiedOutfits()
        self._cache.clear()
        for season in SeasonType.COMMON_SEASONS:
            seasonName = SEASON_TYPE_TO_NAME[season]
            self._cache[seasonName] = self.computeCache(
                self._originalOutfits[season], self._modifiedOutfits[season],
                self.__originalStyleSeasons[season], self.__modifiedStyleSeasons[season])
            outfit = fromOutfits[season]
            addDefaultInsignia(outfit)
            outfit = applyOutfitCache(vDesc, outfit, seasonName, vehCache.get(seasonName, {}), False)
            self._originalOutfits[season] = outfit.copy()
            self.__originalStyles[season] = getStyleFromId(outfit.id) if outfit.id else None
            outfit = applyOutfitCache(vDesc, outfit, seasonName, self._cache[seasonName])
            addDefaultInsignia(outfit)
            self._modifiedOutfits[season] = outfit.copy()
            self.__modifiedStyles[season] = getStyleFromId(outfit.id) if outfit.id else None
        self._fitOutfits()

    def _fillOutfits(self):
        vehCache = g_config.getOutfitCache()
        baseOutfits = self._ctx.getMode().getModifiedOutfits()
        vDesc = g_currentVehicle.item.descriptor
        for season in SeasonType.COMMON_SEASONS:
            seasonName = SEASON_TYPE_TO_NAME[season]
            seasonCache = vehCache.get(seasonName, {})
            outfit = applyOutfitCache(vDesc, baseOutfits[season], seasonName, seasonCache, False)
            self._originalOutfits[season] = outfit.copy()
            self.__originalStyles[season] = getStyleFromId(outfit.id) if outfit.id else None
            outfit = applyOutfitCache(vDesc, outfit, seasonName, self._cache.get(seasonName, {}))
            self._modifiedOutfits[season] = outfit.copy()
            self.__modifiedStyles[season] = getStyleFromId(outfit.id) if outfit.id else None
            self.__originalStyleSeasons[season] = self.__modifiedStyleSeasons[season] = SEASON_NAME_TO_TYPE[
                seasonCache.get('style', {}).get('season', seasonName)]
        self._invalidateCache()

    def _preserveState(self):
        WGCustomMode._preserveState(self)
        self.__preservedCache = deepcopy(self._cache)
        self.__preservedStyleSeasons = self.__modifiedStyleSeasons.copy()

    def _restoreState(self):
        WGCustomMode._restoreState(self)
        self._cache = self.__preservedCache
        self.__modifiedStyleSeasons = self.__preservedStyleSeasons.copy()
        for season in SeasonType.COMMON_SEASONS:
            styleId = self._modifiedOutfits[season].id
            self.__modifiedStyles[season] = self._service.getItemByID(GUI_ITEM_TYPE.STYLE, styleId) if styleId else None
        self._invalidateCache()

    def installItem(self, intCD, slotId, season=None, component=None, refresh=True):
        result = WGCustomMode.installItem(self, intCD, slotId, season, component, refresh)
        self._invalidateCache()
        return result

    def _installItem(self, intCD, slotId, season=None, component=None):
        item = self._service.getItemByCD(intCD)
        if item.itemTypeID != GUI_ITEM_TYPE.STYLE:
            result = WGCustomMode._installItem(self, intCD, slotId, season, component)
            self._invalidateCache()
            return result
        season = season or self.season
        vDesc = g_currentVehicle.item.descriptor
        vehicleCD = vDesc.makeCompactDescr()
        outfit = self._modifiedOutfits[season]
        style_season = self.__modifiedStyleSeasons[season]
        style = self.__modifiedStyles[season]
        if style is None:
            baseOutfit = createEmptyOutfit(vDesc)
        else:
            baseOutfit = style.getOutfit(style_season, vehicleCD=vehicleCD)
            if style.isProgressive:
                addOutfit = style.getAdditionalOutfit(outfit.progressionLevel, style_season, vehicleCD)
                if addOutfit is not None:
                    baseOutfit = baseOutfit.patch(addOutfit)
        fitOutfit(baseOutfit, getCurrentVehicleAvailableRegionsMap())
        diffComp = getEditableStyleOutfitDiffComponent(outfit, baseOutfit)
        diffComp.styleId = item.id
        self.__modifiedStyles[season] = item
        self.__modifiedStyleSeasons[season] = season
        outfit = item.getOutfit(season, vehicleCD=vehicleCD, diff=diffComp.makeCompDescr())
        if item.isProgressive:
            outfit = getStyleProgressionOutfit(outfit, 1, season)
        self._modifiedOutfits[season] = outfit
        self._fitOutfits(modifiedOnly=True)
        self._invalidateCache()
        return True

    def _removeItem(self, slotId, season=None):
        season = season or self.season
        if slotId == self.STYLE_SLOT:
            vDesc = g_currentVehicle.item.descriptor
            vehicleCD = vDesc.makeCompactDescr()
            outfit = self._modifiedOutfits[season]
            style_season = self.__modifiedStyleSeasons[season]
            style = self.__modifiedStyles[season]
            if style is None:
                baseOutfit = createEmptyOutfit(vDesc)
            else:
                baseOutfit = style.getOutfit(style_season, vehicleCD=vehicleCD)
                if style.isProgressive:
                    addOutfit = style.getAdditionalOutfit(outfit.progressionLevel, style_season, vehicleCD)
                    if addOutfit is not None:
                        baseOutfit = baseOutfit.patch(addOutfit)
            fitOutfit(baseOutfit, getCurrentVehicleAvailableRegionsMap())
            diffComp = getEditableStyleOutfitDiffComponent(outfit, baseOutfit)
            diffComp.styleId = 0
            self._modifiedOutfits[season] = createEmptyOutfit(vDesc, diffComp)
            self.__modifiedStyles[season] = None
            self.__modifiedStyleSeasons[season] = season
            self._fitOutfits(modifiedOnly=True)
        else:
            outfit = self._modifiedOutfits[season]
            multiSlot = outfit.getContainer(slotId.areaId).slotFor(slotId.slotType)
            multiSlot.remove(slotId.regionIdx)
        self._invalidateCache()

    @async
    def _applyItems(self, purchaseItems, isModeChanged, callback):
        self.applySettings()
        vDesc = g_currentVehicle.item.descriptor
        nation, vehName = vDesc.name.split(':')
        isTurretCustomisable = isTurretCustom(vDesc)
        if not self.isOutfitsModified() and not isModeChanged:
            return callback(self)
        fromOutfits = self._ctx.getMode().getModifiedOutfits()
        cache = {}
        for season in SeasonType.COMMON_SEASONS:
            seasonName = SEASON_TYPE_TO_NAME[season]
            fromOutfit = fromOutfits[season]
            toOutfit = self.getModifiedOutfit(season)
            addDefaultInsignia(fromOutfit, toOutfit)
            cache[seasonName] = seasonCache = self.computeCache(
                fromOutfit, toOutfit,
                self.__originalStyleSeasons[season], self.__modifiedStyleSeasons[season])
            for typeName, typeCache in seasonCache.items():
                if typeName == 'style':
                    if typeCache['id'] != EMPTY_ITEM_ID:
                        g_config.getHangarCache().get(seasonName, {}).get(
                            GUI_ITEM_TYPE_NAMES[GUI_ITEM_TYPE.CAMOUFLAGE], {}).clear()
                if typeName == GUI_ITEM_TYPE_NAMES[GUI_ITEM_TYPE.CAMOUFLAGE]:
                    for area, areaCache in typeCache.items():
                        for reg in areaCache:
                            g_config.getHangarCache().get(seasonName, {}).get(typeName, {}).get(area, {}).pop(reg, None)
        deleteEmpty(g_config.getHangarCache(), isTurretCustomisable)
        deleteEmpty(g_config.hangarCamoCache)
        g_config.outfitCache.setdefault(nation, {})[vehName] = cache
        deleteEmpty(cache, isTurretCustomisable)
        deleteEmpty(g_config.outfitCache)
        loadJson(g_config.ID, 'outfitCache', g_config.outfitCache, g_config.configPath, True)
        SystemMessages.pushI18nMessage(
            MESSENGER.SERVICECHANNELMESSAGES_SYSMSG_CONVERTER_CUSTOMIZATIONS, type=SystemMessages.SM_TYPE.Information)
        self._events.onItemsBought({}, [], [])
        callback(self)

    def _cancelChanges(self):
        ItemSettingsRemap.cancelChanges(self)
        self.__modifiedStyles = self.__originalStyles.copy()
        self.__modifiedStyleSeasons = self.__originalStyleSeasons.copy()
        self._cache.clear()
        WGCustomMode._cancelChanges(self)
        self._invalidateCache()

    def _getAppliedItems(self, isOriginal=True):
        appliedItems = WGCustomMode._getAppliedItems(self, isOriginal)
        style = self.__originalStyles[self.season] if isOriginal else self.__modifiedStyles[self.season]
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

    def computeCache(self, original, modified, original_season, modified_season):
        seasonCache = {}
        if original.id and not modified.id:
            seasonCache['style'] = {'id': EMPTY_ITEM_ID}
        elif modified.id != original.id:
            seasonCache['style'] = {'id': modified.id}
        if original_season != modified_season:
            seasonCache['style']['id'] = modified.id
            seasonCache['style']['season'] = SEASON_TYPE_TO_NAME[modified_season]
        if modified.style and modified.style.isProgression and original.progressionLevel != modified.progressionLevel:
            seasonCache['style']['id'] = modified.id
            seasonCache['style']['level'] = modified.progressionLevel
        original = applyStyleOverride(
            g_currentVehicle.item.descriptor, original, SEASON_TYPE_TO_NAME[original_season], seasonCache, False)
        addDefaultInsignia(original, modified)
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

    def _isOutfitsEmpty(self):
        defCDs = getDefaultItemCDs(g_currentVehicle.item.descriptor)
        for season in SeasonType.COMMON_SEASONS:
            outfit = self._modifiedOutfits[season]
            for i in outfit.items():
                if i and i not in defCDs:
                    return False

        return not ItemSettingsRemap.isOutfitsModified(self)

    def _isOutfitsModified(self):
        return ItemSettingsRemap.isOutfitsModified(self) or any(self._cache.values())

    def _getAnchorVOs(self):
        if self.tabId != CustomizationTabs.STYLES:
            return WGCustomMode._getAnchorVOs(self)
        slotId = C11nId(self.STYLE_SLOT.areaId, self.STYLE_SLOT.slotType, self.STYLE_SLOT.regionIdx)
        uid = customizationSlotIdToUid(slotId)
        intCD = self.modifiedStyle.intCD if self.modifiedStyle is not None else 0
        return [CustomizationSlotUpdateVO(slotId=slotId._asdict(), itemIntCD=intCD, uid=uid)._asdict()]

    def __configureProjectionDecalComponentProgression(self, component, item, prevItem):
        maxLevel = item.getMaxProgressionLevel()
        component.progressionLevel = 0 if maxLevel == -1 else (
                (min(self.__storedProgressionLevel, maxLevel) if prevItem is None or prevItem == item else
                 0 if not prevItem.isProgressive else
                 min(component.progressionLevel or prevItem.getMaxProgressionLevel(), maxLevel)) or 1)
