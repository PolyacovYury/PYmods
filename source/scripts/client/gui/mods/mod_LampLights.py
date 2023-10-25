# -*- coding: utf-8 -*-
import BigWorld
import Keys
import Math
import os
import traceback
from Avatar import PlayerAvatar
from OpenModsCore import (
    BigWorld_callback, SimpleConfigInterface, overrideMethod, checkKeys, sendPanelMessage, Analytics, events,
)
from OpenModsCore.config import smart_update
from Vehicle import Vehicle
from gui import SystemMessages
from math import copysign
from math_utils import createTranslationMatrix, createRotationMatrix, MatrixProviders as MP
from vehicle_systems.CompoundAppearance import CompoundAppearance
from vehicle_systems.tankStructure import TankNodeNames as TankNodes, TankPartNames as TankParts


class ConfigInterface(SimpleConfigInterface):
    listToTuple = classmethod(lambda cls, seq: seq if not isinstance(seq, list) else tuple(cls.listToTuple(x) for x in seq))

    def __init__(self):
        self.teams = ('player', 'platoon', 'ally', 'enemy')
        self.lampsMeta = {}
        self.lampsData = {}
        self.lampsStorage = {}
        self.fakeModelsStorage = {}
        self.speedsStorage = {}
        self.lampsVisible = True
        self.tickRequired = True
        self.isLogin = True
        super(ConfigInterface, self).__init__()

    def init(self):
        self.ID = '%(mod_ID)s'
        self.version = '3.0.0 (%(file_compile_date)s)'
        self.author = 'by Polyacov_Yury'
        self.modsGroup = 'PYmods'
        self.modSettingsID = 'PYmodsGUI'
        self.defaultKeys = {'hotkey': [Keys.KEY_F12]}
        self.data = {
            'enabled': True, 'enableAtStartup': True, 'hotkey': self.defaultKeys['hotkey'], 'enableMessage': True,
            'Debug': False, 'DebugModel': False, 'DebugPath': '',
        }
        self.i18n = {
            'UI_description': 'Lamp Lights Enabler',
            'UI_activLamps': 'Lamps ENABLED',
            'UI_deactivLamps': 'Lamps DISABLED',
            'UI_setting_enableAtStartup_text': 'Lamps are enabled by default',
            'UI_setting_enableAtStartup_tooltip': 'Lamp lights will be added after battle loads.',
            'UI_setting_hotkey_text': 'LampLights hotkey',
            'UI_setting_hotkey_tooltip': 'Pressing this button in-battle toggles lamps on/off.',
            'UI_setting_enableMessage_text': 'Enable service channel message',
            'UI_setting_enableMessage_tooltip': (
                'This allows the mod to send a notification to service channel in no-GUI mode.'),
            'UI_setting_caps_text': 'Total configs loaded: {totalCfg}, light sources: {totalSrc}, models: {models}',
            'UI_setting_meta_text': 'Loaded configs:',
            'UI_setting_meta_tooltip': '%(meta)s',
            'UI_setting_meta_no_configs': 'No configs were loaded.',
            'UI_setting_meta_NDA': '{attachTo} • No data available or provided.',
            'UI_setting_meta_AND': ' and ',
            'UI_serviceChannelPopUp': '<b>{author}<font color="#cc9933"> brought some light!</font></b>'}
        super(ConfigInterface, self).init()

    def createTemplate(self):
        models = sum(1 for v in self.lampsData.values() if 'model' in v['type'])
        cntLabel = self.tb.createLabel('meta')
        cntLabel['text'] = self.tb.getLabel('caps').format(
            totalCfg=len(self.lampsMeta), totalSrc=len(self.lampsData) - models, models=models)
        cntLabel['tooltip'] %= {'meta': '\n'.join(
            ['\n'.join((self.lampsMeta[fileName]['name'], self.lampsMeta[fileName]['desc'].format(attachTo=''))).rstrip()
             for fileName in sorted(self.lampsMeta.keys(), key=str.lower)]
        ) or self.i18n['UI_setting_meta_no_configs']}
        return {'modDisplayName': self.i18n['UI_description'],
                'enabled': self.data['enabled'],
                'column1': [self.tb.createControl('enableAtStartup'),
                            cntLabel],
                'column2': [self.tb.createHotKey('hotkey'),
                            self.tb.createControl('enableMessage')]}

    def onApplySettings(self, settings):
        super(ConfigInterface, self).onApplySettings(settings)
        self.lampsVisible = self.data['enabled'] and self.data['enableAtStartup'] and self.lampsVisible

    def onReadConfig(self, quiet, dir_path, name, json_data, sub_dirs, names):
        if not dir_path:
            names[:] = []
            return
        if '/' not in dir_path and name == '_meta':
            if self.data['Debug']:
                print self.LOG, 'loading', dir_path + ':'
            self.lampsMeta[dir_path] = meta = {'name': '<b>%s</b>' % dir_path, 'desc': self.i18n['UI_setting_meta_NDA']}
            lang = self.lang
            if lang not in json_data:
                lang = 'en'
            smart_update(meta, json_data.get(lang, {}))
            return
        if dir_path.partition('/')[0] not in self.lampsMeta:
            sub_dirs[:] = []
            names[:] = []
            return
        if not self.readLampConfig(quiet, dir_path, name, json_data) and name in sub_dirs:
            sub_dirs.remove(name)

    def readLampConfig(self, quiet, dir_path, name, json_data):
        confID = dir_path + '/' + name
        settings = {team: json_data.get(team, True) for team in self.teams}
        settings.update({k: json_data.get(k, []) for k in ('include', 'exclude')})
        parentID = dir_path
        while parentID.count('/') > 1:
            for team in self.teams:
                settings[team] &= self.lampsData[parentID][team]
            for k in ('include', 'exclude'):
                settings[k] += self.lampsData[parentID][k]
            parentID = os.path.dirname(parentID)
        if not any(settings[team] for team in self.teams) and not quiet:
            print self.LOG, confID, 'disabled'
            return False
        if self.data['Debug']:
            print self.LOG, 'loading', confID
        if json_data['type'] == 'model':
            try:
                BigWorld.Model(json_data['path'])
            except StandardError:
                print self.LOG, confID, 'model path incorrect:', json_data['path']
                return False
        elif json_data['type'] not in ('omniLight', 'spotLight'):
            print self.LOG, confID, 'unknown type:', json_data['type']
            return False
        root = json_data['root']
        if confID.count('/') > 1:
            try:
                BigWorld.Model(self.lampsData[os.path.dirname(confID)]['path']).node(root)
            except ValueError:
                print self.LOG, confID, 'unknown root:', root
                return False
        elif root not in (
                'front_left', 'front_right', 'back_left', 'back_right', 'wheels_left', 'wheels_right', 'roof', 'hull',
                'spot', 'collide_front_left', 'collide_front_right', 'collide_back_left', 'collide_back_right'):
            print self.LOG, confID, 'unknown root:', root
            return False
        if json_data['mode'] not in ('constant', 'stop', 'turn_left', 'turn_right', 'back', 'target', 'spot'):
            print self.LOG, confID, 'unknown mode:', json_data['mode']
            return False
        keys = ('type', 'root', 'mode', 'preRotate', 'postRotate', 'position')
        if json_data['type'] == 'model':
            keys += ('path',)
        else:
            keys += ('colour', 'multiplier', 'innerRadius', 'outerRadius', 'castShadows')
            if json_data['type'] == 'spotLight':
                keys += ('coneAngle',)
        self.lampsData[confID] = dict(settings, **{k: self.listToTuple(json_data[k]) for k in keys})
        if self.data['Debug'] and not quiet:
            print self.LOG, confID, 'loaded'
        return True

    def readCurrentSettings(self, quiet=True):
        self.lampsData.clear(), self.lampsMeta.clear()
        if self.data['DebugModel']:
            if not self.data['DebugPath']:
                print self.LOG, 'debug model disabled due to absence of DebugPath.'
                self.data['DebugModel'] = False
            else:
                try:
                    _ = BigWorld.Model(self.data['DebugPath'])
                except StandardError:
                    print self.LOG, 'debug model path incorrect:', self.data['DebugPath']
                    self.data['DebugModel'] = False
        if not self.data['enabled']:
            if not quiet:
                print self.LOG, 'mod fully disabled via main config'
            self.lampsVisible = False
            self.tickRequired = False
            return
        self.readConfigDir(quiet, recursive=True)
        if not self.lampsData:
            print self.LOG, 'no configs loaded. Are you sure that you need this mod?'
        elif self.data['DebugModel']:
            if self.data['Debug'] and not quiet:
                print self.LOG, 'loading configs for Debug:'
            for confID, data in self.lampsData.items():
                newID = confID + 'Debug'
                if newID in self.lampsData:
                    if not quiet:
                        print self.LOG, 'debug assignment failed:', newID
                    continue
                if 'model' in data['type']:
                    continue
                self.lampsData[newID] = new_data = {}
                new_data['type'] = 'model'
                for key in ('root', 'preRotate', 'postRotate', 'position', 'mode', 'include', 'exclude') + self.teams:
                    new_data[key] = data[key]
                new_data['path'] = self.data['DebugPath']
                if self.data['Debug'] and not quiet:
                    print self.LOG, newID, 'loaded'
        self.tickRequired = any(v['mode'] in ('stop', 'turn_left', 'turn_right', 'back') for v in self.lampsData.values())

    def onHotkeyPressed(self, event):
        if (not hasattr(BigWorld.player(), 'arena') or not self.data['enabled']
                or not checkKeys(self.data['hotkey'], event.key) or not event.isKeyDown()):
            return
        self.lampsVisible = not self.lampsVisible
        if self.lampsVisible:
            sendPanelMessage(self.i18n['UI_activLamps'])
            self.readData(not self.data['Debug'])
            self.readCurrentSettings(not self.data['Debug'])
            for vehicleID in BigWorld.player().arena.vehicles:
                vEntity = BigWorld.entity(vehicleID)
                if vEntity is not None and vEntity.isAlive():
                    createLamps(vehicleID, 'keyPress')
        else:
            sendPanelMessage(self.i18n['UI_deactivLamps'], 'Red')
            for vehicleID in self.lampsStorage.keys():
                destroyLamps(vehicleID, 'keyPress')

    def load(self):
        super(ConfigInterface, self).load()
        if not self.data['enableMessage']:
            return
        LOGIN_TEXT_MESSAGE = self.i18n['UI_serviceChannelPopUp'].format(author='<font color="#DD7700">Polyacov_Yury</font>')

        @events.LobbyView.populate.after
        def new_Lobby_populate(*_, **__):
            isRegistered = self.ID in getattr(self.MSAInstance, 'activeMods', ())
            if self.isLogin and not isRegistered:
                SystemMessages.pushMessage(LOGIN_TEXT_MESSAGE, type=SystemMessages.SM_TYPE.Information)
                self.isLogin = False


