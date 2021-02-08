from gui.Scaleform.daapi.view.lobby.customization.context.styled_mode import StyledMode as WGStyledMode


class StyledMode(WGStyledMode):
    def __init__(self, ctx, baseMode):
        super(StyledMode, self).__init__(ctx)
        self._baseMode = baseMode

    def prolongRent(self, style):
        self._baseMode.prolongRent(style)

    def getItemInventoryCount(self, item, excludeBase=False):
        return 10  # should be enough to plaster any vehicle
