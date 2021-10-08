from collections import defaultdict
from math import degrees

import Math
import ResMgr
import nations
from OpenModsCore import remDups
from items import _xml
from items.components import chassis_components as cc, shared_components
from items.components.component_constants import ALLOWED_EMBLEM_SLOTS as AES
from items.components.shared_components import EmblemSlot
from items.readers import shared_readers
from items.vehicles import _writeAODecals, _writeDrivenJoints, g_cache, g_list
from items.writers import chassis_writers, shared_writers

modelDescriptor = lambda: {
    'name': '', 'message': '', 'player': True, 'ally': True, 'enemy': True, 'whitelist': [],
    'chassis': {'undamaged': '', 'emblemSlots': [], 'AODecals': [], 'hullPosition': [], 'soundID': ''},
    'hull': {'undamaged': '', 'emblemSlots': [], 'exhaust': {'nodes': [], 'pixie': ''},
             'camouflage': {'exclusionMask': '', 'tiling': [1.0, 1.0, 0.0, 0.0]}},
    'turret': {'undamaged': '', 'emblemSlots': [],
               'camouflage': {'exclusionMask': '', 'tiling': [1.0, 1.0, 0.0, 0.0]}},
    'gun': {'undamaged': '', 'emblemSlots': [], 'soundID': '', 'drivenJoints': None,
            'camouflage': {'exclusionMask': '', 'tiling': [1.0, 1.0, 0.0, 0.0]}},
    'engine': {'soundID': ''},
    'common': {'camouflage': {'exclusionMask': '', 'tiling': [1.0, 1.0, 0.0, 0.0]}}}


def save_as_xml(g_config, path, name, data):
    data = fill_descriptor(g_config, data)
    section = ResMgr.openSection('.' + path + '/' + name + '.xml', True)
    section.write('message', data['message'])
    for k in g_config.teams:
        section.writeBool(k, data[k])
    section.writeString('whitelist', ' '.join(data['whitelist']))
    nationIDs = set()
    lowered_ids = {name.partition(':')[2].lower(): ids[0] for name, ids in g_list._VehicleList__ids.items()}  # shitheads
    for vehName in data['whitelist']:
        nationID = lowered_ids.get(vehName.lower())
        if nationID is not None:
            nationIDs.add(nationID)
        else:
            print g_config.LOG, 'whitelist vehicle for', name, 'not recognized:', vehName
    if not nationIDs:
        print g_config.LOG, 'nation ID could not be detected for', name, '- all soundIDs will be saved as-is and ignored'
    elif len(nationIDs) > 1:
        print g_config.LOG, 'multiple nation IDs detected for', name, '- all soundIDs will be saved as-is and ignored'
    else:
        nationID = nationIDs.pop()
        for k in ('chassis', 'gun', 'engine'):
            data[k]['soundID'] = data[k]['soundID'] and nations.NAMES[nationID] + ':' + data[k]['soundID']
    write_chassis(section.createSection('chassis'), data['chassis'])
    write_hull(section.createSection('hull'), data['hull'])
    write_turret(section.createSection('turret'), data['turret'])
    write_gun(section.createSection('gun'), data['gun'])
    if data['engine']['soundID']:
        _xml.rewriteString(section.createSection('engine'), 'soundID', data['engine']['soundID'], '')
    write_camouflage(section, data['common'])
    section.save()


class _SplineConfig(cc.SplineConfig):
    @property
    def editorData(self):
        return self


