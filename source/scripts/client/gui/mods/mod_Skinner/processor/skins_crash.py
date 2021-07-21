import ResMgr
from items.components.shared_components import ModelStatesPaths
from vehicle_systems.tankStructure import TankPartNames
from .. import g_config


def apply(vDesc, modelsSet):
    parts = []
    present_crash_tex = {
        x: ResMgr.isFile('vehicles/skins/textures/white_crash/all/all/%s_crash.dds' % x) for x in ('track', 'tank')}
    if present_crash_tex['track']:
        parts.append(TankPartNames.CHASSIS)
    if present_crash_tex['tank']:
        parts += TankPartNames.ALL[1:]
    for partName in parts:
        part = getattr(vDesc, partName)
        models = part.modelsSets[modelsSet]
        path_destroyed = 'vehicles/skins/models/white_crash/' + models.destroyed
        if ResMgr.isFile(path_destroyed):
            part.modelsSets[modelsSet] = ModelStatesPaths(models.undamaged, path_destroyed, models.exploded)
            part.models = part.modelsSets['default']
        else:
            print g_config.ID + ': skin model not found:', path_destroyed
        models = part.modelsSets[modelsSet]
        path_exploded = 'vehicles/skins/models/white_crash/' + models.exploded
        if ResMgr.isFile(path_exploded):
            part.modelsSets[modelsSet] = ModelStatesPaths(models.undamaged, models.destroyed, path_exploded)
            part.models = part.modelsSets['default']
        else:
            print g_config.ID + ': skin model not found:', path_exploded
