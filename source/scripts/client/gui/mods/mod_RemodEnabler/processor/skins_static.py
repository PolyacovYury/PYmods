import os

import BigWorld
from items.components import shared_components
from vehicle_systems.tankStructure import TankPartNames
from .. import g_config


def apply(vDesc):
    OSDesc = g_config.OSDesc['static']
    if OSDesc is not None:
        sname = OSDesc.name
        for partName in TankPartNames.ALL:
            modelPath = getattr(vDesc, partName).models.undamaged.replace(
                'vehicles/', 'vehicles/skins/models/%s/vehicles/' % sname)
            if os.path.isfile(BigWorld.curCV + '/' + modelPath):
                part = getattr(vDesc, partName)
                models = part.models
                part.models = shared_components.ModelStatesPaths(modelPath, models.destroyed, models.exploded)
            else:
                print 'RemodEnabler: skin model not found:', modelPath
