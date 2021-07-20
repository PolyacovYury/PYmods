import ResMgr
from items.components.shared_components import ModelStatesPaths
from vehicle_systems.tankStructure import TankPartNames
from .. import g_config


def apply(vDesc, modelsSet, skinName):
    for partName in TankPartNames.ALL:
        part = getattr(vDesc, partName)
        models = part.modelsSets[modelsSet]
        path = 'vehicles/skins/models/' + skinName + '/' + models.undamaged
        if ResMgr.isFile(path):
            part.modelsSets[modelsSet] = ModelStatesPaths(path, models.destroyed, models.exploded)
            part.models = part.modelsSets['default']
        else:
            print g_config.ID + ': skin model not found:', path
