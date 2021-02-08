from CurrentVehicle import g_currentVehicle
from gui.Scaleform.daapi.view.lobby.customization.context.styled_mode import StyledMode as WGStyledMode
from items.components.c11n_constants import SeasonType
from ... import g_config


class StyledMode(WGStyledMode):
    def __init__(self, ctx, baseMode):
        super(StyledMode, self).__init__(ctx)
        self._baseMode = baseMode

    def prolongRent(self, style):
        self._baseMode.prolongRent(style)

    def getItemInventoryCount(self, item, excludeBase=False):
        return 10  # should be enough to plaster any vehicle

    def _removeHiddenFromOutfit(self, outfit, vehicleIntCD):
        pass

    def _fillOutfits(self):
        vehicleCD = g_currentVehicle.item.descriptor.makeCompactDescr()
        vehCache = g_config.getOutfitCache()
        styleCache = vehCache.get('style', {'intCD': None, 'applied': False})
        style = self._baseMode.originalStyle
        moddedStyle = None if styleCache['intCD'] is None else self._service.getItemByCD(styleCache['intCD'])
        if not styleCache['applied']:
            style = None
        elif moddedStyle:
            style = moddedStyle
        self.__originalStyle = style
        self.__modifiedStyle = style
        for season in SeasonType.COMMON_SEASONS:
            if style is None:
                outfit = self._service.getEmptyOutfit()
            elif moddedStyle is None:
                outfit = self._baseMode.getOriginalOutfit(season).copy()
            else:
                outfit = style.getOutfit(season, vehicleCD=vehicleCD)
            self._originalOutfits[season] = outfit.copy()
            self._modifiedOutfits[season] = outfit.copy()

    def getPurchaseItems(self):
        return self._baseMode.getPurchaseItems()

    def getModdedPurchaseItems(self):
        return super(StyledMode, self).getPurchaseItems()