g_config = ConfigInterface()
statistic_mod = Analytics(g_config.ID, g_config.version, 'UA-76792179-2', g_config.lampsData)
createFakeModel = lambda: BigWorld.Model('objects/fake_model.model')


def matrixFromNode(model, rootMatrix, nodeName):
    node = model.node(nodeName)
    if node is None:
        return
    return createTranslationMatrix(rootMatrix.applyPoint(node.position))


def findWheelNodes(model, invertedHullMatrix):
    result = {'L': {}, 'R': {}}
    for side, nodes in result.items():
        for template in ('W_' + side, 'WD_' + side):
            wheelsCount = 0
            while wheelsCount < 40:  # pretty reasonable assumption, no?
                nodeName = template + str(wheelsCount)
                if g_config.data['Debug']:
                    print g_config.LOG, 'looking for wheel:', nodeName
                node = matrixFromNode(model, invertedHullMatrix, nodeName)
                if node is None:
                    if g_config.data['Debug']:
                        print g_config.LOG, 'wheel not found, stopping'
                    break
                if node.translation.lengthSquared < 0.1:  # that happened, yes
                    if g_config.data['Debug']:
                        print g_config.LOG, 'wheel matrix is at the center of the vehicle, stopping'
                    break
                if g_config.data['Debug']:
                    print g_config.LOG, 'wheel found:', node
                nodes[nodeName] = node
                wheelsCount += 1
    return result


