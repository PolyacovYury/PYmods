from gui.Scaleform.daapi.view.battle.shared.indicators import _ExtendedMarkerVOBuilder


def new_getDamageLabel(self, markerData):
    label = old_getDamageLabel(self, markerData)
    if not markerData.hitData.isFriendlyFire():
        label += '\n%s%%' % round(100.0 * markerData.hitData.getDamage() / markerData.hitData.getPlayerVehicleMaxHP(), 1)
    return label


old_getDamageLabel = _ExtendedMarkerVOBuilder._getDamageLabel
_ExtendedMarkerVOBuilder._getDamageLabel = new_getDamageLabel
