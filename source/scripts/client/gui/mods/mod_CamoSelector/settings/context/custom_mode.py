from gui.Scaleform.daapi.view.lobby.customization.context.custom_mode import CustomMode as WGCustomMode


class CustomMode(WGCustomMode):
    def __init__(self, ctx, baseMode):
        super(CustomMode, self).__init__(ctx)
        self._baseMode = baseMode

    def installStyleItemsToModifiedOutfit(self, season, styleOutfit):
        self._modifiedOutfits[season] = styleOutfit
        self._fitOutfits()
