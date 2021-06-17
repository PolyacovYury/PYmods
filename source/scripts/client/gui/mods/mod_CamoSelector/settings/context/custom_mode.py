import operator
from CurrentVehicle import g_currentVehicle
from PYmodsCore import loadJson
from adisp import async
from copy import deepcopy
from gui import SystemMessages
from gui.Scaleform.daapi.view.lobby.customization.context.custom_mode import CustomMode as WGCustomMode
from gui.Scaleform.daapi.view.lobby.customization.shared import ITEM_TYPE_TO_SLOT_TYPE, getSlotDataFromSlot
from gui.Scaleform.locale.MESSENGER import MESSENGER
from gui.SystemMessages import SM_TYPE
from gui.customization.shared import SEASON_TYPE_TO_NAME, C11nId, __isTurretCustomizable as isTurretCustom
from gui.shared.gui_items import GUI_ITEM_TYPE_NAMES, GUI_ITEM_TYPE
from items.components.c11n_constants import SeasonType
from items.customizations import EmptyComponent, FieldFlags
from vehicle_outfit.outfit import Area
from ..shared import getItemSeason
from ... import g_config
from ...processors import applyOutfitCache, deleteEmpty


class CustomMode(WGCustomMode):
    def __init__(self, ctx, baseMode):
        WGCustomMode.__init__(self, ctx)
        self._baseMode = baseMode
        self._cache = deepcopy(g_config.getHangarCache())

    def installStyleItemsToModifiedOutfit(self, styleOutfits):
        self._modifiedOutfits = styleOutfits
        self._fitOutfits()

    def getItemInventoryCount(self, item, excludeBase=False):
        return 10  # should be enough to plaster any vehicle

    def _cancelChanges(self):
        self._cache.clear()
        WGCustomMode._cancelChanges(self)

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
        seasonCache = {}
        for container, slot, regionIdx, _, o_component in self.iterOutfit(original):
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
            elif not m.component.weak_eq(o_component):
                if isinstance(m.component, EmptyComponent):
                    item_data['id'] = self._service.getItemByCD(m.intCD).id
                else:
                    item_data.update({
                        f: getattr(m.component, f) for f, fd in m.component.fields.items()
                        if not fd.flags & (FieldFlags.DEPRECATED | FieldFlags.WEAK_EQUAL_IGNORED)})
        deleteEmpty(seasonCache)
        return seasonCache

    def _isOutfitsModified(self):
        vehCache = g_config.getOutfitCache()
        fromOutfits = self._baseMode.getModifiedOutfits()
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

    def _fillOutfits(self):
        vehCache = g_config.getOutfitCache()
        for season in SeasonType.COMMON_SEASONS:
            fromOutfit = self._service.getCustomOutfit(season) or self._service.getEmptyOutfit()
            seasonName = SEASON_TYPE_TO_NAME[season]
            applyOutfitCache(fromOutfit, vehCache.get(seasonName, {}), False)
            self._originalOutfits[season] = fromOutfit.copy()
            applyOutfitCache(fromOutfit, self._cache.get(seasonName, {}))
            self._modifiedOutfits[season] = fromOutfit.copy()
        self._fitOutfits()

    @async
    def _applyItems(self, purchaseItems, isModeChanged, callback):
        vDesc = g_currentVehicle.item.descriptor
        nation, vehName = vDesc.name.split(':')
        isTurretCustomisable = isTurretCustom(vDesc)
        fromOutfits = self._baseMode.getModifiedOutfits()
        if self.isOutfitsModified() or isModeChanged:
            SystemMessages.pushI18nMessage(
                MESSENGER.SERVICECHANNELMESSAGES_SYSMSG_CONVERTER_CUSTOMIZATIONS, type=SM_TYPE.Information)
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
            styleCache = g_config.getOutfitCache().get('style', {})
            styleCache.setdefault('intCD', None)
            styleCache['applied'] = False
            if styleCache != {'intCD': None, 'applied': False}:
                cache['style'] = styleCache
            g_config.outfitCache.setdefault(nation, {})[vehName] = cache
            deleteEmpty(cache, isTurretCustomisable)
            deleteEmpty(g_config.outfitCache)
            loadJson(g_config.ID, 'outfitCache', g_config.outfitCache, g_config.configPath, True)
        callback(self)

    def getPurchaseItems(self):
        return self._ctx.getPurchaseItems()

    def getModdedPurchaseItems(self):
        return WGCustomMode.getPurchaseItems(self)

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

    def isPossibleToInstallItemForAllSeasons(self, slotId, intCD):
        return getItemSeason(self._service.getItemByCD(intCD)) == reduce(
            operator.ior, SeasonType.COMMON_SEASONS, SeasonType.UNDEFINED)
