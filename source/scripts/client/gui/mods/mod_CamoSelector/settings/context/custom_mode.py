from gui.Scaleform.daapi.view.lobby.customization.context.custom_mode import CustomMode as WGCustomMode
from gui.customization.shared import SEASON_TYPE_TO_NAME
from items.components.c11n_constants import SeasonType
from ... import g_config
from ...processors import applyOutfitCache


class CustomMode(WGCustomMode):
    def __init__(self, ctx, baseMode):
        super(CustomMode, self).__init__(ctx)
        self._baseMode = baseMode

    def installStyleItemsToModifiedOutfit(self, season, styleOutfit):
        self._modifiedOutfits[season] = styleOutfit
        self._fitOutfits()

    def getItemInventoryCount(self, item, excludeBase=False):
        return 10  # should be enough to plaster any vehicle

    def _fillOutfits(self):
        super(CustomMode, self)._fillOutfits()
        vehCache = g_config.getOutfitCache()
        tempCache = g_config.getHangarCache()
        for season in SeasonType.COMMON_SEASONS:
            fromOutfit = self._service.getCustomOutfit(season) or self._service.getEmptyOutfit()
            seasonName = SEASON_TYPE_TO_NAME[season]
            applyOutfitCache(fromOutfit, vehCache.get(seasonName, {}), False)
            self._originalOutfits[season] = fromOutfit.copy()
            applyOutfitCache(fromOutfit, tempCache.get(seasonName, {}))
            self._modifiedOutfits[season] = fromOutfit.copy()
            self._fitOutfits()

    def getPurchaseItems(self):
        return self._ctx.getPurchaseItems()

    def getModdedPurchaseItems(self):
        return super(CustomMode, self).getPurchaseItems()
