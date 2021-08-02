from items import _xml, vehicles
from items.components import chassis_components, component_constants, shared_components
from items.readers import chassis_readers, gun_readers, shared_readers
from .common import getOrigItem, readCamouflage, readEmblemSlots, readModels


def readEngine(xmlCtx, section, item):  # readChassis is last because it's huge
    pickFrom = getOrigItem(xmlCtx, section, 'engine')
    if pickFrom is not None:
        item.sounds = pickFrom.sounds


def readHull(xmlCtx, section, item):
    readModels(xmlCtx, section, item)
    readEmblemSlots(xmlCtx, section, item)
    readCamouflage(xmlCtx, section, item)
    item.AODecals = vehicles._readAODecals(xmlCtx, section, 'AODecals')
    if section.has_key('hangarShadowTexture'):
        item.hangarShadowTexture = _xml.readString(xmlCtx, section, 'hangarShadowTexture')
    if section.readString('exhaust/pixie'):
        item.customEffects = (vehicles.__readExhaustEffect(xmlCtx, section),)
    else:
        item.customEffects = ([intern(node) for node in _xml.readNonEmptyString(xmlCtx, section, 'exhaust/nodes').split()],)


def readTurret(xmlCtx, section, item):
    if section.has_key('multiGun'):
        item.multiGun = vehicles._readMultiGun(xmlCtx, section, 'multiGun')
    item.showEmblemsOnGun = section.readBool('showEmblemsOnGun', False)
    readModels(xmlCtx, section, item)
    readEmblemSlots(xmlCtx, section, item)
    readCamouflage(xmlCtx, section, item)
    item.AODecals = vehicles._readAODecals(xmlCtx, section, 'AODecals')
    pickFrom = getOrigItem(xmlCtx, section, 'turret')
    if pickFrom is not None:
        item.ceilless = pickFrom.ceilless
        item.turretRotatorSoundManual = pickFrom.turretRotatorSoundManual
        item.turretDetachmentEffects = pickFrom.turretDetachmentEffects
        return
    item.ceilless = section.readBool('ceilless', False)
    if section.has_key('wwturretRotatorSoundManual'):
        item.turretRotatorSoundManual = _xml.readString(xmlCtx, section, 'wwturretRotatorSoundManual')
    if section.has_key('turretDetachmentEffects'):
        item.turretDetachmentEffects = vehicles._readTurretDetachmentEffects(
            xmlCtx, section, 'turretDetachmentEffects', vehicles.g_cache.commonConfig['defaultTurretDetachmentEffects'])


def readGun(xmlCtx, section, item):
    readModels(xmlCtx, section, item)
    readEmblemSlots(xmlCtx, section, item)
    readCamouflage(xmlCtx, section, item)
    item.animateEmblemSlots = section.readBool('animateEmblemSlots', True)
    if section.has_key('drivenJoints'):
        item.drivenJoints = vehicles._readDrivenJoints(xmlCtx, section, 'drivenJoints')
    pickFrom = getOrigItem(xmlCtx, section, 'gun')
    if pickFrom is not None:
        item.effects = pickFrom.effects
        item.reloadEffect = pickFrom.reloadEffect
        item.impulse = pickFrom.impulse
        item.recoil = pickFrom.recoil
        return
    if section.has_key('effects'):
        effName = _xml.readNonEmptyString(xmlCtx, section, 'effects')
        eff = vehicles.g_cache._gunEffects.get(effName)
        if eff is None:
            _xml.raiseWrongXml(xmlCtx, 'effects', "unknown effect '%s'" % effName)
        item.effects = eff
    effName = _xml.readStringOrNone(xmlCtx, section, 'reloadEffect')
    if effName is not None:
        reloadEff = vehicles.g_cache._gunReloadEffects.get(effName, None)
        if reloadEff is None:
            _xml.raiseWrongXml(xmlCtx, 'effects', "unknown reload effect '%s'" % effName)
        item.reloadEffect = reloadEff
    if section.has_key('impulse'):
        item.impulse = _xml.readNonNegativeFloat(xmlCtx, section, 'impulse')
    if section.has_key('recoil'):
        item.recoil = gun_readers.readRecoilEffect(xmlCtx, section, vehicles.g_cache)


