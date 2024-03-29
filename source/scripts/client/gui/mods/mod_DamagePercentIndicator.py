from gui.Scaleform.daapi.view.battle.shared.indicators import _ExtendedMarkerVOBuilder


def new_getDamageLabel(self, markerData):
    label = old_getDamageLabel(self, markerData)
    data = markerData.hitData
    if not data.isFriendlyFire() and not data.isBlocked():
        label += '\n%s%%' % round(100.0 * data.getDamage() / data.getPlayerVehicleMaxHP(), 1)
    return label


old_getDamageLabel = _ExtendedMarkerVOBuilder._getDamageLabel
_ExtendedMarkerVOBuilder._getDamageLabel = new_getDamageLabel
print 'DamagePercentIndicator v.1.0.0 by Polyacov_Yury: initialised.'