def computeTransform(data):
    keys = ('preRotate', 'postRotate', 'position')
    if not any(isinstance(data[key][0], tuple) for key in keys):
        matrix = createTranslationMatrix(data['position'])
        matrix.postMultiply(createRotationMatrix(data['postRotate']))
        matrix.preMultiply(createRotationMatrix(data['preRotate']))
        return matrix
    matrices = {}
    for key in keys:
        createMatrix = createTranslationMatrix if key == 'position' else createRotationMatrix
        frames = data[key]
        if not isinstance(frames[0], tuple):
            matrices[key] = createMatrix(frames)
            continue
        matrices[key] = anim = Math.MatrixAnimation()
        anim.keyframes = map(lambda x: (x[0], createMatrix(x[1])), frames)
        anim.time = 0.0
        anim.loop = True
    return MP.product(matrices['preRotate'], MP.product(matrices['position'], matrices['postRotate']))


def createLamps(vehicleID, caller, count=20):
    try:
        vEntity = BigWorld.entity(vehicleID)
        if vEntity is None:
            return
        pos = vEntity.position
        if not BigWorld.wg_collideDynamic(vEntity.spaceID, pos - Math.Vector3(0, 10, 0), pos + Math.Vector3(0, 10, 0), 0, -1):
            if g_config.data['Debug']:
                print g_config.LOG, 'user does not see world yet, rescheduling lamps creation for', vehicleID
            if count:
                BigWorld_callback(0.1, createLamps, vehicleID, 'Vehicle.startVisual.rescheduled', count - 1)
            else:
                print g_config.LOG, 'lamps creation for', vehicleID, 'cancelled'
            return
        wheelNodes = buildSkeleton(vehicleID, vEntity, caller)
        applyLamps(vehicleID, vEntity, wheelNodes, caller)
    except StandardError:
        print g_config.LOG, 'create: error in', caller
        traceback.print_exc()


