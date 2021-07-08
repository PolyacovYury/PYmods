from adisp import process
from gui.Scaleform.daapi.view.lobby.tank_setup import OptDeviceItemContextMenu
from gui.impl.backport import text
from gui.impl.gen import R
from gui.shared.gui_items.items_actions import factory as ActionsFactory
from gui.shared.utils.requesters import REQ_CRITERIA


def new_generateOptions(self, ctx, *a, **k):
    # noinspection PyArgumentList
    result = old_generateOptions(self, ctx, *a, **k)
    if not self._isDisabled:
        return result
    item = self._getItem()
    inventoryVehicles = self._itemsCache.items.getVehicles(REQ_CRITERIA.INVENTORY).itervalues()
    vehicles = {x: x.shortUserName for x in item.getInstalledVehicles(inventoryVehicles)}
    if self._getVehicle().intCD in vehicles:
        return result
    groupLabel = text(R.strings.vehicle_customization.propertySheet.actionBtn.clear())
    if len(vehicles) == 1:
        vehicle, vehName = vehicles.popitem()
        return result + [self._makeSeparator(), self._makeItem(
            'removeFromOther_%s_%s' % (vehicle.intCD, vehicle.optDevices.installed.index(item)), groupLabel + ' ' + vehName)]
    return result + [self._makeSeparator(), self._makeItem('removeFromOther', groupLabel, optSubMenu=[
        self._makeItem('removeFromOther_%s_%s' % (vehicle.intCD, vehicle.optDevices.installed.index(item)), vehName)
        for vehicle, vehName in sorted(vehicles, key=lambda x: x[1])
    ])]


@process
def new_onOptionSelect(self, optionId, *a, **k):
    if not optionId.startswith('removeFromOther'):
        # noinspection PyArgumentList
        old_onOptionSelect(self, optionId, *a, **k)
    vehicleCD, slotID = map(int, optionId.split('_')[1:])
    yield ActionsFactory.asyncDoAction(ActionsFactory.getAction(
        ActionsFactory.REMOVE_OPT_DEVICE, self._itemsCache.items.getItemByCD(vehicleCD), self._getItem(), slotID, False))


old_generateOptions = OptDeviceItemContextMenu._generateOptions
OptDeviceItemContextMenu._generateOptions = new_generateOptions
old_onOptionSelect = OptDeviceItemContextMenu.onOptionSelect
OptDeviceItemContextMenu.onOptionSelect = new_onOptionSelect
print 'DemountOptionalDevice v.1.0.0 by Polyacov_Yury: initialised.'
