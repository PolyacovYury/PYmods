from gui.Scaleform.daapi.view.lobby.customization.context.custom_mode import CustomMode as WGCustomMode
from items.components.c11n_constants import SeasonType


class CustomMode(WGCustomMode):
    def __init__(self, ctx, baseMode):
        super(CustomMode, self).__init__(ctx)
        self._baseMode = baseMode

    def installStyleItemsToModifiedOutfit(self, season, styleOutfit):
        self._modifiedOutfits[season] = styleOutfit
        self._fitOutfits()

    def _validateItem(self, item, slotId, season):
        return []

    def isPossibleToInstallToAllTankAreas(self, intCD, slotType):
        return True

    def isPossibleToInstallItemForAllSeasons(self, slotId, intCD):
        return self._service.getItemByCD(intCD).season == SeasonType.ALL