def readChassis(xmlCtx, section, item):  # told ya
    import Vehicular
    readModels(xmlCtx, section, item)
    readEmblemSlots(xmlCtx, section, item)
    readCamouflage(xmlCtx, section, item)
    item.hullPosition = _xml.readVector3(xmlCtx, section, 'hullPosition')
    item.topRightCarryingPoint = _xml.readPositiveVector2(xmlCtx, section, 'topRightCarryingPoint')
    drivingWheelNames = section.readString('drivingWheels').split()
    if len(drivingWheelNames) != 2:
        _xml.raiseWrongSection(xmlCtx, 'drivingWheels')
    frontWheelSize = None
    rearWheelSize = None
    if _xml.readBool(xmlCtx, section, 'wheels/generalWheels', False):
        item.generalWheelsAnimatorConfig = Vehicular.GeneralWheelsAnimatorConfig(section)
        radius = item.generalWheelsAnimatorConfig.getRadius(drivingWheelNames[0])
        frontWheelSize = radius * vehicles.WHEEL_SIZE_COEF
        radius = item.generalWheelsAnimatorConfig.getRadius(drivingWheelNames[1])
        rearWheelSize = radius * vehicles.WHEEL_SIZE_COEF
    if frontWheelSize is None:
        wheelGroups, wheels = chassis_readers.readWheelsAndGroups(xmlCtx, section)
        for wheel in wheels:
            if wheel.nodeName == drivingWheelNames[0]:
                frontWheelSize = wheel.radius * vehicles.WHEEL_SIZE_COEF
            if wheel.nodeName == drivingWheelNames[1]:
                rearWheelSize = wheel.radius * vehicles.WHEEL_SIZE_COEF
            if frontWheelSize is not None and rearWheelSize is not None:
                break
        else:
            _xml.raiseWrongXml(xmlCtx, 'drivingWheels', 'unknown wheel name(s)')

        item.wheels = chassis_components.WheelsConfig(wheelGroups, wheels)

    item.drivingWheelsSizes = (frontWheelSize, rearWheelSize)
    item.traces = chassis_readers.readTraces(xmlCtx, section, item.topRightCarryingPoint[0], vehicles.g_cache)
    item.tracks = chassis_readers.readTrackBasicParams(xmlCtx, section, vehicles.g_cache)
    groundGroups, groundNodes, groundNodesActivePostmortem, lodSettings = chassis_readers.readGroundNodesAndGroups(
        xmlCtx, section, vehicles.g_cache)
    item.groundNodes = shared_components.NodesAndGroups(
        nodes=groundNodes, groups=groundGroups, activePostmortem=groundNodesActivePostmortem, lodSettings=lodSettings)
    item.trackNodes = shared_components.NodesAndGroups(
        nodes=chassis_readers.readTrackNodes(xmlCtx, section), groups=component_constants.EMPTY_TUPLE,
        activePostmortem=False, lodSettings=None)
    item.trackSplineParams = chassis_readers.readTrackSplineParams(xmlCtx, section)
    item.splineDesc = chassis_readers.readSplineConfig(xmlCtx, section, vehicles.g_cache)
    item.leveredSuspension = chassis_readers.readLeveredSuspension(xmlCtx, section, vehicles.g_cache)
    item.physicalTracks = physicalTracksDict = {}
    physicalTracksSection = section['physicalTracks']
    for k in ('left', 'right') if physicalTracksSection is not None else ():
        physicalTracksDict[k] = shared_readers.readBuilders(xmlCtx, physicalTracksSection, k, Vehicular.PhysicalTrackBuilder)
    item.chassisLodDistance = shared_readers.readLodDist(xmlCtx, section, 'wheels/lodDist', vehicles.g_cache)
    item.AODecals = vehicles._readAODecals(xmlCtx, section, 'AODecals')
    pickFrom = getOrigItem(xmlCtx, section, 'chassis')
    if pickFrom is None:
        return
    item.sounds = pickFrom.sounds
    item.hullAimingSound = pickFrom.hullAimingSound
    item.effects = pickFrom.effects
    item.customEffects = pickFrom.customEffects
