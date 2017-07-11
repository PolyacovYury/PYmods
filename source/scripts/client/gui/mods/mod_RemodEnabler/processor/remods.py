import copy
from items.vehicle_config_types import GroundNode, GroundNodeGroup, TrackNode, Wheel, WheelGroup
from items.vehicles import g_cache
from vehicle_systems.tankStructure import TankPartNames
from .. import g_config


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
        g_config.loadJson('remodsCache', selected, g_config.configPath, True)
    else:
        snameList = sorted(g_config.OM.models.keys())
        if selected['Remod'] not in snameList:
            snameIdx = 0
        else:
            snameIdx = snameList.index(selected['Remod'])
        sname = snameList[snameIdx]
        g_config.OMDesc = g_config.OM.models[sname]
        selected['Remod'] = sname
        g_config.loadJson('remodsCache', selected, g_config.configPath, True)


def apply(vDesc):
    for key in ('splineDesc', 'trackParams'):
        if vDesc.chassis[key] is None:
            vDesc.chassis[key] = {}
    data = g_config.OMDesc.data
    for key in ('traces', 'tracks', 'wheels', 'groundNodes', 'trackNodes', 'splineDesc', 'trackParams'):
        obj = eval(data['chassis'][key])
        if key not in ('wheels', 'groundNodes', 'trackNodes') or any(
                hasattr(d, '_fields') for l in obj.itervalues() if type(l) != float for d in l):
            vDesc.chassis[key] = obj
            continue
        newObj = {}
        if key == 'wheels':
            newObj['groups'] = []
            newObj['wheels'] = []
            newObj['lodDist'] = obj['lodDist']
            newObj['leadingWheelSyncAngle'] = obj['leadingWheelSyncAngle']
            for d in obj['groups']:
                newObj['groups'].append(WheelGroup(*d))
            for d in obj['wheels']:
                newObj['wheels'].append(Wheel(*(d[0], d[2], d[1], d[3], d[4])))
        if key == 'groundNodes':
            newObj['groups'] = []
            newObj['nodes'] = []
            for d in obj['groups']:
                newObj['groups'].append(GroundNodeGroup(*(d[0], d[4], d[5], d[1], d[2], d[3])))
            for d in obj['nodes']:
                newObj['nodes'].append(GroundNode(*(d[1], d[0], d[2], d[3])))
        if key == 'trackNodes':
            newObj['groups'] = []
            newObj['nodes'] = []
            for d in obj['nodes']:
                newObj['nodes'].append(TrackNode(*(d[0], d[1], d[2], d[5], d[6], d[4], d[3], d[7], d[8])))
        vDesc.chassis[key] = newObj
    if data['chassis']['AODecals']:
        AODecalsOffset = vDesc.chassis['hullPosition'] - data['chassis']['hullPosition']
        vDesc.chassis['AODecals'] = copy.deepcopy(data['chassis']['AODecals'])
        vDesc.chassis['AODecals'][0].setElement(3, 1, AODecalsOffset.y)
    for part in TankPartNames.ALL:
        getattr(vDesc, part)['models']['undamaged'] = data[part]['undamaged']
    if data['gun']['effects']:
        newGunEffects = g_cache._gunEffects.get(data['gun']['effects'])
        if newGunEffects:
            vDesc.gun['effects'] = newGunEffects
    if data['gun']['reloadEffect']:
        newGunReloadEffect = g_cache._gunReloadEffects.get(data['gun']['reloadEffect'])
        if newGunReloadEffect:
            vDesc.gun['reloadEffect'] = newGunReloadEffect
    vDesc.gun['emblemSlots'] = data['gun']['emblemSlots']
    if data['hull']['emblemSlots']:
        cntClan = 1
        cntPlayer = cntInscription = 0
        for part in ('hull', 'turret'):
            for slot in getattr(vDesc, part)['emblemSlots']:
                if slot.type == 'inscription':
                    cntInscription += 1
                if slot.type == 'player':
                    cntPlayer += 1
        try:
            vDesc.hull['emblemSlots'] = []
            vDesc.turret['emblemSlots'] = []
            for part in ('hull', 'turret'):
                for slot in data[part]['emblemSlots']:
                    if slot.type in ('player', 'inscription', 'clan'):
                        getattr(vDesc, part)['emblemSlots'].append(slot)
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
            for i in range(len(part['emblemSlots'])):
                part['emblemSlots'][i] = part['emblemSlots'][i]._replace(size=0.001)

    exclMask = data['common']['camouflage']['exclusionMask']
    vDesc.type.camouflageExclusionMask = exclMask
    if exclMask:
        vDesc.type.camouflageTiling = data['common']['camouflage']['tiling']
    for partName in ('hull', 'gun', 'turret'):
        camoData = data[partName]['camouflage']
        exclMask = camoData['exclusionMask']
        if exclMask:
            part = getattr(vDesc, partName)
            part['camouflageExclusionMask'] = exclMask
            part['camouflageTiling'] = camoData['tiling']
    exhaust = data['hull']['exhaust']
    for effectDesc in vDesc.hull['customEffects']:
        if exhaust['nodes']:
            effectDesc.nodes[:] = exhaust['nodes']
        effectDesc._selectorDesc = g_cache._customEffects['exhaust'].get(exhaust['pixie'], effectDesc._selectorDesc)
    for partName in ('chassis', 'engine'):
        for key in ('wwsoundPC', 'wwsoundNPC'):
            part = getattr(vDesc, partName)
            soundID = data[partName][key]
            if soundID:
                part[key] = soundID

