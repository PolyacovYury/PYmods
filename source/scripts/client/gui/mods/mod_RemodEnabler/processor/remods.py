import copy
from helpers.xmltodict import OrderedDict
from items.components.chassis_components import Wheel, WheelGroup, TrackNode, TrackMaterials, GroundNode, GroundNodeGroup, \
    Traces, SplineConfig, WheelsConfig, TrackParams
from items.components.shared_components import Camouflage, ModelStatesPaths, NodesAndGroups
from items.components.sound_components import WWTripleSoundConfig
from items.vehicles import g_cache
from vehicle_systems.tankStructure import TankPartNames

SplineConfig._asdict = lambda self: OrderedDict(
    (attrName.strip('_'), getattr(self, attrName.strip('_'))) for attrName in self.__slots__)
chassis_params = ('traces', 'tracks', 'wheels', 'groundNodes', 'trackNodes', 'splineDesc', 'trackParams')


def migrate_chassis_config(config):  # please send data['chassis'] here
    new_config = OrderedDict()
    for key in config:
        if key not in chassis_params or not isinstance(config[key], basestring):
            if 'wwsound' not in key:  # sounds are obsolete
                new_config[key] = config[key]
            continue  # config already converted
        obj = eval(config[key])
        if isinstance(obj, dict):  # ancient config
            if key == 'traces':
                newObj = Traces(**obj)
            elif key == 'tracks':
                newObj = TrackMaterials(**obj)
            elif key == 'wheels':
                groups = []
                wheels = []
                for d in obj['groups']:
                    if not hasattr(d, '_fields'):
                        d = WheelGroup(*d)
                    groups.append(d)
                for d in obj['wheels']:
                    if not hasattr(d, '_fields'):
                        d = Wheel(d[0], d[2], d[1], d[3], d[4])
                    wheels.append(d)
                newObj = WheelsConfig(lodDist=obj['lodDist'], groups=tuple(groups), wheels=tuple(wheels))
            elif key == 'groundNodes':
                groups = []
                nodes = []
                for d in obj['groups']:
                    if not hasattr(d, '_fields'):
                        d = GroundNodeGroup(d[0], d[4], d[5], d[1], d[2], d[3])
                    groups.append(d)
                for d in obj['nodes']:
                    if not hasattr(d, '_fields'):
                        d = GroundNode(d[1], d[0], d[2], d[3])
                    nodes.append(d)
                newObj = NodesAndGroups(nodes=tuple(nodes), groups=tuple(groups))
            elif key == 'trackNodes':
                nodes = []
                for d in obj['nodes']:
                    if not hasattr(d, '_fields'):
                        d = TrackNode(d[0], d[1], d[2], d[5], d[6], d[4], d[3], d[7], d[8])
                    nodes.append(d)
                newObj = NodesAndGroups(nodes=tuple(nodes), groups=())
            elif key == 'splineDesc':
                newObj = SplineConfig(**obj)
            elif key == 'trackParams':
                newObj = TrackParams(**obj)
            else:
                assert False
            obj = newObj
        new_obj = None
        if not isinstance(obj, dict):  # we assume that we have a namedtuple, if we don't - something malicious, so crash
            new_obj = obj._asdict()
            keys = ()
            if key == 'wheels':
                keys = ('groups', 'wheels')
            elif key in ('groundNodes', 'trackNodes'):
                keys = ('nodes', 'groups')
            for sub in keys:
                for idx, value in enumerate(new_obj[sub]):
                    new_obj[sub][idx] = value._asdict()
        if new_obj is not None:
            new_config[key] = new_obj
    return new_config


