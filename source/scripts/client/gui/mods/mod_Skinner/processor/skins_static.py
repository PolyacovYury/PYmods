import BigWorld
import os
from items.components.shared_components import ModelStatesPaths
from items.vehicles import CompositeVehicleDescriptor
from vehicle_systems.tankStructure import TankPartNames
from .. import g_config


def apply(vDesc, sname, modelsSet):
    for partName in TankPartNames.ALL:
        for descr in (vDesc,) if not isinstance(vDesc, CompositeVehicleDescriptor) else (
                vDesc._CompositeVehicleDescriptor__vehicleDescr, vDesc._CompositeVehicleDescriptor__siegeDescr):
            part = getattr(descr, partName)
            # if modelsSet != 'default':
            #     if g_config.data['isDebug']:
            #         print g_config.ID + ': non-default modelsSet skipped:', modelsSet
            #     return
            models = part.modelsSets[modelsSet]
            path = models.undamaged.replace('vehicles/', 'vehicles/skins/models/%s/vehicles/' % sname)
            if os.path.isfile(BigWorld.curCV + '/' + path):
                part.modelsSets[modelsSet] = ModelStatesPaths(path, models.destroyed, models.exploded)
            else:
                print g_config.ID + ': skin model not found:', path
