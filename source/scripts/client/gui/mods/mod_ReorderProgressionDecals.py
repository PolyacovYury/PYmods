from gui.impl.lobby.customization.progressive_items_view.progressive_items_view import ProgressiveItemsView
from items import vehicles
from items.components.c11n_constants import CustomizationType

order = ('battles', 'frags', 'BonusBattles', 'marksOfMastery', 'mainGun', 'BrothersInArms', )


def _getPossibleItemsForVehicle(self):
    customizationCache = vehicles.g_cache.customization20()
    vehicleType = self._vehicle.descriptor.type
    items = [item for item in customizationCache.customizationWithProgression.itervalues()
             if item.itemType == CustomizationType.PROJECTION_DECAL]
    sortedItems = sorted(items, key=lambda i: (
        next((j for j, tag in enumerate(order) if tag in i.progression.levels[1]['conditions'][0]['path'][1]), 100),
        i.id
    ))
    return [item.compactDescr for item in sortedItems if item.filter.matchVehicleType(vehicleType)]


ProgressiveItemsView._getPossibleItemsForVehicle = _getPossibleItemsForVehicle
