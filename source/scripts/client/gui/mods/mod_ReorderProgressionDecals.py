from gui.impl.lobby.customization.progressive_items_view.progressive_items_view import ProgressiveItemsView
from items import vehicles

order = ('battles', 'frags', 'ranked', 'marksOfMastery', 'mainGun', 'BrothersInArms', )


def _getPossibleItemsForVehicle(self):
    customizationCache = vehicles.g_cache.customization20()
    vehicleType = self._vehicle.descriptor.type
    sortedItems = sorted(customizationCache.customizationWithProgression.itervalues(), key=lambda i: (
        next((j for j, tag in enumerate(order) if tag in i.progression.levels[1][0]['path'][1]), 100), i.id
    ))
    return [item.compactDescr for item in sortedItems if item.filter.matchVehicleType(vehicleType)]


ProgressiveItemsView._ProgressiveItemsView__getPossibleItemsForVehicle = _getPossibleItemsForVehicle