def write_chassis(section, data):
    section.writeString('models/undamaged', data['undamaged'])
    data['traces']['size'] = tuple(data['traces']['size'])
    traces = cc.Traces(**data['traces'])
    chassis_writers.writeTraces(traces, section, g_cache)
    _xml.rewriteVector2(section, 'topRightCarryingPoint', Math.Vector2(traces.centerOffset, 2.5))
    trackParams = cc.TrackBasicParams(**data['tracks'])
    chassis_writers.writeTrackBasicParams(trackParams, section, g_cache)
    _xml.rewriteInt(section, 'tracks/pairsCount', trackParams.pairsCount, 1)
    section.createSection('wheels')
    shared_writers.writeLodDist(data['chassisLodDistance'], section['wheels'], 'lodDist', g_cache)
    wheels = cc.WheelsConfig(
        groups=tuple(cc.WheelGroup(**d) for d in data['wheels']['groups']),
        wheels=tuple(cc.Wheel(**d) for d in data['wheels']['wheels']))
    for group in wheels.groups:
        subsection = section.createSection('wheels/group')
        _xml.rewriteBool(subsection, 'isLeft', group.isLeft)
        _xml.rewriteString(subsection, 'template', group.template)
        _xml.rewriteFloat(subsection, 'radius', group.radius)
        _xml.rewriteInt(subsection, 'startIndex', group.startIndex, 0)
        _xml.rewriteInt(subsection, 'count', group.count, 1)
    drivingWheels = []
    for wheel in wheels.wheels:
        subsection = section.createSection('wheels/wheel')
        _xml.rewriteBool(subsection, 'isLeft', wheel.isLeft)
        _xml.rewriteBool(subsection, 'isLeading', wheel.isLeading)
        _xml.rewriteString(subsection, 'name', wheel.nodeName)
        _xml.rewriteFloat(subsection, 'radius', wheel.radius)
        _xml.rewriteFloat(subsection, 'syncAngle', wheel.leadingSyncAngle, 60)
        if wheel.isLeft and wheel.isLeading:
            drivingWheels.append(wheel.nodeName)
    drivingWheels.sort()
    _xml.rewriteString(section, 'drivingWheels', drivingWheels[0] + ' ' + drivingWheels[-1])
    _xml.rewriteVector3(section, 'hullPosition', Math.Vector3(*data['hullPosition']))
    groundNodes = shared_components.NodesAndGroups(
        nodes=tuple(cc.GroundNode(**d) for d in data['groundNodes']['nodes']),
        groups=tuple(cc.GroundNodeGroup(**d) for d in data['groundNodes']['groups']),
        activePostmortem=data['groundNodes']['activePostmortem'], lodSettings=data['groundNodes']['lodSettings'])
    chassis_writers.writeGroundNodes(groundNodes.groups, section)
    for node in groundNodes.nodes:
        subsection = section.createSection('groundNodes/node')
        _xml.rewriteString(subsection, 'name', node.nodeName)
        _xml.rewriteString(subsection, 'affectedWheelName', node.affectedWheelName, '')
        _xml.rewriteBool(subsection, 'isLeft', node.isLeft)
        _xml.rewriteFloat(subsection, 'minOffset', node.minOffset)
        _xml.rewriteFloat(subsection, 'maxOffset', node.maxOffset)
        _xml.rewriteInt(subsection, 'collisionSamplesCount', node.collisionSamplesCount, 1)
        _xml.rewriteBool(subsection, 'hasLiftMode', node.hasLiftMode, False)
    _xml.rewriteBool(section['groundNodes'], 'activePostmortem', groundNodes.activePostmortem, False)
    if groundNodes.lodSettings is not None:
        subsection = section.createSection('groundNodes/lodSettings')
        shared_writers.writeLodDist(groundNodes.lodSettings.maxLodDistance, subsection, 'maxLodDistance', g_cache)
        _xml.rewriteInt(subsection, 'maxPriority', groundNodes.lodSettings.maxPriority)
    trackSplineParams = cc.TrackSplineParams(**data['trackSplineParams'])
    _xml.rewriteFloat(section, 'trackThickness', trackSplineParams.thickness)
    trackNodes = shared_components.NodesAndGroups(
        nodes=tuple(cc.TrackNode(**d) for d in data['trackNodes']['nodes']),
        groups=(), activePostmortem=False, lodSettings=None)
    if trackNodes.nodes:
        _xml.rewriteFloat(section, 'trackNodes/maxAmplitude', trackSplineParams.maxAmplitude)
        _xml.rewriteFloat(section, 'trackNodes/maxOffset', trackSplineParams.maxOffset)
        _xml.rewriteFloat(section, 'trackNodes/gravity', trackSplineParams.gravity)
        for curNode in trackNodes.nodes:
            curSection = section['trackNodes'].createSection('node')
            _xml.rewriteBool(curSection, 'isLeft', curNode.isLeft)
            _xml.rewriteString(curSection, 'name', curNode.name)
            _xml.rewriteFloat(curSection, 'elasticity', curNode.elasticity, 1500.0)
            _xml.rewriteFloat(curSection, 'damping', curNode.damping, 1.0)
            _xml.rewriteFloat(curSection, 'forwardElastK', curNode.forwardElasticityCoeff, 1.0)
            _xml.rewriteFloat(curSection, 'backwardElastK', curNode.backwardElasticityCoeff, 1.0)
            _xml.rewriteFloat(curSection, 'offset', curNode.initialOffset, 0.0)
            if curNode.leftNodeName:
                _xml.rewriteString(curSection, 'leftSibling', curNode.leftNodeName)
            if curNode.rightNodeName:
                _xml.rewriteString(curSection, 'rightSibling', curNode.rightNodeName)
        chassis_writers.writeTrackNodes(trackNodes.nodes, section)
    splineDesc = _SplineConfig(
        ({'default': cc.SplineSegmentModelSet(**data['splineDesc']['segmentModelSets'])} or None),
        **{k: v for k, v in data['splineDesc'].items() if k != 'segmentModelSets'})
    chassis_writers.writeSplineDesc(splineDesc, section, g_cache)
    suspensionData = data.get('leveredSuspension')
    if suspensionData is not None:
        for leverSectionName, leverSection in section['leveredSuspension'].items():
            if leverSectionName != 'lever':
                continue
            leverName = _xml.readNonEmptyString(None, leverSection, 'trackNode')
            for lever in suspensionData.levers:
                if leverName == lever.trackNodeName:
                    limits = Math.Vector2(degrees(lever.minAngle), degrees(lever.maxAngle))
                    _xml.rewriteVector2(leverSection, 'limits', limits)
    section.createSection('AODecals')
    for _ in data['AODecals']:
        section.createSection('AODecals/decal')
    _writeAODecals(data['AODecals'], section, 'AODecals')
    _xml.rewriteString(section, 'soundID', data['soundID'], '')


