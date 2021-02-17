from CurrentVehicle import g_currentVehicle
from PYmodsCore import loadJson
from adisp import async
from gui import SystemMessages
from gui.Scaleform.daapi.view.lobby.customization.context.styled_mode import StyledMode as WGStyledMode
from gui.Scaleform.locale.MESSENGER import MESSENGER
from gui.SystemMessages import SM_TYPE
from gui.customization.shared import __isTurretCustomizable as isTurretCustom
from items.components.c11n_constants import SeasonType
from ... import g_config
from ...processors import deleteEmpty


class StyledMode(WGStyledMode):
    def __init__(self, ctx, baseMode):
        super(StyledMode, self).__init__(ctx)
        self._baseMode = baseMode
        self._moddedStyle = None

    def prolongRent(self, style):
        self._baseMode.prolongRent(style)

    def getItemInventoryCount(self, item, excludeBase=False):
        return 10  # should be enough to plaster any vehicle

    def _removeHiddenFromOutfit(self, outfit, vehicleIntCD):
        pass

    def safe_getOutfitFromStyle(self, style, season, vehicleCD):
        if style is None:
            return self._service.getEmptyOutfit()
        return style.getOutfit(season, vehicleCD=vehicleCD).copy()

    def _isOutfitsModified(self):
        vehicleCD = g_currentVehicle.item.descriptor.makeCompactDescr()
        style = self._baseMode.modifiedStyle
        if self.__modifiedStyle == self.__originalStyle and self._baseMode.originalStyle == self._moddedStyle:
            self.__modifiedStyle = style
            self.__originalStyle = style
        else:
            self.__originalStyle = self._moddedStyle or style
        for season in SeasonType.COMMON_SEASONS:
            self._originalOutfits[season] = self.safe_getOutfitFromStyle(self.__originalStyle, season, vehicleCD)
            self._modifiedOutfits[season] = self.safe_getOutfitFromStyle(self.__modifiedStyle, season, vehicleCD)
        return super(StyledMode, self)._isOutfitsModified()

    def _fillOutfits(self):
        vehicleCD = g_currentVehicle.item.descriptor.makeCompactDescr()
        vehCache = g_config.getOutfitCache()
        styleCache = vehCache.get('style', {'intCD': None, 'applied': False})
        style = self._baseMode.originalStyle
        self._moddedStyle = None if styleCache['intCD'] is None else self._service.getItemByCD(styleCache['intCD'])
        if not styleCache['applied']:
            style = None
        elif self._moddedStyle:
            style = self._moddedStyle
        self.__originalStyle = style
        self.__modifiedStyle = style
        for season in SeasonType.COMMON_SEASONS:
            if style is None:
                outfit = self._service.getEmptyOutfit()
            elif self._moddedStyle is None:
                outfit = self._baseMode.getModifiedOutfit(season).copy()
            else:
                outfit = style.getOutfit(season, vehicleCD=vehicleCD).copy()
            self._originalOutfits[season] = outfit.copy()
            self._modifiedOutfits[season] = outfit.copy()

    @async
    def _applyItems(self, purchaseItems, isModeChanged, callback):
        vDesc = g_currentVehicle.item.descriptor
        nation, vehName = vDesc.name.split(':')
        isTurretCustomisable = isTurretCustom(vDesc)
        vehCache = g_config.outfitCache.setdefault(nation, {}).setdefault(vehName, {})
        if self.__originalStyle != self.__modifiedStyle or self._moddedStyle != self.__modifiedStyle or isModeChanged:
            vehCache.setdefault('style', {}).update(
                intCD=self.__modifiedStyle.intCD if self.__modifiedStyle else None, applied=True)
            if self.__modifiedStyle:
                g_config.getHangarCache().clear()
            SystemMessages.pushI18nMessage(
                MESSENGER.SERVICECHANNELMESSAGES_SYSMSG_CONVERTER_CUSTOMIZATIONS, type=SM_TYPE.Information)
        deleteEmpty(g_config.outfitCache, isTurretCustomisable)
        loadJson(g_config.ID, 'outfitCache', g_config.outfitCache, g_config.configPath, True)
        callback(self)

    def getPurchaseItems(self):
        return self._ctx.getPurchaseItems()

    def getModdedPurchaseItems(self):
        return super(StyledMode, self).getPurchaseItems()
