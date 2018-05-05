import BigWorld
import os
from items.components.shared_components import ModelStatesPaths
from items.vehicles import CompositeVehicleDescriptor
from vehicle_systems.tankStructure import TankPartNames


def apply(vDesc, sname):
    for partName in TankPartNames.ALL:
        for descr in (vDesc,) if not isinstance(vDesc, CompositeVehicleDescriptor) else (
                vDesc._CompositeVehicleDescriptor__vehicleDescr, vDesc._CompositeVehicleDescriptor__siegeDescr):
            part = getattr(descr, partName)
            path = part.modelsSets['default'].undamaged.replace('vehicles/', 'vehicles/skins/models/%s/vehicles/' % sname)
            if os.path.isfile(BigWorld.curCV + '/' + path):
                models = part.modelsSets['default']
                part.models = part.modelsSets['default'] = ModelStatesPaths(path, models.destroyed, models.exploded)
            else:
                print 'RemodEnabler: skin model not found:', path