def buildSkeleton(vehicleID, vEntity, caller):
    if g_config.data['Debug']:
        print g_config.LOG, 'call from', caller, 'started building skeleton for', vehicleID
    g_config.fakeModelsStorage[vehicleID] = fakeModels = {}
    vDesc = vEntity.typeDescriptor
    compoundModel = vEntity.model
    invertedEntityMatrix = Math.Matrix()
    invertedEntityMatrix.set(vEntity.matrix)
    invertedEntityMatrix.invert()
    localHullMatrix = matrixFromNode(compoundModel, invertedEntityMatrix, TankParts.HULL)
    invertedHullMatrix = Math.Matrix()
    invertedHullMatrix.set(localHullMatrix)
    invertedHullMatrix.invert()
    invertedHullMatrix.preMultiply(invertedEntityMatrix)
    globalHullMatrix = Math.Matrix()
    globalHullMatrix.set(invertedHullMatrix)
    globalHullMatrix.invert()
    if g_config.data['Debug']:
        print g_config.LOG, 'calculated matrices'

    for partName in (TankParts.HULL, TankParts.GUN):
        fakeModels[partName] = part = createFakeModel()
        compoundModel.node(partName).attach(part)
        if g_config.data['Debug']:
            print g_config.LOG, 'created', partName
    hullRoot = fakeModels[TankParts.HULL]

    if g_config.data['Debug']:
        print g_config.LOG, 'looking for wheels'
    wheelNodes = findWheelNodes(compoundModel, invertedHullMatrix)
    if g_config.data['Debug']:
        print g_config.LOG, 'found wheels'
    for nodes in wheelNodes.values():
        for nodeName, node in nodes.items():
            fakeModels[nodeName] = wheel = createFakeModel()
            hullRoot.node('', node).attach(wheel)

    chassis_bbox_min, chassis_bbox_max, _ = vDesc.chassis.hitTester.bbox
    hull_bbox_min, hull_bbox_max, _ = vDesc.hull.hitTester.bbox
    turret_pos_on_hull = vDesc.hull.turretPositions[0]
    turret_bbox_max = vDesc.turret.hitTester.bbox[1]
    gun_pos_on_turret = vDesc.turret.gunPosition
    gun_pos_on_hull = gun_pos_on_turret + turret_pos_on_hull
    gun_bbox_max = vDesc.gun.hitTester.bbox[1]

    hullLocalCenterY = (hull_bbox_min.y + hull_bbox_max.y) / 2.0
    hullLocalCenterZ = (hull_bbox_min.z + hull_bbox_max.z) / 2.0
    visionNodes = {
        'hullLocalPt1': Math.Vector3(0.0, hullLocalCenterY, hull_bbox_max.z),
        'hullLocalPt2': Math.Vector3(0.0, hullLocalCenterY, hull_bbox_min.z),
        'hullLocalPt3': Math.Vector3(hull_bbox_max.x, gun_pos_on_hull.y, hullLocalCenterZ),
        'hullLocalPt4': Math.Vector3(hull_bbox_min.x, gun_pos_on_hull.y, hullLocalCenterZ),
        'hullGunLocal': gun_pos_on_hull}
    for nodeName, node in visionNodes.items():
        fakeModels[nodeName] = visionPoint = createFakeModel()
        hullRoot.node('', createTranslationMatrix(node)).attach(visionPoint)

    if hull_bbox_max.y >= turret_pos_on_hull.y + turret_bbox_max.y:
        top_pos = Math.Vector3(0, hull_bbox_max.y, 0)
        topNodeName = TankParts.HULL
    elif gun_pos_on_turret.y + gun_bbox_max.y >= turret_bbox_max.y:
        top_pos = Math.Vector3(0, gun_bbox_max.y, 0)
        topNodeName = TankNodes.GUN_INCLINATION
    else:
        top_pos = Math.Vector3(0, turret_bbox_max.y, 0)
        topNodeName = TankParts.TURRET
    fakeModels['roof'] = roofModel = createFakeModel()
    fakeModels['roofRoot'] = roofRootModel = createFakeModel()
    compoundModel.node(topNodeName).attach(roofRootModel)  # compoundModels' nodes are not to be messed with
    roofRootModel.node('', createTranslationMatrix(top_pos)).attach(roofModel)

    vehicle_width = max(chassis_bbox_max.x - chassis_bbox_min.x, hull_bbox_max.x - hull_bbox_min.x)
    off_front, off_back = hull_bbox_max.z, hull_bbox_min.z
    off_side = 0.2 * vehicle_width

    for nodeName, x, z in (
            (TankNodes.TRACK_LEFT_UP_FRONT, -off_side, off_front), (TankNodes.TRACK_RIGHT_UP_FRONT, off_side, off_front),
            (TankNodes.TRACK_LEFT_UP_REAR, -off_side, off_back), (TankNodes.TRACK_RIGHT_UP_REAR, off_side, off_back)):
        fakeModels[nodeName] = corner = createFakeModel()
        z_sign = copysign(1, z)
        cornerMatrix = matrixFromNode(compoundModel, invertedHullMatrix, nodeName)
        if cornerMatrix is None:
            cornerMatrix = matrixFromNode(compoundModel, invertedHullMatrix, nodeName.replace('Up', ''))
        if cornerMatrix is None:  # wheeled
            wheel_nodes = wheelNodes[('L', 'R')[x > 0]].values()
            if wheel_nodes:
                wheel_center = max(wheel_nodes, key=lambda m: m.translation.z * z_sign)
                offset = (localHullMatrix.translation.y + wheel_center.translation.y) / (2 ** 0.5)
                cornerMatrix = createTranslationMatrix(wheel_center.translation + Math.Vector3(0, offset, offset * z_sign))
            else:
                cornerMatrix = createTranslationMatrix((x, 0, z))
        hullRoot.node('', cornerMatrix).attach(corner)

        fakeModels['collide_' + nodeName] = collide = createFakeModel()
        corner_y, corner_z = cornerMatrix.translation.y - 0.1 * z_sign, cornerMatrix.translation.z - 0.1 * z_sign
        y_variants = (corner_y, 0.0)
        if topNodeName == TankParts.HULL:
            y_variants += (hullLocalCenterY,)
        for y in y_variants:
            start = globalHullMatrix.applyPoint(Math.Vector3(x, y, z + 2 * z_sign))  # Strv S1
            endAt = globalHullMatrix.applyPoint(Math.Vector3(x, y, z - 2 * z_sign))  # T28
            collision = BigWorld.wg_collideDynamic(vEntity.spaceID, start, endAt, 0, -1)
            if collision is None:
                continue
            localCollision = (x, y, z - (collision[0] - 2) * z_sign)
            hullRoot.node('', createTranslationMatrix(localCollision)).attach(collide)
            break
        else:  # T92 HMC has no behind
            if g_config.data['Debug']:
                print g_config.LOG, 'error calculating collide point', nodeName, 'in', caller, 'for', vehicleID
            hullRoot.node('', createTranslationMatrix((x, corner_y, corner_z))).attach(collide)
    return wheelNodes


