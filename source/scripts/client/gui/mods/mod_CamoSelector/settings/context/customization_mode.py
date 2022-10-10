from copy import deepcopy

from CurrentVehicle import g_currentVehicle
from OpenModsCore import BigWorld_callback, loadJson
from adisp import adisp_async
from constants import CLIENT_COMMAND_SOURCES
from gui import SystemMessages
from gui.Scaleform.daapi.view.lobby.customization.context.context import CustomizationContext
from gui.Scaleform.daapi.view.lobby.customization.context.custom_mode import CustomMode as WGCustomMode
from gui.Scaleform.daapi.view.lobby.customization.shared import (
    CustomizationSlotUpdateVO, CustomizationTabs, ITEM_TYPE_TO_SLOT_TYPE, customizationSlotIdToUid, getSlotDataFromSlot,
)
from gui.Scaleform.locale.MESSENGER import MESSENGER
from gui.customization.constants import CustomizationModes
from gui.customization.shared import (
    AdditionalPurchaseGroups, C11nId, PurchaseItem, SEASON_IDX_TO_TYPE, SEASON_TYPE_TO_NAME,
    __isTurretCustomizable as isTurretCustom,
)
from gui.shared.gui_items import GUI_ITEM_TYPE, GUI_ITEM_TYPE_NAMES
from helpers import dependency
from items.components.c11n_constants import EMPTY_ITEM_ID, SeasonType
from items.customizations import DecalComponent, EmptyComponent, FieldFlags
from skeletons.account_helpers.settings_core import ISettingsCore
from vehicle_outfit.containers import SlotData
from vehicle_outfit.outfit import Area
from .item_remap import ItemSettingsRemap
from ..shared import isSlotLocked, isStyleSeasoned
from ... import g_config
from ...constants import SEASON_NAME_TO_TYPE
from ...processors import (
    addDefaultInsignia, applyOutfitCache, applyStyleOverride, changeOutfitStyleData, createEmptyOutfit, deleteEmpty,
    getDefaultItemCDs, getOutfitFromStyle, getStyleFromId,
)


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
            BigWorld_callback(0, self.selectSlot, C11nId(Area.GUN, GUI_ITEM_TYPE.INSIGNIA, 0))

    def changeTab(self, tabId, itemCD=None):
        if self._tabId != tabId == 8:
            BigWorld_callback(0, self._selectInsignia)
        WGCustomMode.changeTab(self, tabId, itemCD)

    def _onStart(self):
        WGCustomMode._onStart(self)
        self._events.onSeasonChanged += self._selectInsignia
        self._events.onComponentChanged += self._onComponentChanged
        self._events.onItemsRemoved += self._onItemsRemoved
        self._events.onItemInstalled += self._onItemInstalled
        self._invalidateCache()

    def _onStop(self):
        self._events.onItemInstalled -= self._onItemInstalled
        self._events.onItemsRemoved -= self._onItemsRemoved
        self._events.onComponentChanged -= self._onComponentChanged
        self._events.onSeasonChanged -= self._selectInsignia
        WGCustomMode._onStop(self)

    # noinspection PyUnusedLocal
    def _onItemInstalled(self, item, slotId, season, component):
        self._invalidateCache(season)

    def _onItemsRemoved(self, *_, **__):
        self._invalidateCache()

    def _onComponentChanged(self, *_, **__):
        self._invalidateCache(self.season)

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
        baseOutfit = getOutfitFromStyle(style, styleSeason, progressionLevel)
        modifiedOutfit = addDefaultInsignia(modifiedOutfit)
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
        return (self.getCustomPurchaseItems(season) if self.__modifiedStyles[season] is None else self.getStylePurchaseItems(
            self.__modifiedStyles[season], self._modifiedOutfits[season], season, self.__modifiedStyleSeasons[season],
            self.getStyleProgressionLevel()))

    def getSlotDataFromSlot(self, slotId, season=None):
        season = season or self.season
        outfit = self._modifiedOutfits[season]
        if slotId.slotType != GUI_ITEM_TYPE.STYLE:
            return getSlotDataFromSlot(outfit, slotId)
        return SlotData() if not outfit.id else SlotData(
            self.__modifiedStyles[season].intCD, DecalComponent(
                outfit.id, self.__modifiedStyleSeasons[season], outfit.progressionLevel))

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

    def removeItemsFromSeason(self, season=None, filterMethod=None, refresh=True, revertToPrevious=False):
        season = season or self.season  # called from above and prop sheet to clean projection decals
        outfit = self._modifiedOutfits[season]
        originalOutfit = self._originalOutfits[season]
        for intCD, _, regionIdx, container, _ in outfit.itemsFull():
            item = self._service.getItemByCD(intCD)
            if filterMethod is None or filterMethod(item):
                areaId = container.getAreaID()
                slotType = ITEM_TYPE_TO_SLOT_TYPE[item.itemTypeID]
                slotId = C11nId(areaId, slotType, regionIdx)
                if revertToPrevious:
                    container = originalOutfit.getContainer(areaId)
                    slotData = container.slotFor(item.itemTypeID).getSlotData(regionIdx)
                    if slotData.intCD:
                        self.installItem(slotData.intCD, slotId, season, refresh=False)
                    else:
                        self.removeItem(slotId, season, refresh=False)
                else:
                    self.removeItem(slotId, season, refresh=False)
        if refresh:
            self._ctx.refreshOutfit(season)
            self._events.onItemsRemoved()

    def isOutfitsHasLockedItems(self):
        return False

    def getOutfitsLockedItemsCount(self):
        return 0

    def removeStyle(self, intCD):
        if self.modifiedStyle is not None and self.modifiedStyle.intCD == intCD:
            self.removeItem(self.STYLE_SLOT)

    def changeStyleProgressionLevel(self, toLevel):
        styleSeason = self.__modifiedStyleSeasons[self.season]
        outfit = self._modifiedOutfits[self.season]
        self._modifiedOutfits[self.season] = changeOutfitStyleData(
            outfit, self.modifiedStyle, styleSeason, (outfit.progressionLevel, toLevel))
        self._fitOutfits(modifiedOnly=True)
        self._ctx.refreshOutfit()
        self._events.onComponentChanged(self.STYLE_SLOT, True)

    def getStyleProgressionLevel(self):
        return self.currentOutfit.progressionLevel if self.modifiedStyle and self.modifiedStyle.isProgressive else -1

    def clearStyle(self):
        style = self.modifiedStyle
        if style is None:
            return
        outfit = self._modifiedOutfits[self.season]
        self._modifiedOutfits[self.season] = getOutfitFromStyle(self.modifiedStyle, self.season, outfit.progressionLevel)
        self.__modifiedStyleSeasons[self.season] = self.season
        self._fitOutfits(modifiedOnly=True)
        self._ctx.refreshOutfit()
        self._ctx.events.onItemsRemoved()

    def changeCamouflageColor(self, slotId, paletteIdx):
        if slotId.slotType != GUI_ITEM_TYPE.STYLE:
            return WGCustomMode.changeCamouflageColor(self, slotId, paletteIdx)
        style = self.__modifiedStyles[self.season]
        if not style or not isStyleSeasoned(style):
            return
        outfit = self._modifiedOutfits[self.season]
        styleSeason = self.__modifiedStyleSeasons[self.season]
        self.__modifiedStyleSeasons[self.season] = newSeason = SEASON_IDX_TO_TYPE[paletteIdx]
        self._modifiedOutfits[self.season] = changeOutfitStyleData(
            outfit, style, (styleSeason, newSeason), outfit.progressionLevel)
        self._fitOutfits(modifiedOnly=True)
        self._ctx.refreshOutfit()
        self._events.onComponentChanged(slotId, False)

    def _getBaseOutfits(self):
        return self._ctx.getMode().getModifiedOutfits() if g_config.data['useBought'] else {
            season: self._service.getEmptyOutfit() for season in SeasonType.COMMON_SEASONS}

    def _invalidateCache(self, season=None):
        vDesc = g_currentVehicle.item.descriptor
        vehCache = g_config.getOutfitCache()
        fromOutfits = self._getBaseOutfits()
        seasons = (season,) if season else SeasonType.COMMON_SEASONS
        for _season in seasons:
            seasonName = SEASON_TYPE_TO_NAME[_season]
            self._cache[seasonName] = self.computeCache(
                self._originalOutfits[_season], self._modifiedOutfits[_season],
                self.__originalStyleSeasons[_season], self.__modifiedStyleSeasons[_season])
            outfit = fromOutfits[_season].copy()
            outfit = applyOutfitCache(vDesc, outfit, seasonName, vehCache.get(seasonName, {}), False)
            self._originalOutfits[_season] = outfit
            self.__originalStyles[_season] = getStyleFromId(outfit.id) if outfit.id else None
            outfit = applyOutfitCache(vDesc, outfit, seasonName, self._cache[seasonName])
            self._modifiedOutfits[_season] = outfit
            self.__modifiedStyles[_season] = getStyleFromId(outfit.id) if outfit.id else None
        self._fitOutfits()

    def _fillOutfits(self):
        vehCache = g_config.getOutfitCache()
        baseOutfits = self._getBaseOutfits()
        vDesc = g_currentVehicle.item.descriptor
        for season in SeasonType.COMMON_SEASONS:
            seasonName = SEASON_TYPE_TO_NAME[season]
            seasonCache = vehCache.get(seasonName, {})
            outfit = applyOutfitCache(vDesc, baseOutfits[season], seasonName, seasonCache, False)
            self._originalOutfits[season] = outfit
            self.__originalStyles[season] = getStyleFromId(outfit.id) if outfit.id else None
            outfit = applyOutfitCache(vDesc, outfit, seasonName, self._cache.get(seasonName, {}))
            self._modifiedOutfits[season] = outfit
            self.__modifiedStyles[season] = getStyleFromId(outfit.id) if outfit.id else None
            self.__originalStyleSeasons[season] = self.__modifiedStyleSeasons[season] = SEASON_NAME_TO_TYPE[
                seasonCache.get('style', {}).get('season', seasonName)]

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

    def _installItem(self, intCD, slotId, season=None, component=None):
        item = self._service.getItemByCD(intCD)
        season = season or self.season
        outfit = self._modifiedOutfits[season]
        if item.itemTypeID != GUI_ITEM_TYPE.STYLE:
            if isSlotLocked(outfit, slotId):
                return False
            component = component or self._getComponent(item, slotId)
            multiSlot = outfit.getContainer(slotId.areaId).slotFor(slotId.slotType)
            multiSlot.set(item.intCD, idx=slotId.regionIdx, component=component)
            return True
        if self.__modifiedStyles[season] == item and component is None:
            return False
        old_style = self.__modifiedStyles[season]
        old_season = self.__modifiedStyleSeasons[season]
        self._modifiedOutfits[season] = changeOutfitStyleData(
            outfit, (old_style, item), (old_season, season), (
                outfit.progressionLevel, component.progressionLevel if component else 1))
        self.__modifiedStyles[season] = item
        self.__modifiedStyleSeasons[season] = season
        self._fitOutfits(modifiedOnly=True)
        return True

    def _removeItem(self, slotId, season=None):
        season = season or self.season
        if slotId == self.STYLE_SLOT:
            outfit = self._modifiedOutfits[season]
            style = self.__modifiedStyles[season]
            styleSeason = self.__modifiedStyleSeasons[season]
            self._modifiedOutfits[season] = changeOutfitStyleData(
                outfit, (style, None), (styleSeason, season), (outfit.progressionLevel, 1))
            self.__modifiedStyles[season] = None
            self.__modifiedStyleSeasons[season] = season
            self._fitOutfits(modifiedOnly=True)
        else:
            outfit = self._modifiedOutfits[season]
            multiSlot = outfit.getContainer(slotId.areaId).slotFor(slotId.slotType)
            multiSlot.remove(slotId.regionIdx)

    @adisp_async
    def _applyItems(self, purchaseItems, isModeChanged, callback):
        self.applySettings()
        vDesc = g_currentVehicle.item.descriptor
        nation, vehName = vDesc.name.split(':')
        isTurretCustomisable = isTurretCustom(vDesc)
        if not self.isOutfitsModified() and not isModeChanged:
            return callback(self)
        fromOutfits = self._getBaseOutfits()
        cache = {}
        for season in SeasonType.COMMON_SEASONS:
            seasonName = SEASON_TYPE_TO_NAME[season]
            fromOutfit = addDefaultInsignia(fromOutfits[season])
            toOutfit = addDefaultInsignia(self._modifiedOutfits[season])
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
            styleInfo = seasonCache.setdefault('style', {})
            styleInfo['id'] = modified.id
            styleInfo['season'] = SEASON_TYPE_TO_NAME[modified_season]
        if modified.style and modified.style.isProgression and original.progressionLevel != modified.progressionLevel:
            styleInfo = seasonCache.setdefault('style', {})
            styleInfo['id'] = modified.id
            styleInfo['progressionLevel'] = modified.progressionLevel
        original = applyStyleOverride(
            g_currentVehicle.item.descriptor, original, SEASON_TYPE_TO_NAME[original_season], seasonCache, False)
        modified = addDefaultInsignia(modified)
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
                item = self._service.getItemByCD(m.intCD)
                if isinstance(m.component, EmptyComponent):
                    item_data['id'] = item.id
                else:
                    item_data.update({
                        f: getattr(m.component, f) for f, fd in m.component.fields.items()
                        if (not fd.flags & (FieldFlags.DEPRECATED | FieldFlags.WEAK_EQUAL_IGNORED)
                            and getattr(m.component, f) != fd.default)})
                item_data['id'] = g_config.getItemKeys(item.id, item.descriptor)[1]
        deleteEmpty(seasonCache)
        return seasonCache

    def _isOutfitsEmpty(self):
        defCDs = getDefaultItemCDs()
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
            result = WGCustomMode._getAnchorVOs(self)
            if not self.currentOutfit.modelsSet:
                return result
            outfit = self._modifiedOutfits[self.season]
            self._modifiedOutfits[self.season] = createEmptyOutfit(g_currentVehicle.item.descriptor)
            try:
                return list({i['uid']: i for i in result + WGCustomMode._getAnchorVOs(self)}.values())
            finally:
                self._modifiedOutfits[self.season] = outfit
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