def write_camouflage(section, data):
    tiling = data['camouflage']['tiling']
    if tiling is not None and len(tiling) == 4 and tiling != [1.0, 1.0, 0.0, 0.0]:
        _xml.rewriteVector4(section, 'camouflage/tiling', Math.Vector4(tiling[0], tiling[1], tiling[2], tiling[3]))
    mask = data['camouflage']['exclusionMask']
    if mask is not None and len(mask) > 0:
        _xml.rewriteString(section, 'camouflage/exclusionMask', mask)


def write_non_chassis(section, data):
    section.writeString('models/undamaged', data['undamaged'])
    shared_writers.writeCustomizationSlots(data['emblemSlots'], section, 'customizationSlots')
    write_camouflage(section, data)


def write_hull(section, data):
    write_non_chassis(section, data)
    _xml.rewriteString(section, 'exhaust/pixie', data['exhaust']['pixie'])
    _xml.rewriteString(section, 'exhaust/nodes', ' '.join(data['exhaust']['nodes']))


def write_turret(section, data):
    write_non_chassis(section, data)


def write_gun(section, data):
    write_non_chassis(section, data)
    _xml.rewriteString(section, 'soundID', data['soundID'], '')
    _writeDrivenJoints(data['drivenJoints'], section, 'drivenJoints')