def applyLamps(vehicleID, vEntity, wheelNodes, caller):
    vName = vEntity.typeDescriptor.name
    ctx = BigWorld.player().guiSessionProvider.getCtx()
    lamps = g_config.lampsStorage.setdefault(vehicleID, {})
    fakeModels = g_config.fakeModelsStorage[vehicleID]
    nodesForRoot = {
        'front_left': (TankNodes.TRACK_LEFT_UP_FRONT,), 'front_right': (TankNodes.TRACK_RIGHT_UP_FRONT,),
        'back_left': (TankNodes.TRACK_LEFT_UP_REAR,), 'back_right': (TankNodes.TRACK_RIGHT_UP_REAR,),
        'collide_front_left': ('collide_' + TankNodes.TRACK_LEFT_UP_FRONT,),
        'collide_front_right': ('collide_' + TankNodes.TRACK_RIGHT_UP_FRONT,),
        'collide_back_left': ('collide_' + TankNodes.TRACK_LEFT_UP_REAR,),
        'collide_back_right': ('collide_' + TankNodes.TRACK_RIGHT_UP_REAR,),
        'wheels_left': wheelNodes['L'].keys(), 'wheels_right': wheelNodes['R'].keys(),
        'roof': ('roof',), 'hull': (TankParts.HULL,),
        'spot': ('roof', TankParts.GUN, 'hullGunLocal') + tuple('hullLocalPt%s' % num for num in xrange(1, 5)),
    }
    for name, data in sorted(g_config.lampsData.items(), key=lambda x: x[0]):
        try:
            if not (data['player'] if ctx.isCurrentPlayer(vehicleID) else
                    (data['platoon'] if ctx.isSquadMan(vehicleID) else
                    (data['ally'] if ctx.isAlly(vehicleID) else data['enemy']))):
                continue
            include, exclude = data['include'], data['exclude']
            if include and vName not in include or exclude and vName in exclude:
                continue
            nodes = nodesForRoot[data['root']] if name.count('/') == 1 else (data['root'],)
            parents = name.split('/')[:-1]
            names = []
            for existing in lamps.keys():
                other_parents = existing.split('/')
                if len(parents) != len(other_parents) or any(
                        parentName != other_parents[depth].partition(':')[0] for depth, parentName in enumerate(parents)):
                    continue
                names.append(existing + '/' + name.split('/')[-1])
            if not names:
                names = [name]
            for fullName in names:
                for nodeName in nodes:
                    fullNameWithNode = fullName
                    parentNode = nodeName
                    isRoot = fullNameWithNode.count('/') == 1
                    if not isRoot:
                        parent, _, tail = fullNameWithNode.rpartition('/')
                        parentNode = parent + ':' + nodeName
                        fullNameWithNode = parentNode + '/' + tail
                    elif len(nodes) != 1:
                        fullNameWithNode += ':' + nodeName
                    if parentNode not in fakeModels:  # implies `not isRoot`
                        fakeModels[parentNode] = parentModel = createFakeModel()
                        lamps[parentNode.rpartition(':')[0]][0].node(nodeName).attach(parentModel)
                    if g_config.data['Debug']:
                        print g_config.LOG, 'creating', fullNameWithNode, 'for', vName, 'with ID', vehicleID
                    fakeNode = fakeModels[parentNode].node('', computeTransform(data))
                    lamp = buildLamp(data, fakeNode)
                    setLampVisible(lamp, g_config.lampsVisible and data['mode'] == 'constant')
                    lamps[fullNameWithNode] = (lamp, data['mode'])

        except StandardError:
            print g_config.LOG, 'error in', caller, 'while processing', name, 'for', vName
            traceback.print_exc()


