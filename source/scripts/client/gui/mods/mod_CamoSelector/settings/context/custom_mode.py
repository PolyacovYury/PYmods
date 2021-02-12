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
from items.customizations import EmptyComponent
from vehicle_outfit.outfit import Area
from ... import g_config
from ...processors import applyOutfitCache, deleteEmpty


class CustomMode(WGCustomMode):
    def __init__(self, ctx, baseMode):
        super(CustomMode, self).__init__(ctx)
        self._baseMode = baseMode
        self._cache = deepcopy(g_config.getHangarCache())

    def installStyleItemsToModifiedOutfit(self, season, styleOutfit):
        self._modifiedOutfits[season] = styleOutfit
        self._fitOutfits()

    def getItemInventoryCount(self, item, excludeBase=False):
        return 10  # should be enough to plaster any vehicle

    def _cancelChanges(self):
        self._cache.clear()
        super(CustomMode, self)._cancelChanges()

    def iterOutfit(self, outfit):
        for container in outfit.containers():
            for slot in container.slots():
                for regionIdx in range(slot.capacity()):
                    slotData = slot.getSlotData(regionIdx)
                    if slotData and slotData.intCD:
                        yield slotData.intCD, slotData.component, regionIdx, container, slot
                    else:
                        yield None, None, regionIdx, container, slot

    def _isOutfitsModified(self):
        vehCache = g_config.getOutfitCache()
        fromOutfits = self._ctx.getOrigModifiedOutfits()
        self._cache.clear()
        for season in SeasonType.COMMON_SEASONS:
            seasonName = SEASON_TYPE_TO_NAME[season]
            original = self._originalOutfits[season]
            modified = self._modifiedOutfits[season]
            for intCD, component, regionIdx, container, slot in self.iterOutfit(original):
                item = self._service.getItemByCD(intCD) if intCD is not None else None
                slotType = ITEM_TYPE_TO_SLOT_TYPE.get(slot.getTypes()[0])
                typeName = GUI_ITEM_TYPE_NAMES[slotType]
                areaID = container.getAreaID()
                slotId = C11nId(areaID, slotType, regionIdx)
                reg = str(regionIdx)
                m = getSlotDataFromSlot(modified, slotId)
                area = Area.getName(areaID) if areaID != Area.MISC else 'misc'
                if component if not m.intCD else not m.component.weak_eq(component):
                    self._cache.setdefault(seasonName, {}).setdefault(typeName, {}).setdefault(area, {})[reg] = (
                        ({f: getattr(m.component, f) for f, fd in m.component.fields.items() if not fd.weakEqualIgnored}
                         if not isinstance(m.component, EmptyComponent) else {'id': item.id})
                        if m.intCD else {'id': None})
            fromOutfit = fromOutfits[season]
            applyOutfitCache(fromOutfit, vehCache.get(seasonName, {}), False)
            self._originalOutfits[season] = fromOutfit.copy()
            applyOutfitCache(fromOutfit, self._cache.get(seasonName, {}))
            self._modifiedOutfits[season] = fromOutfit.copy()
        self._fitOutfits()
        return bool(self._cache)

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
        if self.isOutfitsModified():
            SystemMessages.pushI18nMessage(
                MESSENGER.SERVICECHANNELMESSAGES_SYSMSG_CONVERTER_CUSTOMIZATIONS, type=SM_TYPE.Information)
            for seasonName, seasonCache in self._cache.items():
                for typeName, typeCache in seasonCache.items():
                    if typeName != GUI_ITEM_TYPE_NAMES[GUI_ITEM_TYPE.CAMOUFLAGE]:
                        continue
                    for area, areaCache in typeCache.items():
                        for reg in areaCache:
                            g_config.getHangarCache().get(seasonName, {}).get(typeName, {}).get(area, {}).pop(reg, None)
            deleteEmpty(g_config.getHangarCache(), isTurretCustomisable)
            styleCache = g_config.outfitCache.get(nation, {}).get(vehName, {}).get('style', {})
            styleCache.setdefault('intCD', None)
            styleCache['applied'] = False
            if styleCache != {'intCD': None, 'applied': False}:
                self._cache['style'] = styleCache
            g_config.outfitCache.setdefault(nation, {})[vehName] = self._cache
            deleteEmpty(g_config.outfitCache, isTurretCustomisable)
            loadJson(g_config.ID, 'outfitCache', g_config.outfitCache, g_config.configPath, True)
        callback(self)

    def getPurchaseItems(self):
        return self._ctx.getPurchaseItems()

    def getModdedPurchaseItems(self):
        return super(CustomMode, self).getPurchaseItems()
