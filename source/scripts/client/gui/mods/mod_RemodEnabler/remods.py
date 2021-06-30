import Math
import copy
from items.components import chassis_components as cc
from items.components.shared_components import Camouflage, ModelStatesPaths, NodesAndGroups
from items.vehicles import g_cache
from vehicle_systems.tankStructure import TankPartNames

chassis_params = (
    'traces', 'tracks', 'wheels', 'groundNodes', 'trackNodes', 'splineDesc', 'trackSplineParams', 'leveredSuspension')


class VehicleTypeProxy(object):  # I would
    def __init__(self, vDesc):  # tear off
        self._vDesc = vDesc  # the hands
        self._type = vDesc.type  # that made me

    def __getattr__(self, item):  # write this crap
        value = getattr(self._type, item)  # see items.vehicles.Cache.vehicle() and VehicleType.__init__() for details
        if item == 'camouflage' and getattr(self._vDesc, 'modelDesc', None) is not None:
            mask = self._vDesc.modelDesc['common']['camouflage']['exclusionMask']  # all this
            tiling = self._vDesc.modelDesc['common']['camouflage']['tiling']  # just to break the attribute link
            value = value._replace(tiling=tiling, exclusionMask=mask or value.exclusionMask)  # holy shit
        return value


def apply(vDesc, modelDesc, modelsSet):
    for key in chassis_params:
        obj = copy.deepcopy(modelDesc['chassis'][key])
        if key == 'traces':
            obj['size'] = tuple(obj['size'])
            obj = cc.Traces(**obj)
        elif key == 'tracks':
            obj = cc.TrackBasicParams(**obj)
        elif key == 'wheels':
            obj = cc.WheelsConfig(groups=tuple(cc.WheelGroup(**d) for d in obj['groups']),
                                  wheels=tuple(cc.Wheel(**d) for d in obj['wheels']))
        elif key == 'groundNodes':
            obj = NodesAndGroups(nodes=tuple(cc.GroundNode(**d) for d in obj['nodes']),
                                 groups=tuple(cc.GroundNodeGroup(**d) for d in obj['groups']),
                                 activePostmortem=obj['activePostmortem'], lodSettings=obj['lodSettings'])
        elif key == 'trackNodes':
            obj = NodesAndGroups(nodes=tuple(cc.TrackNode(**d) for d in obj['nodes']), groups=(),
                                 activePostmortem=obj['activePostmortem'], lodSettings=obj['lodSettings'])
        elif key == 'splineDesc':
            obj = cc.SplineConfig(({modelsSet: cc.SplineSegmentModelSet(**obj['segmentModelSets'])} or None),
                                  **{k: v for k, v in obj.items() if k != 'segmentModelSets'})
        elif key == 'trackSplineParams':
            obj = cc.TrackSplineParams(**obj)
        elif key == 'leveredSuspension':
            if obj is not None:
                obj = cc.LeveredSuspensionConfig(([cc.SuspensionLever(**d) for d in obj['levers']] or None),
                                                 **{k: v for k, v in obj.items() if k != 'levers'})
        setattr(vDesc.chassis, key, obj)
    vDesc.chassis.chassisLodDistance = modelDesc['chassis']['chassisLodDistance']
    vDesc.chassis.physicalTracks = {}
    if modelDesc['chassis']['AODecals']:
        AODecalsOffset = vDesc.chassis.hullPosition - Math.Vector3(*modelDesc['chassis']['hullPosition'])
        vDesc.chassis.AODecals = copy.deepcopy(modelDesc['chassis']['AODecals'])
        vDesc.chassis.AODecals[0].setElement(3, 1, AODecalsOffset.y)
    vDesc.type = VehicleTypeProxy(vDesc)  # all this to break the attribute link
    for partName in TankPartNames.ALL:
        part = getattr(vDesc, partName)
        models = part.modelsSets[modelsSet]
        part.modelsSets[modelsSet] = ModelStatesPaths(modelDesc[partName]['undamaged'], models.destroyed, models.exploded)
        part.models = part.modelsSets['default']
        part.emblemSlots = tuple(modelDesc[partName]['emblemSlots'])
        if partName == 'chassis':
            continue
        camoData = modelDesc[partName]['camouflage']
        partMask = camoData['exclusionMask']
        if partMask:
            part.camouflage = part.camouflage._replace(tiling=camoData['tiling'], exclusionMask=partMask)
    vDesc.gun.drivenJoints = modelDesc['gun']['drivenJoints']
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