def buildLamp(data, node):
    if data['type'] == 'model':
        lamp = BigWorld.Model(data['path'])
        node.attach(lamp)
        return lamp
    keys = ('innerRadius', 'outerRadius', 'castShadows', 'multiplier')
    if data['type'] == 'spotLight':
        lamp = BigWorld.PySpotLight()
        keys += ('coneAngle',)
    else:
        lamp = BigWorld.PyOmniLight()
    for k in keys:
        setattr(lamp, k, data[k])
    lamp.source = node
    if data['type'] == 'spotLight':
        return lamp
    colour_data = data['colour']
    if not isinstance(data['colour'][0], tuple):
        colour_data = [(0.0, colour_data)]
    colorAnimator = Math.Vector4Animation()
    colorAnimator.keyframes = [(ts, Math.Vector4(clr)) for ts, clr in colour_data]
    colorAnimator.duration = colour_data[-1][0]
    lamp.colorAnimator = colorAnimator
    return lamp


def setLampVisible(lamp, visible):
    if isinstance(lamp, BigWorld.Model):
        lamp.visible = visible
    elif visible and lamp.multiplier <= 1:
        lamp.multiplier *= 10000
    elif not visible and lamp.multiplier > 1:
        lamp.multiplier *= 0.0001


def destroyLamps(vehicleID, caller=''):
    try:
        lamps = g_config.lampsStorage.pop(vehicleID, {})
        for (lamp, _) in lamps.values():
            setLampVisible(lamp, False)
            if not isinstance(lamp, BigWorld.Model):
                lamp.destroyLight()
        g_config.fakeModelsStorage.pop(vehicleID, None)
        g_config.speedsStorage.pop(vehicleID, None)
    except StandardError:
        print g_config.LOG, 'destroy: error in', caller
        traceback.print_exc()


