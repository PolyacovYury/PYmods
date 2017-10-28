import PYmodsCore
import ResMgr
import copy
import traceback
from collections import namedtuple
from gui.ClientHangarSpace import _VehicleAppearance
from items.components.chassis_components import *
from items.components.chassis_components import SplineConfig, WheelsConfig
from items.components.shared_components import Camouflage, ModelStatesPaths, NodesAndGroups
from items.components.sound_components import WWTripleSoundConfig
from items.vehicles import g_cache
from vehicle_systems.tankStructure import TankNodeNames, TankPartNames
from . import attached_models
from .. import g_config

TrackMaterials = namedtuple('TrackMaterials', ('lodDist', 'leftMaterial', 'rightMaterial', 'textureScale'))
TrackParams = namedtuple('TrackParams', ('thickness', 'maxAmplitude', 'maxOffset', 'gravity'))


def find(xmlName, isPlayerVehicle, isAlly, currentMode='battle'):
    g_config.OMDesc = None
    g_config.OSDesc = dict.fromkeys(g_config.OSDesc, None)
    if not g_config.OM.enabled:
        return
    curTankType = 'Player' if isPlayerVehicle else 'Ally' if isAlly else 'Enemy'
    selected = g_config.OM.selected
    if currentMode != 'remod':
        snameList = sorted(g_config.OM.models.keys()) + ['']
        if selected[curTankType].get(xmlName) not in snameList:
            snameIdx = 0
        else:
            snameIdx = snameList.index(selected[curTankType][xmlName])
        for Idx in xrange(snameIdx, len(snameList)):
            curPRecord = g_config.OM.models.get(snameList[Idx])
            if snameList[Idx] and xmlName not in curPRecord.whitelists[curTankType]:
                continue
            else:
                if xmlName in selected[curTankType]:
                    selected[curTankType][xmlName] = getattr(curPRecord, 'name', '')
                g_config.OMDesc = curPRecord
                break

        # noinspection PyUnboundLocalVariable
        if g_config.OMDesc is None and snameList[Idx] and xmlName in selected[curTankType]:
            del selected[curTankType][xmlName]
        g_config.loadJson('remodsCache', selected, g_config.configPath, True, doPrint=g_config.data['isDebug'])
    else:
        snameList = sorted(g_config.OM.models.keys())
        if selected['Remod'] not in snameList:
            snameIdx = 0
        else:
            snameIdx = snameList.index(selected['Remod'])
        sname = snameList[snameIdx]
        g_config.OMDesc = g_config.OM.models[sname]
        selected['Remod'] = sname
        g_config.loadJson('remodsCache', selected, g_config.configPath, True, doPrint=g_config.data['isDebug'])


def apply(vDesc):
    for key in ('splineDesc', 'trackParams'):
        if getattr(vDesc.chassis, key) is None:
            setattr(vDesc.chassis, key, {})
    data = g_config.OMDesc.data
    for key in ('traces', 'tracks', 'wheels', 'groundNodes', 'trackNodes', 'splineDesc', 'trackParams'):
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
                        d = GroundNodeGroup(*(d[0], d[4], d[5], d[1], d[2], d[3]))
                    groups.append(d)
                for d in obj['nodes']:
                    if not hasattr(d, '_fields'):
                        d = GroundNode(*(d[1], d[0], d[2], d[3]))
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
        models = part.models
        part.models = ModelStatesPaths(data[partName]['undamaged'], models.destroyed, models.exploded)
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
            print 'RemodEnabler: provided emblem slots corrupted. Stock slots restored'
            if g_config.data['isDebug']:
                print 'cntPlayer =', cntPlayer
                print 'cntInscription =', cntInscription
    for partName in ('hull', 'turret'):
        if not data[partName]['emblemSlots']:
            part = getattr(vDesc, partName)
            for i in range(len(part.emblemSlots)):
                part.emblemSlots[i] = part.emblemSlots[i]._replace(size=0.001)

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
