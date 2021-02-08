from gui.Scaleform.daapi.view.lobby.customization.context.custom_mode import CustomMode as WGCustomMode
from items.components.c11n_constants import SeasonType


class CustomMode(WGCustomMode):
    def __init__(self, ctx, baseMode):
        super(CustomMode, self).__init__(ctx)
        self._baseMode = baseMode

    def installStyleItemsToModifiedOutfit(self, season, styleOutfit):
        self._modifiedOutfits[season] = styleOutfit
        self._fitOutfits()

    def getItemInventoryCount(self, item, excludeBase=False):
        return 10  # should be enough to plaster any vehicle
