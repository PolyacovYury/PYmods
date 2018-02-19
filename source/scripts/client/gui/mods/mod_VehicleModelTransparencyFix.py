from vehicle_systems.components.highlighter import Highlighter


def new_doHighlight(self, status, args):
    if self._Highlighter__isPlayersVehicle:
        status &= ~self.HIGHLIGHT_SIMPLE & ~self.HIGHLIGHT_ON
    old_doHighlight(self, status, args)


old_doHighlight = Highlighter._Highlighter__doHighlightOperation
Highlighter._Highlighter__doHighlightOperation = new_doHighlight
print 'VehicleModelTransparencyFix v.1.0.0 by Polyacov_Yury: initialised.'
