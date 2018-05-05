import BigWorld
import os
from items.components.shared_components import ModelStatesPaths
from items.vehicles import CompositeVehicleDescriptor
from vehicle_systems.tankStructure import TankPartNames


def apply(vDesc, sname):
    for partName in TankPartNames.ALL:
        for descr in (vDesc,) if not isinstance(vDesc, CompositeVehicleDescriptor) else (
                vDesc._CompositeVehicleDescriptor__vehicleDescr, vDesc._CompositeVehicleDescriptor__siegeDescr):
            modelPath = getattr(descr, partName).models.undamaged.replace(
                'vehicles/', 'vehicles/skins/models/%s/vehicles/' % sname)
            if os.path.isfile(BigWorld.curCV + '/' + modelPath):
                part = getattr(descr, partName)
                models = part.modelsSets['default']
                part.modelsSets['default'] = ModelStatesPaths(modelPath, models.destroyed, models.exploded)
            else:
                print 'RemodEnabler: skin model not found:', modelPath
