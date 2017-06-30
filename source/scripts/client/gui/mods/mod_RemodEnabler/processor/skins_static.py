import os

import BigWorld
from vehicle_systems.tankStructure import TankPartNames
from .. import g_config


def apply(vDesc):
    OSDesc = g_config.OSDesc['static']
    if OSDesc is not None:
        sname = OSDesc.name
        for part in TankPartNames.ALL:
            modelPath = getattr(vDesc, part)['models']['undamaged'].replace(
                'vehicles/', 'vehicles/skins/models/%s/vehicles/' % sname)
            if os.path.isfile(BigWorld.curCV + '/' + modelPath):
                getattr(vDesc, part)['models']['undamaged'] = modelPath
            else:
                print 'RemodEnabler: skin model not found:', modelPath
