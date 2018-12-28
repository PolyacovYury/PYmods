import Math
import copy
from items.components import chassis_components as cc
from items.components.shared_components import Camouflage, ModelStatesPaths, NodesAndGroups
from items.vehicles import g_cache
from vehicle_systems.tankStructure import TankPartNames

chassis_params = ('traces', 'tracks', 'wheels', 'groundNodes', 'trackNodes', 'splineDesc', 'trackParams', 'leveredSuspension')


def apply(vDesc, modelDesc):
    for key in chassis_params:
        obj = modelDesc['chassis'][key]
        if key == 'traces':
            obj['size'] = tuple(obj['size'])
            obj = cc.Traces(**obj)
        elif key == 'tracks':
            obj = cc.TrackMaterials(**obj)
        elif key == 'wheels':
            obj = cc.WheelsConfig(lodDist=obj['lodDist'], groups=tuple(cc.WheelGroup(**d) for d in obj['groups']),
                                  wheels=tuple(cc.Wheel(**d) for d in obj['wheels']))
        elif key == 'groundNodes':
            obj = NodesAndGroups(nodes=tuple(cc.GroundNode(**d) for d in obj['nodes']),
                                 groups=tuple(cc.GroundNodeGroup(**d) for d in obj['groups']),
                                 activePostmortem=obj['activePostmortem'], lodSettings=obj['lodSettings'])
        elif key == 'trackNodes':
            obj = NodesAndGroups(nodes=tuple(cc.TrackNode(**d) for d in obj['nodes']), groups=(),
                                 activePostmortem=obj['activePostmortem'], lodSettings=obj['lodSettings'])
        elif key == 'splineDesc':
            for setName, modelSet in obj['segmentModelSets'].items():
                obj['segmentModelSets'][setName] = cc.SplineSegmentModelSet(**modelSet)
            obj = cc.SplineConfig(**obj)
        elif key == 'trackParams':
            obj = cc.TrackParams(**obj)
        elif key == 'leveredSuspension':
            if obj is not None:
                obj['levers'] = [cc.SuspensionLever(**d) for d in obj['levers']]
                obj = cc.LeveredSuspensionConfig(**obj)
        setattr(vDesc.chassis, key, obj)
    vDesc.chassis.physicalTracks = {}
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
