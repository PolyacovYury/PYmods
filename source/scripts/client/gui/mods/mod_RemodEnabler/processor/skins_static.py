import BigWorld
import os
from items.components import shared_components
from items.vehicles import CompositeVehicleDescriptor
from vehicle_systems.tankStructure import TankPartNames
from .. import g_config


def apply(vDesc):
    OSDesc = g_config.OSDesc['static']
    if OSDesc is not None:
        sname = OSDesc.name
        for partName in TankPartNames.ALL[1:]:
            for descr in (vDesc,) if not isinstance(vDesc, CompositeVehicleDescriptor) else (
                    vDesc._CompositeVehicleDescriptor__vehicleDescr, vDesc._CompositeVehicleDescriptor__siegeDescr):
                modelPath = getattr(descr, partName).models.undamaged.replace(
                    'vehicles/', 'vehicles/skins/models/%s/vehicles/' % sname)
                if os.path.isfile(BigWorld.curCV + '/' + modelPath):
                    part = getattr(descr, partName)
                    models = part.models
                    part.models = shared_components.ModelStatesPaths(modelPath, models.destroyed, models.exploded)
                else:
                    print 'RemodEnabler: skin model not found:', modelPath
