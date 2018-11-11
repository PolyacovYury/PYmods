import Math
import copy
from collections import OrderedDict
from items.components.chassis_components import Wheel, WheelGroup, TrackNode, TrackMaterials, GroundNode, GroundNodeGroup, \
    Traces, SplineConfig, WheelsConfig, TrackParams
from items.components.shared_components import Camouflage, ModelStatesPaths, NodesAndGroups
from items.vehicles import g_cache
from vehicle_systems.tankStructure import TankPartNames

chassis_params = ('traces', 'tracks', 'wheels', 'groundNodes', 'trackNodes', 'splineDesc', 'trackParams')


def _asdict(obj):
    if isinstance(obj, SplineConfig):
        return OrderedDict((attrName.strip('_'), getattr(obj, attrName.strip('_'))) for attrName in obj.__slots__)
    else:
        return OrderedDict(zip(obj._fields, obj))


def migrate_chassis_config(config):  # please send data['chassis'] here
    new_config = OrderedDict()
    for key in config:
        if key not in chassis_params or not isinstance(config[key], basestring):
            if 'wwsound' not in key:  # sounds are obsolete
                new_config[key] = config[key]
            if key == 'AODecals' and config[key] and isinstance(config[key][0], dict):
                new_config[key] = [[row for row in decal['transform'].values()] for decal in config[key]]
            continue  # config already converted
        obj = eval(config[key])
        if isinstance(obj, dict):  # ancient config
            if key == 'traces':
                obj = Traces(**obj)
            elif key == 'tracks':
                obj = TrackMaterials(**obj)
            elif key == 'wheels':
                obj = WheelsConfig(
                    lodDist=obj['lodDist'],
                    groups=[d if hasattr(d, '_fields') else WheelGroup(*d) for d in obj['groups']],
                    wheels=[d if hasattr(d, '_fields') else Wheel(d[0], d[2], d[1], d[3], d[4]) for d in obj['wheels']])
            elif key == 'groundNodes':
                obj = NodesAndGroups(
                    nodes=[d if hasattr(d, '_fields') else GroundNode(d[1], d[0], d[2], d[3]) for d in obj['nodes']],
                    groups=[d if hasattr(d, '_fields') else GroundNodeGroup(d[0], d[4], d[5], d[1], d[2], d[3])
                            for d in obj['groups']])
            elif key == 'trackNodes':
                obj = NodesAndGroups(nodes=[
                    d if hasattr(d, '_fields') else TrackNode(d[0], d[1], d[2], d[5], d[6], d[4], d[3], d[7], d[8])
                    for d in obj['nodes']], groups=[])
            elif key == 'splineDesc':
                obj = SplineConfig(**obj)
            elif key == 'trackParams':
                obj = TrackParams(**obj)
        if not isinstance(obj, dict):  # we assume that we have a namedtuple, if we don't - something malicious, so crash
            if key == 'traces':
                obj = obj._replace(size=list(obj.size))
            obj = _asdict(obj)
            keys = ()
            if key == 'wheels':
                keys = ('groups', 'wheels')
            elif key in ('groundNodes', 'trackNodes'):
                keys = ('nodes', 'groups')
            for sub in keys:
                obj[sub] = list(obj[sub])
                for idx, value in enumerate(obj[sub]):
                    obj[sub][idx] = _asdict(value)
        new_config[key] = obj
    return new_config


def apply(vDesc, modelDesc):
    for key in chassis_params:
        obj = modelDesc['chassis'][key]
        if key == 'traces':
            obj = Traces(**obj)
        elif key == 'tracks':
            obj = TrackMaterials(**obj)
        elif key == 'wheels':
            obj = WheelsConfig(lodDist=obj['lodDist'], groups=tuple(WheelGroup(**d) for d in obj['groups']),
                               wheels=tuple(Wheel(**d) for d in obj['wheels']))
        elif key == 'groundNodes':
            obj = NodesAndGroups(nodes=tuple(GroundNode(**d) for d in obj['nodes']),
                                 groups=tuple(GroundNodeGroup(**d) for d in obj['groups']))
        elif key == 'trackNodes':
            obj = NodesAndGroups(nodes=tuple(TrackNode(**d) for d in obj['nodes']), groups=())
        elif key == 'splineDesc':
            obj = SplineConfig(**obj)
        elif key == 'trackParams':
            obj = TrackParams(**obj)
        setattr(vDesc.chassis, key, obj)
    if modelDesc['chassis']['AODecals']:
        AODecalsOffset = vDesc.chassis.hullPosition - Math.Vector3(*modelDesc['chassis']['hullPosition'])
        vDesc.chassis.AODecals = copy.deepcopy(modelDesc['chassis']['AODecals'])
        vDesc.chassis.AODecals[0].setElement(3, 1, AODecalsOffset.y)
    exclMask = modelDesc['common']['camouflage']['exclusionMask']
    vDesc.type.camouflage = Camouflage(
        modelDesc['common']['camouflage']['tiling'] if exclMask else vDesc.type.camouflage.tiling, exclMask)
    for partName in TankPartNames.ALL:
        part = getattr(vDesc, partName)
        models = part.modelsSets['default']
        part.modelsSets['default'] = ModelStatesPaths(modelDesc[partName]['undamaged'], models.destroyed, models.exploded)
        part.models = part.modelsSets['default']
        if partName == 'chassis':
            continue
        part.emblemSlots = tuple(modelDesc[partName]['emblemSlots'])
        camoData = modelDesc[partName]['camouflage']
        exclMask = camoData['exclusionMask']
        if exclMask:
            part.camouflage = Camouflage(camoData['tiling'], exclMask)
    exhaust = modelDesc['hull']['exhaust']
    for effectDesc in vDesc.hull.customEffects:
        if exhaust['nodes']:
            effectDesc.nodes[:] = exhaust['nodes']
        effectDesc._selectorDesc = g_cache._customEffects['exhaust'].get(exhaust['pixie'], effectDesc._selectorDesc)
    nationID = vDesc.type.id[0]
    for partName, cacheName, cacheIDs in (
            ('chassis', 'chassis', 'chassisIDs'), ('engine', 'engines', 'engineIDs'), ('gun', 'guns', 'gunIDs')):
        soundID = modelDesc[partName].get('soundID')
        if soundID:
            part = getattr(vDesc, partName)
            pickFrom = getattr(g_cache, cacheName)(nationID).get(getattr(g_cache, cacheIDs)(nationID).get(soundID))
            if pickFrom is not None:
                if partName != 'gun':
                    part.sounds = pickFrom.sounds
                else:
                    part.effects = pickFrom.effects
                    part.reloadEffect = pickFrom.reloadEffect
