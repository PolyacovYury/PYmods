import ResMgr
from items.components.shared_components import ModelStatesPaths
from items.vehicles import CompositeVehicleDescriptor
from vehicle_systems.tankStructure import TankPartNames
from .. import g_config


def apply(vDesc, modelsSet, sname):
    for partName in TankPartNames.ALL:
        for descr in (vDesc,) if not isinstance(vDesc, CompositeVehicleDescriptor) else (
                vDesc._CompositeVehicleDescriptor__vehicleDescr, vDesc._CompositeVehicleDescriptor__siegeDescr):
            part = getattr(descr, partName)
            models = part.modelsSets[modelsSet]
            path = models.undamaged.replace('vehicles/', 'vehicles/skins/models/%s/vehicles/' % sname)
            if ResMgr.isFile(path):
                part.modelsSets[modelsSet] = ModelStatesPaths(path, models.destroyed, models.exploded)
            else:
                print g_config.ID + ': skin model not found:', path