# noinspection PyTypeChecker
def fill_descriptor(g_config, json_data):
    descr = modelDescriptor()
    descr['message'] = json_data.get('message', '')
    for k in g_config.teams:
        descr[k] = json_data.get(k, True)
    descr['whitelist'] = remDups(x.strip() for x in json_data['whitelist'] if x.strip())
    for key, data in descr.iteritems():
        if key in ('name', 'message', 'whitelist') + g_config.teams:
            continue
        if key == 'common':
            confSubDict = json_data
        else:
            confSubDict = json_data.get(key)
        if not confSubDict:
            continue
        if 'undamaged' in data:
            data['undamaged'] = confSubDict['undamaged']
        if 'AODecals' in data and 'AODecals' in confSubDict and 'hullPosition' in confSubDict:
            data['AODecals'] = []
            for subList in confSubDict['AODecals']:
                m = Math.Matrix()
                for strNum, row in enumerate(subList):
                    for colNum, elemNum in enumerate(row):
                        m.setElement(strNum, colNum, elemNum)
                data['AODecals'].append(m)
            data['hullPosition'] = confSubDict['hullPosition']
        if 'camouflage' in data and 'exclusionMask' in confSubDict.get('camouflage', {}):
            data['camouflage']['exclusionMask'] = confSubDict['camouflage']['exclusionMask']
            if 'tiling' in confSubDict['camouflage']:
                data['camouflage']['tiling'] = confSubDict['camouflage']['tiling']
        if 'emblemSlots' in data:
            data['emblemSlots'] = slots = []
            id_by_type = {}
            for subDict in confSubDict.get('emblemSlots', ()):
                slotType = subDict['type']
                if slotType not in AES:
                    print g_config.LOG, 'emblem slot type', slotType, 'not in', AES
                    continue
                subDict.update({k: Math.Vector3(subDict[k]) for k in ('rayStart', 'rayEnd', 'rayUp')})
                if slotType not in id_by_type:
                    slotId = subDict['slotId']
                    minId, maxId = customizationSlotIds[key][slotType]
                    if minId <= slotId <= maxId:
                        if shared_readers.__customizationSlotIdRanges is None:
                            shared_readers.__customizationSlotIdRanges = defaultdict(dict)
                            shared_readers._readCustomizationSlotIdRanges()
                        slotId = shared_readers.__customizationSlotIdRanges[key][slotType][0] + slotId - minId
                    subDict['slotId'] = id_by_type[slotType] = slotId
                else:
                    id_by_type[slotType] += 1
                    subDict['slotId'] = id_by_type[slotType]
                slots.append(EmblemSlot(**subDict))
        if 'exhaust' in data and 'exhaust' in confSubDict:
            if 'nodes' in confSubDict['exhaust']:
                data['exhaust']['nodes'] = confSubDict['exhaust']['nodes']
            if 'pixie' in confSubDict['exhaust']:
                data['exhaust']['pixie'] = confSubDict['exhaust']['pixie']
        if key == 'chassis':
            for k in (
                    'traces', 'tracks', 'wheels', 'groundNodes', 'trackNodes', 'splineDesc', 'trackSplineParams',
                    'leveredSuspension', 'chassisLodDistance',):
                data[k] = confSubDict[k]
        for k in ('soundID', 'drivenJoints'):
            if k in data and k in confSubDict:
                data[k] = confSubDict[k]
    return descr


customizationSlotIds = {
    'hull': {
        'clan': (1, 1),
        'paint': (2, 2),
        'camouflage': (3, 3),
        'player': (4, 35),
        'inscription': (36, 67),
        'projectionDecal': (68, 195),
        'insignia': (196, 203),
        'fixedEmblem': (204, 255),
        'fixedInscription': (204, 255),
        'attachment': (1024, 1073),
        'sequence': (1024, 1073)},
    'chassis': {
        'paint': (256, 256),
        'style': (257, 257),
        'insignia': (258, 265),
        'fixedEmblem': (266, 319),
        'fixedInscription': (266, 319),
        'attachment': (1074, 1123),
        'sequence': (1074, 1123)},
    'turret': {
        'clan': (1, 1),
        'paint': (512, 512),
        'camouflage': (513, 513),
        'player': (514, 545),
        'inscription': (546, 577),
        'projectionDecal': (578, 705),
        'insignia': (706, 713),
        'fixedEmblem': (714, 767),
        'fixedInscription': (714, 767),
        'attachment': (1124, 1173),
        'sequence': (1124, 1173)},
    'gun': {
        'paint': (768, 769),
        'camouflage': (770, 770),
        'insigniaOnGun': (771, 771),
        'player': (772, 803),
        'inscription': (804, 835),
        'projectionDecal': (836, 963),
        'insignia': (964, 971),
        'fixedEmblem': (972, 1023),
        'fixedInscription': (972, 1023),
        'attachment': (1174, 1224),
        'sequence': (1174, 1224)}}