def apply(vDesc, modelDesc):
    for key in ('splineDesc', 'trackParams'):
        if getattr(vDesc.chassis, key) is None:
            setattr(vDesc.chassis, key, {})
    data = modelDesc.data
    for key in chassis_params:
        obj = eval(data['chassis'][key])
        newObj = None
        if isinstance(obj, dict):
            if key == 'traces':
                newObj = Traces(**obj)
            elif key == 'tracks':
                newObj = TrackMaterials(**obj)
            elif key == 'wheels':
                groups = []
                wheels = []
                for d in obj['groups']:
                    if not hasattr(d, '_fields'):
                        d = WheelGroup(*d)
                    groups.append(d)
                for d in obj['wheels']:
                    if not hasattr(d, '_fields'):
                        d = Wheel(d[0], d[2], d[1], d[3], d[4])
                    wheels.append(d)
                newObj = WheelsConfig(lodDist=obj['lodDist'], groups=tuple(groups), wheels=tuple(wheels))
            elif key == 'groundNodes':
                groups = []
                nodes = []
                for d in obj['groups']:
                    if not hasattr(d, '_fields'):
                        d = GroundNodeGroup(d[0], d[4], d[5], d[1], d[2], d[3])
                    groups.append(d)
                for d in obj['nodes']:
                    if not hasattr(d, '_fields'):
                        d = GroundNode(d[1], d[0], d[2], d[3])
                    nodes.append(d)
                newObj = NodesAndGroups(nodes=tuple(nodes), groups=tuple(groups))
            elif key == 'trackNodes':
                nodes = []
                for d in obj['nodes']:
                    if not hasattr(d, '_fields'):
                        d = TrackNode(d[0], d[1], d[2], d[5], d[6], d[4], d[3], d[7], d[8])
                    nodes.append(d)
                newObj = NodesAndGroups(nodes=tuple(nodes), groups=())
            elif key == 'splineDesc':
                newObj = SplineConfig(**obj)
            elif key == 'trackParams':
                newObj = TrackParams(**obj)
        setattr(vDesc.chassis, key, newObj if newObj is not None else obj)
    if data['chassis']['AODecals']:
        AODecalsOffset = vDesc.chassis.hullPosition - data['chassis']['hullPosition']
        vDesc.chassis.AODecals = copy.deepcopy(data['chassis']['AODecals'])
        vDesc.chassis.AODecals[0].setElement(3, 1, AODecalsOffset.y)
    for partName in TankPartNames.ALL:
        part = getattr(vDesc, partName)
        models = part.modelsSets['default']
        part.modelsSets['default'] = ModelStatesPaths(data[partName]['undamaged'], models.destroyed, models.exploded)
        part.models = part.modelsSets['default']
    if data['gun']['effects']:
        newGunEffects = g_cache._gunEffects.get(data['gun']['effects'])
        if newGunEffects:
            vDesc.gun.effects = newGunEffects
    if data['gun']['reloadEffect']:
        newGunReloadEffect = g_cache._gunReloadEffects.get(data['gun']['reloadEffect'])
        if newGunReloadEffect:
            vDesc.gun.reloadEffect = newGunReloadEffect
    vDesc.gun.emblemSlots = data['gun']['emblemSlots']
    if data['hull']['emblemSlots']:
        cntClan = 1
        cntPlayer = cntInscription = 0
        for partName in ('hull', 'turret'):
            for slot in getattr(vDesc, partName).emblemSlots:
                if slot.type == 'inscription':
                    cntInscription += 1
                if slot.type == 'player':
                    cntPlayer += 1
        try:
            vDesc.hull.emblemSlots = []
            vDesc.turret.emblemSlots = []
            for partName in ('hull', 'turret'):
                for slot in data[partName]['emblemSlots']:
                    if slot.type in ('player', 'inscription', 'clan'):
                        getattr(vDesc, partName).emblemSlots.append(slot)
                    if slot.type == 'player' and cntPlayer > 0:
                        cntPlayer -= 1
                    if slot.type == 'inscription' and cntInscription > 0:
                        cntInscription -= 1
                    if slot.type == 'clan' and cntClan > 0:
                        cntClan -= 1

            assert not cntClan and not cntPlayer and not cntInscription
        except StandardError:
            from .. import g_config
            print g_config.ID + ': provided emblem slots corrupted. Stock slots restored'
            if g_config.data['isDebug']:
                print 'cntPlayer =', cntPlayer
                print 'cntInscription =', cntInscription
    for partName in ('hull', 'turret'):
        part = getattr(vDesc, partName)
        slots = list(part.emblemSlots)
        if not data[partName]['emblemSlots']:
            for i in range(len(slots)):
                slots[i] = slots[i]._replace(size=0.001)
        part.emblemSlots = tuple(slots)

    exclMask = data['common']['camouflage']['exclusionMask']
    vDesc.type.camouflage = Camouflage(
        data['common']['camouflage']['tiling'] if exclMask else vDesc.type.camouflage.tiling, exclMask)
    for partName in TankPartNames.ALL[1:]:
        camoData = data[partName]['camouflage']
        exclMask = camoData['exclusionMask']
        if exclMask:
            getattr(vDesc, partName).camouflage = Camouflage(camoData['tiling'], exclMask)
    exhaust = data['hull']['exhaust']
    for effectDesc in vDesc.hull.customEffects:
        if exhaust['nodes']:
            effectDesc.nodes[:] = exhaust['nodes']
        effectDesc._selectorDesc = g_cache._customEffects['exhaust'].get(exhaust['pixie'], effectDesc._selectorDesc)
    for partName in ('chassis', 'engine'):
        soundIDs = []
        part = getattr(vDesc, partName)
        partData = data[partName]
        for key in ('wwsound', 'wwsoundPC', 'wwsoundNPC'):
            soundID = partData[key]
            if not soundID:
                soundID = getattr(part.sounds, key)
            soundIDs.append(soundID)
        part.sounds = WWTripleSoundConfig(*soundIDs)
