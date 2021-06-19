from CurrentVehicle import g_currentVehicle
from PYmodsCore import loadJson
from adisp import async
from constants import CLIENT_COMMAND_SOURCES
from gui import SystemMessages
from gui.Scaleform.daapi.view.lobby.customization.context.styled_mode import StyledMode as WGStyledMode
from gui.Scaleform.locale.MESSENGER import MESSENGER
from gui.SystemMessages import SM_TYPE
from gui.customization.shared import __isTurretCustomizable as isTurretCustom
from items.components.c11n_constants import SeasonType
from vehicle_systems.camouflages import getStyleProgressionOutfit
from ... import g_config
from ...processors import deleteEmpty


class StyledMode(WGStyledMode):
    def __init__(self, ctx, baseMode):
        WGStyledMode.__init__(self, ctx)
        self._baseMode = baseMode
        self._moddedStyle = None

    def changeAutoRent(self, source=CLIENT_COMMAND_SOURCES.UNDEFINED):
        self._baseMode.changeAutoRent(source)

    def prolongRent(self, style):
        self._baseMode.prolongRent(style)

    def getItemInventoryCount(self, item, excludeBase=False):
        return 10  # should be enough to plaster any vehicle

    def _removeHiddenFromOutfit(self, outfit, vehicleIntCD):
        pass

    def _validateItem(self, item, slotId, season):
        return []

    def safe_getOutfitFromStyle(self, vehicleCD, season, style, level, baseStyle, baseOutfit):
        if style is None:
            return self._service.getEmptyOutfit()
        if style == baseStyle:
            if style.isProgressive and level != baseOutfit.progressionLevel:
                return getStyleProgressionOutfit(baseOutfit, level, season)
            return baseOutfit.copy()
        outfit = style.getOutfit(season, vehicleCD=vehicleCD)
        if style.isProgressive:
            return getStyleProgressionOutfit(outfit, level, season).copy()
        return outfit.copy()

    def _isOutfitsModified(self):
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
        return self.__originalStyle != self.__modifiedStyle or (
                self.__modifiedStyle and self.__modifiedStyle.isProgressive
                and self._originalOutfits[season].progressionLevel != self._modifiedOutfits[season].progressionLevel)

    def _fillOutfits(self):
        vehicleCD = g_currentVehicle.item.descriptor.makeCompactDescr()
        vehCache = g_config.getOutfitCache()
        styleCache = vehCache.get('style', {'intCD': None, 'applied': False})
        style = self._baseMode.originalStyle
        self._moddedStyle = None if styleCache['intCD'] is None else self._service.getItemByCD(styleCache['intCD'])
        if self._moddedStyle:
            style = self._moddedStyle
        self.__originalStyle = style
        self.__modifiedStyle = style
        for season in SeasonType.COMMON_SEASONS:
            if style is None:
                outfit = self._service.getEmptyOutfit()
            elif self._moddedStyle is None or style == self._baseMode.originalStyle:
                outfit = self._baseMode.getModifiedOutfit(season).copy()
            else:
                outfit = style.getOutfit(season, vehicleCD=vehicleCD).copy()
            if outfit.style and outfit.style.isProgression:
                progressionLevel = styleCache.get('level', 1)
                outfit = getStyleProgressionOutfit(outfit, progressionLevel, season)
            self._originalOutfits[season] = outfit.copy()
            self._modifiedOutfits[season] = outfit.copy()

    @async
    def _applyItems(self, purchaseItems, isModeChanged, callback):
        vDesc = g_currentVehicle.item.descriptor
        nation, vehName = vDesc.name.split(':')
        isTurretCustomisable = isTurretCustom(vDesc)
        vehCache = g_config.outfitCache.setdefault(nation, {}).setdefault(vehName, {})
        if self.__originalStyle != self.__modifiedStyle or self._moddedStyle != self.__modifiedStyle or (
                self.__modifiedStyle and self.__modifiedStyle.isProgressive
                and self._originalOutfits[self.season].progressionLevel != self._modifiedOutfits[self.season].progressionLevel
        ) or isModeChanged:
            vehCache.setdefault('style', {}).update(
                intCD=self.__modifiedStyle.intCD if self.__modifiedStyle else None, applied=True)
            if self.__modifiedStyle:
                g_config.getHangarCache().clear()
                deleteEmpty(g_config.hangarCamoCache)
                progressionLevel = self.getStyleProgressionLevel()
                if progressionLevel != -1:
                    vehCache['style']['level'] = progressionLevel
            else:
                vehCache['style'].pop('level', None)
            SystemMessages.pushI18nMessage(
                MESSENGER.SERVICECHANNELMESSAGES_SYSMSG_CONVERTER_CUSTOMIZATIONS, type=SM_TYPE.Information)
            self._events.onItemsBought({}, [], [])
        deleteEmpty(vehCache, isTurretCustomisable)
        deleteEmpty(g_config.outfitCache)
        loadJson(g_config.ID, 'outfitCache', g_config.outfitCache, g_config.configPath, True)
        callback(self)

    def getPurchaseItems(self):
        return self._ctx.getPurchaseItems()

    def getModdedPurchaseItems(self):
        return WGStyledMode.getPurchaseItems(self)
