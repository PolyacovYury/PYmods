import BigWorld
import os
from items.components.shared_components import ModelStatesPaths
from items.vehicles import CompositeVehicleDescriptor
from vehicle_systems.tankStructure import TankPartNames
from .. import g_config


def apply(vDesc, sname):
    for partName in TankPartNames.ALL:
        for descr in (vDesc,) if not isinstance(vDesc, CompositeVehicleDescriptor) else (
                vDesc._CompositeVehicleDescriptor__vehicleDescr, vDesc._CompositeVehicleDescriptor__siegeDescr):
            part = getattr(descr, partName)
            for setName in part.modelsSets:
                models = part.modelsSets[setName]
                path = models.undamaged.replace('vehicles/', 'vehicles/skins/models/%s/vehicles/' % sname)
                if os.path.isfile(BigWorld.curCV + '/' + path):
                    part.modelsSets[setName] = ModelStatesPaths(path, models.destroyed, models.exploded)
                else:
                    print g_config.ID + ': skin model not found:', path
            part.models = part.modelsSets['default']