@overrideMethod(Vehicle, 'startVisual')
def new_startVisual(base, self, *a, **k):
    base(self, *a, **k)
    if self.isStarted and self.isAlive() and g_config.data['enabled'] and g_config.lampsVisible:
        BigWorld_callback(0.1, createLamps, self.id, 'Vehicle.startVisual')


@overrideMethod(Vehicle, 'stopVisual')
def new_stopVisual(base, self, *a, **k):
    if self.isStarted:
        destroyLamps(self.id, 'Vehicle.stopVisual')
    base(self, *a, **k)


@overrideMethod(PlayerAvatar, 'leaveArena')
def new_leaveArena(base, *a, **k):
    for vehID in g_config.lampsStorage.keys():
        destroyLamps(vehID, 'Avatar.leaveArena')
    base(*a, **k)


@overrideMethod(CompoundAppearance, 'onVehicleHealthChanged')
def new_oVHC(base, self, *a, **k):
    if not self._vehicle.isAlive():
        destroyLamps(self._vehicle.id, 'onVehicleHealthChanged')
    base(self, *a, **k)


@overrideMethod(CompoundAppearance, '_periodicUpdate')
def new_periodicUpdate(base, self, *a, **k):
    base(self, *a, **k)
    if self._vehicle is None or not g_config.data['enabled'] or not g_config.lampsVisible or not g_config.tickRequired:
        return
    vehicleID = self._vehicle.id
    lamps = g_config.lampsStorage.get(vehicleID)
    if lamps is None:
        return
    speeds = g_config.speedsStorage.setdefault(vehicleID, {})
    old_speed = speeds.setdefault('speed', 0.0)
    speedInfo = self._vehicle.filter.speedInfo.value
    speeds['speed'] = speed = round(speedInfo[0], 1)
    speeds['rSpeed'] = rSpeed = round(speedInfo[1], 1)
    visibleModes = {
        'back': speed < 0,
        'turn_left': rSpeed != 0 and ((rSpeed > 0) != (speed >= 0)),
        'turn_right': rSpeed != 0 and ((rSpeed > 0) == (speed >= 0)),
        'stop': abs(old_speed) - abs(speed) > 0.6}
    for (lamp, mode) in lamps.values():
        if mode in visibleModes:
            setLampVisible(lamp, visibleModes[mode])


def spotToggle(vehicleID, lightIdx, visible):
    if not g_config.lampsVisible:
        return
    lamps = g_config.lampsStorage.get(vehicleID)
    if lamps is None:
        return
    nodes = ('roof', TankParts.GUN) + tuple('hullLocalPt%s' % num for num in xrange(1, 5)) + ('hullGunLocal',)
    for fullName, (lamp, mode) in lamps.items():
        if mode != 'spot':
            continue
        node = fullName.split('/')[1].split(':')[1]
        if nodes[lightIdx] != node:
            continue
        setLampVisible(lamp, visible if not isinstance(lamp, BigWorld.Model) or lightIdx not in (1, 6) else False)


@overrideMethod(PlayerAvatar, 'targetFocus')
def new_targetFocus(base, self, entity, *a, **k):
    base(self, entity, *a, **k)
    if not g_config.lampsVisible or entity not in self._PlayerAvatar__vehicles:
        return
    for vehicleID, lamps in g_config.lampsStorage.items():
        for (lamp, mode) in lamps.values():
            if mode == 'target':
                setLampVisible(lamp, vehicleID == entity.id)


@overrideMethod(PlayerAvatar, 'targetBlur')
def new_targetBlur(base, self, prevEntity, *a, **k):
    base(self, prevEntity, *a, **k)
    if not g_config.lampsVisible or prevEntity not in self._PlayerAvatar__vehicles:
        return
    for lamps in g_config.lampsStorage.values():
        for (lamp, mode) in lamps.values():
            if mode == 'target':
                setLampVisible(lamp, False)
