# -*- coding: utf-8 -*-
import cProfile
import glob
import os
import traceback
from functools import partial

import BigWorld
import Math
import ResMgr

import Keys
import PYmodsCore
from Avatar import PlayerAvatar
from AvatarInputHandler import mathUtils
from Vehicle import Vehicle
from VehicleGunRotator import VehicleGunRotator as VGR
from debug_utils import LOG_ERROR, LOG_NOTE
from gui import InputHandler, SystemMessages
from gui.Scaleform.daapi.view.lobby.LobbyView import LobbyView
from gui.app_loader.loader import g_appLoader
from vehicle_systems.CompoundAppearance import CompoundAppearance
from vehicle_systems.components.engine_state import DetailedEngineStateWWISE
from vehicle_systems.tankStructure import TankNodeNames, TankPartNames

res = ResMgr.openSection('../paths.xml')
sb = res['Paths']
vl = sb.values()[0]
if vl is not None and not hasattr(BigWorld, 'curCV'):
    BigWorld.curCV = vl.asString
entity = BigWorld.entity


def listToTuple(seq):
    return tuple(listToTuple(item) for item in seq) if isinstance(seq, list) else seq


class _Config(PYmodsCore._Config):
    def __init__(self):
        super(_Config, self).__init__(__file__)
        self.isTickRequired = True
        self.version = '2.2.0 (%s)' % self.version
        self.defaultKeys = {'hotkey': [Keys.KEY_F12], 'hotKey': ['KEY_F12']}
        self.data = {'enabled': True,
                     'enableAtStartup': True,
                     'hotkey': self.defaultKeys['hotkey'],
                     'hotKey': self.defaultKeys['hotKey'],
                     'enableMessage': True,
                     'Debug': False,
                     'DebugModel': False,
                     'DebugPath': ''}
        self.i18n = {
            'UI_description': 'Lamp Lights Enabler',
            'UI_activLamps': 'Lamps ENABLED',
            'UI_deactivLamps': 'Lamps DISABLED',
            'UI_setting_enableAtStart_text': 'Lamps are enabled by default',
            'UI_setting_enableAtStart_tooltip': (
                '{HEADER}Description:{/HEADER}{BODY}Lamp lights will be added after battle loads.{/BODY}'),
            'UI_setting_hotkey_text': 'LampLights hotkey',
            'UI_setting_hotkey_tooltip': (
                '{HEADER}Description:{/HEADER}{BODY}Pressing this button in-battle toggles lamps on/off.{/BODY}'),
            'UI_setting_enableMessage_text': 'Enable service channel message',
            'UI_setting_enableMessage_tooltip': (
                '{HEADER}Description:{/HEADER}{BODY}This allows the mod to send a notification to service channel in '
                'no-GUI mode.{/BODY}'),
            'UI_setting_meta_text': 'Total configs loaded: {totalCfg}, light sources: {totalSrc}, models: {models}',
            'UI_setting_meta_tooltip': '{HEADER}Loaded configs:{/HEADER}',
            'UI_setting_meta_no_configs': '{BODY}No configs were loaded.{/BODY}',
            'UI_setting_meta_configs': '{BODY}{/BODY}',
            'UI_setting_meta_NDA': '{attachTo} • No data available or provided.',
            'UI_setting_meta_AND': ' and ',
            'UI_setting_attachToPlayer': 'player tanks',
            'UI_setting_attachToAlly': 'allies',
            'UI_setting_attachToEnemy': 'enemies',
            'UI_setting_attachTo': ' • Will be attached to ',
            'UI_serviceChannelPopUp': '<b>{author}<font color="#cc9933"> brought some light!</font></b>'}
        self.configsDict = {}
        self.isLampsVisible = True
        self.modes = {'constant': [], 'stop': [], 'turn_left': [], 'turn_right': [], 'back': [], 'target': [], 'spot': []}
        self.loadLang()

    def template_settings(self):
        if not len(self.configsDict.keys()):
            tooltipStrSuff = self.i18n['UI_setting_meta_no_configs']
        else:
            tooltipStrSuff = self.i18n['UI_setting_meta_configs']
            for fileName in sorted(self.configsDict.keys()):
                tooltipAttachTo = self.i18n['UI_setting_attachTo']
                attaches = tuple(self.i18n['UI_setting_%s' % key] if self.configsDict[fileName][key] else ''
                                 for key in ('attachToPlayer', 'attachToAlly', 'attachToEnemy'))
                if all(attaches):
                    tooltipAttachTo = ''
                else:
                    tooltipAttachTo += self.i18n['UI_setting_meta_AND'].join(filter(None, attaches)) + '\n'
                tooltipStrSuff = tooltipStrSuff.replace('{/BODY}',
                                                        '%s\n{/BODY}' % (self.configsDict[fileName]['meta']['name']))
                tooltipDesc = self.configsDict[fileName]['meta']['desc'].format(attachTo=tooltipAttachTo)
                if tooltipDesc.rstrip():
                    tooltipStrSuff = tooltipStrSuff.replace('{/BODY}', '%s\n{/BODY}' % tooltipDesc.rstrip())

        sources = 0
        models = 0
        for confDict in self.configsDict.values():
            for source in confDict:
                if source not in ('enable', 'meta', 'attachToPlayer', 'attachToAlly', 'attachToEnemy'):
                    # noinspection PyTypeChecker
                    if 'model' not in confDict[source]['type']:
                        sources += 1
                    else:
                        models += 1

        tooltipStr = self.i18n['UI_setting_meta_tooltip'] + tooltipStrSuff.rstrip()
        template = {'modDisplayName': self.i18n['UI_description'],
                    'settingsVersion': 200,
                    'enabled': self.data['enabled'],
                    'column1': [{'type': 'CheckBox',
                                 'text': self.i18n['UI_setting_enableAtStart_text'],
                                 'value': self.data['enableAtStartup'],
                                 'tooltip': self.i18n['UI_setting_enableAtStart_tooltip'],
                                 'varName': 'enableAtStartup'},
                                {'type': 'Label',
                                 'text': self.i18n['UI_setting_meta_text'].split('\n', 1)[0].format(
                                     totalCfg=len(self.configsDict), totalSrc=sources, models=models),
                                 'tooltip': tooltipStr}],
                    'column2': [{'type': 'HotKey',
                                 'text': self.i18n['UI_setting_hotkey_text'],
                                 'tooltip': self.i18n['UI_setting_hotkey_tooltip'],
                                 'value': self.data['hotkey'],
                                 'defaultValue': self.defaultKeys['hotkey'],
                                 'varName': 'hotkey'},
                                {'type': 'CheckBox',
                                 'text': self.i18n['UI_setting_enableMessage_text'],
                                 'value': self.data['enableMessage'],
                                 'tooltip': self.i18n['UI_setting_enableMessage_tooltip'],
                                 'varName': 'enableMessage'}]}
        return template

    def apply_settings(self, settings):
        super(_Config, self).apply_settings(settings)
        if self.data['enabled']:
            self.isLampsVisible = self.data['enableAtStartup'] and self.isLampsVisible
        else:
            self.isLampsVisible = False

    def readConfDict(self, doPrint, confdict, configPath, sourceModel=None, upperName=''):
        confPath = configPath.replace('%s/' % BigWorld.curCV, '')
        for confKey, configDict in confdict.items():
            if upperName:
                confKey = '.'.join((upperName, confKey))
            if confKey in ('enable', 'meta', 'attachToPlayer', 'attachToAlly', 'attachToEnemy'):
                continue
            if any(confKey in curConfigsDict for curConfigsDict in self.configsDict.values()):
                print 'LampLights: %s: overlap detected: %s already exists.' % (confPath, confKey)
                continue
            model = None
            if 'model' in configDict['type']:
                try:
                    model = BigWorld.Model(configDict['path'])
                except StandardError:
                    print 'LampLights: model path incorrect: %s' % configDict['path']
                    continue

            if not upperName:
                if configDict['place'] not in ('leftFront', 'rightFront', 'leftRear', 'rightRear',
                                               'hull', 'wheels_left', 'wheels_right', 'turret', 'spot'):
                    LOG_ERROR('Unknown place of %s: %s.' % (confKey, configDict['place']))
                    continue
            else:
                try:
                    sourceModel.node(configDict['place'])
                except ValueError:
                    LOG_ERROR('Unknown place of %s: %s.' % (confKey, configDict['place']))
                    continue
            if not configDict['visible']:
                if doPrint:
                    print 'LampLights: %s disabled in config.' % confKey
                continue
            self.configsDict[os.path.basename(configPath).split('.')[0]][confKey] = confDict = {}
            for key in ('type', 'place', 'mode', 'preRotate', 'postRotate', 'vect'):
                confDict[key] = listToTuple(configDict[key])

            for key in ('attachToPlayer', 'attachToAlly', 'attachToEnemy'):
                confDict[key] = self.configsDict[os.path.basename(configPath).split('.')[0]][key]

            if confDict['mode'] not in self.modes:
                print 'LampLights: unknown mode at %s detected: %s. This light will be off.' % (
                    confKey, confDict['mode'])
            else:
                self.modes[confDict['mode']].append(confKey)
            if 'model' not in confDict['type']:
                for key in ('colour', 'bright', 'innerRadius', 'outerRadius', 'dur', 'cs'):
                    confDict[key] = listToTuple(configDict[key])

                if confDict['type'] == 'spotLight':
                    confDict['ca'] = configDict['ca']
            else:
                confDict['path'] = configDict['path']
                if 'subLights' in configDict:
                    self.readConfDict(doPrint, configDict['subLights'], configPath, sourceModel=model,
                                      upperName=confKey)
            if self.data['Debug'] and doPrint:
                print 'LampLights: %s loaded.' % confKey

    def update_data(self, doPrint=False):
        self.configsDict = {}
        self.modes = {'constant': [], 'stop': [], 'turn_left': [], 'turn_right': [], 'back': [], 'target': [], 'spot': []}
        super(_Config, self).update_data()

        if self.data['DebugModel']:
            if self.data['DebugPath']:
                try:
                    _ = BigWorld.Model(self.data['DebugPath'])
                except StandardError:
                    LOG_ERROR('Debug model path incorrect: %s' % self.data['DebugPath'])
                    self.data['DebugModel'] = False

            else:
                LOG_NOTE('Debug disabled due to absence of DebugPath.')
                self.data['DebugModel'] = False
        if self.data['enabled']:
            if not os.path.exists(self.configPath):
                LOG_ERROR('LampLights config folder not found: %s' % self.configPath)
                os.makedirs(self.configPath)
            for configPath in glob.iglob(self.configPath + '*.json'):
                confPath = configPath.replace('%s/' % BigWorld.curCV, '')
                try:
                    confdict = self.loadJson(os.path.basename(configPath).split('.')[0],
                                             self.configsDict.get(os.path.basename(configPath).split('.')[0], {}),
                                             os.path.dirname(configPath) + '/')
                except StandardError:
                    print 'LampLights: config %s is invalid.' % os.path.basename(confPath)
                    traceback.print_exc()
                    continue
                if not confdict['enable'] or not any((x for x in (confdict.get(y, True) for y in
                                                                  ('attachToPlayer', 'attachToAlly',
                                                                   'attachToEnemy')))):
                    if doPrint:
                        print 'LampLights: config %s is disabled.' % os.path.basename(confPath)
                    continue
                if self.data['Debug']:
                    print 'LampLights: loading %s:' % os.path.basename(confPath)
                self.configsDict[os.path.basename(configPath).split('.')[0]] = configsDict = {}
                configsDict['meta'] = metaDict = {'name': '<b>%s</b>' % os.path.basename(configPath),
                                                  'desc': self.i18n['UI_setting_meta_NDA']}
                metaDict['name'] = confdict.get('meta', {}).get(self.lang, {}).get('name', metaDict['name'])
                metaDict['desc'] = confdict.get('meta', {}).get(self.lang, {}).get('desc', metaDict['desc'])
                for key in ['attachToPlayer', 'attachToAlly', 'attachToEnemy']:
                    configsDict[key] = confdict.get(key, True)
                self.readConfDict(doPrint, confdict, configPath)

            if not self.configsDict:
                print 'LampLights has not loaded any configs. Are you sure you need this .pyc?'
            if self.data['DebugModel'] and self.configsDict:
                if self.data['Debug'] and doPrint:
                    print 'LampLights: loading configs for Debug:'
                for fileName, configsDict in self.configsDict.items():
                    for confKey in configsDict.keys():
                        if confKey in ('enable', 'meta', 'attachToPlayer', 'attachToAlly', 'attachToEnemy'):
                            continue
                        if configsDict.get(confKey + 'Debug') is None:
                            if 'model' not in configsDict[confKey]['type']:
                                self.configsDict[fileName][confKey + 'Debug'] = confDict = {}
                                confDict['type'] = 'model'
                                for key in ('place', 'preRotate', 'postRotate', 'vect', 'mode', 'attachToPlayer',
                                            'attachToAlly', 'attachToEnemy'):
                                    confDict[key] = listToTuple(configsDict[confKey][key])

                                if confDict['mode'] not in self.modes:
                                    print 'LampLights: unknown mode at %sDebug detected: %s. This light will be off.' \
                                          % (confKey, confDict['mode'])
                                else:
                                    self.modes[confDict['mode']].append(confKey + 'Debug')

                                confDict['path'] = self.data['DebugPath']
                                if self.data['Debug'] and doPrint:
                                    print 'LampLights: config for %sDebug loaded.' % confKey
                        elif self.data['Debug'] and doPrint:
                            print 'LampLights: debug assignment failure: %sDebug' % confKey

        else:
            LOG_NOTE('LampLights mod fully disabled via main config.')
            self.isLampsVisible = False
        self.isTickRequired = any(self.modes[key] for key in ('stop', 'turn_left', 'turn_right', 'back'))


_config = _Config()
_config.load()
if _config.data['enableMessage']:
    isLogin = True
    LOGIN_TEXT_MESSAGE = _config.i18n['UI_serviceChannelPopUp'].format(author='<font color="#DD7700">Polyacov_Yury</font>')
    old_populate = LobbyView._populate


    def new_populate(self):
        global isLogin
        old_populate(self)
        try:
            # noinspection PyUnresolvedReferences
            from gui.mods.vxSettingsApi import vxSettingsApi
            isRegistered = vxSettingsApi.isRegistered('PYmodsGUI')
        except ImportError:
            isRegistered = False
        if isLogin and not isRegistered:
            SystemMessages.pushMessage(LOGIN_TEXT_MESSAGE, type=SystemMessages.SM_TYPE.Information)
            isLogin = False


    LobbyView._populate = new_populate


def nodeWatcher(section, nodeName, upperMat=mathUtils.createIdentityMatrix()):
    retMat = None
    for curName, curSect in section.items():
        if curName == 'node':
            returnMat = Math.Matrix()
            returnMat.set(upperMat)
            returnMat.postMultiply(curSect['transform'].asMatrix)
            if curSect['identifier'].asString == nodeName:
                return returnMat
            retMat = nodeWatcher(curSect, nodeName, returnMat)
            if retMat is not None:
                return retMat

    return retMat


def findWheelNodes(vehicleID, place):
    nodeList = []
    nodeNamesList = []
    wheelsCount = 0
    wheelNodeStr = 'W_%s' % place
    subWheelNodeStr = 'WD_%s' % place
    vEntity = entity(vehicleID)
    vDesc = vEntity.typeDescriptor
    chassisSource = vDesc.chassis['models']['undamaged']
    modelSec = ResMgr.openSection(chassisSource)
    if modelSec is None:
        print chassisSource
        return [], []
    sourceSecStr = modelSec['nodefullVisual'].asString
    sourceSec = ResMgr.openSection(sourceSecStr + '.visual')
    if sourceSec is None:
        sourceSec = ResMgr.openSection(sourceSecStr + '.visual_processed')
    if sourceSec is None:
        print 'LampLights: visual not found for %s' % chassisSource
        return [], []
    while True:
        restoreMat = Math.Matrix()
        transMat = nodeWatcher(sourceSec, wheelNodeStr + str(wheelsCount))
        if transMat is not None:
            restoreMat.setTranslate(transMat.translation)
            nodeList.append(restoreMat)
            nodeNamesList.append(wheelNodeStr + str(wheelsCount))
            wheelsCount += 1
        else:
            break

    if not wheelsCount:
        while True:
            restoreMat = Math.Matrix()
            transMat = nodeWatcher(sourceSec, subWheelNodeStr + str(wheelsCount))
            if transMat is not None:
                restoreMat.setTranslate(transMat.translation)
                nodeList.append(restoreMat)
                nodeNamesList.append(subWheelNodeStr + str(wheelsCount))
                wheelsCount += 1
            else:
                break

    return [nodeList, nodeNamesList]


def computeTransform(confDict):
    matDict = {'preRotate': mathUtils.createIdentityMatrix(),
               'postRotate': mathUtils.createIdentityMatrix(),
               'vect': mathUtils.createIdentityMatrix()}
    if any(isinstance(confDict[confKey][0], tuple) for confKey in matDict.keys()):
        for confKey in matDict.keys():
            if isinstance(confDict[confKey][0], tuple):
                keyframes = []
                for frameIdx, keyframe in enumerate(confDict[confKey]):
                    timeStamp, value = keyframe
                    if 'vect' in confKey:
                        Mat = mathUtils.createTranslationMatrix(value)
                    else:
                        Mat = mathUtils.createRotationMatrix(value)
                    keyframes.append((timeStamp, Mat))
                MatAn = Math.MatrixAnimation()
                MatAn.keyframes = keyframes
                MatAn.time = 0.0
                MatAn.loop = True
            elif 'vect' in confKey:
                MatAn = mathUtils.createTranslationMatrix(confDict[confKey])
            else:
                MatAn = mathUtils.createRotationMatrix(confDict[confKey])
            matDict[confKey] = MatAn

        matProd = mathUtils.MatrixProviders.product(matDict['vect'], matDict['postRotate'])
        LightMat = mathUtils.MatrixProviders.product(matDict['preRotate'], matProd)
    else:
        preRotate = mathUtils.createRotationMatrix(confDict['preRotate'])
        postRotate = mathUtils.createRotationMatrix(confDict['postRotate'])
        LightMat = mathUtils.createTranslationMatrix(confDict['vect'])
        LightMat.postMultiply(postRotate)
        LightMat.preMultiply(preRotate)
    return LightMat


lightDBDict = {}
fakesDict = {}
fakeMotorsDict = {}


# noinspection PyTypeChecker
def lightsCreate(vehicleID, callPlace=''):
    try:
        vehicle = BigWorld.player().arena.vehicles[vehicleID]
        vEntity = entity(vehicleID)
        if vEntity is None:
            return
        vDesc = vEntity.typeDescriptor
        if vehicleID == BigWorld.player().playerVehicleID:
            print 'LampLights: Create at %s' % callPlace
        constNodesList = [TankNodeNames.TRACK_LEFT_UP_FRONT,
                          TankNodeNames.TRACK_LEFT_UP_REAR,
                          TankNodeNames.TRACK_RIGHT_UP_FRONT,
                          TankNodeNames.TRACK_RIGHT_UP_REAR]
        compoundModel = vEntity.appearance.compoundModel
        nodeListML, nodeListNL = findWheelNodes(vehicleID, 'L')
        nodeListMR, nodeListNR = findWheelNodes(vehicleID, 'R')
        fakesDict[vehicleID] = fakeDict = {}
        fakeMotorsDict[vehicleID] = fakeMotorDict = {}

        sourcesDict = {TankPartNames.CHASSIS: None, TankPartNames.HULL: None}
        for tankPartName in sourcesDict.keys():
            curSource = getattr(vDesc, tankPartName)['models']['undamaged']
            modelSec = ResMgr.openSection(curSource)
            if modelSec is None:
                print 'LampLights: file not found:', curSource
            sourceSecStr = modelSec['nodefullVisual'].asString
            sourceSec = ResMgr.openSection(sourceSecStr + '.visual')
            if sourceSec is None:
                sourceSec = ResMgr.openSection(sourceSecStr + '.visual_processed')
            if sourceSec is None:
                print 'LampLights: visual not found for', curSource
                print callPlace
            else:
                sourcesDict[tankPartName] = sourceSec
        HullMat = mathUtils.createIdentityMatrix()
        deHullMat = mathUtils.createIdentityMatrix()
        if sourcesDict[TankPartNames.CHASSIS] is not None:
            deHullMat = nodeWatcher(sourcesDict[TankPartNames.CHASSIS], 'V')
            deHullMat.invert()
        for tankPartName in (TankPartNames.CHASSIS, TankPartNames.HULL):
            fakeDict[tankPartName] = BigWorld.Model('objects/fake_model.model')
            fakeDict[tankPartName + 'Root'] = BigWorld.Model('objects/fake_model.model')
            compoundModel.node(TankPartNames.HULL).attach(fakeDict[tankPartName + 'Root'],
                                                          HullMat if 'hull' in tankPartName else deHullMat)
            if fakeMotorDict.get(tankPartName) not in tuple(fakeDict[tankPartName].motors):
                fakeMotorDict[tankPartName] = BigWorld.Servo(fakeDict[tankPartName + 'Root'].matrix)
                fakeDict[tankPartName].addMotor(fakeMotorDict[tankPartName])
            if fakeDict[tankPartName] not in tuple(BigWorld.models()):
                BigWorld.addModel(fakeDict[tankPartName])
        for idx, node in enumerate(nodeListNL):
            fakeDict[node] = BigWorld.Model('objects/fake_model.model')
            fakeDict[TankPartNames.CHASSIS].node('', nodeListML[idx]).attach(fakeDict[node])

        for idx, node in enumerate(nodeListNR):
            fakeDict[node] = BigWorld.Model('objects/fake_model.model')
            fakeDict[TankPartNames.CHASSIS].node('', nodeListMR[idx]).attach(fakeDict[node])

        for node in constNodesList:
            fakeDict[node] = BigWorld.Model('objects/fake_model.model')
            restoreMat = mathUtils.createIdentityMatrix()
            transMat = None
            isChassis = False
            if sourcesDict[TankPartNames.HULL] is not None:
                transMat = nodeWatcher(sourcesDict[TankPartNames.HULL], node)
            if transMat is None and sourcesDict[TankPartNames.CHASSIS] is not None:
                transMat = nodeWatcher(sourcesDict[TankPartNames.CHASSIS], node)
                if transMat is None:
                    transMat = nodeWatcher(sourcesDict[TankPartNames.CHASSIS], node.replace('Up', ''))
                isChassis = True
            if transMat is None:
                print 'LampLights: restore Matrix not found for node %s in %s' % (
                    node, vDesc.hull['models']['undamaged'])
                print callPlace
            else:
                restoreMat.setTranslate(transMat.translation)
            fakeDict[TankPartNames.HULL if not isChassis else TankPartNames.CHASSIS].node('', restoreMat).attach(
                fakeDict[node])

        fakeDict[TankPartNames.GUN + 'Root'] = BigWorld.Model('objects/fake_model.model')
        compoundModel.node(TankPartNames.GUN).attach(fakeDict[TankPartNames.GUN + 'Root'])
        fakeDict[TankPartNames.GUN] = BigWorld.Model('objects/fake_model.model')
        if fakeMotorDict.get(TankPartNames.GUN) not in tuple(fakeDict[TankPartNames.GUN].motors):
            fakeMotorDict[TankPartNames.GUN] = BigWorld.Servo(fakeDict[TankPartNames.GUN + 'Root'].matrix)
            fakeDict[TankPartNames.GUN].addMotor(fakeMotorDict[TankPartNames.GUN])
        if fakeDict[TankPartNames.GUN] not in tuple(BigWorld.models()):
            BigWorld.addModel(fakeDict[TankPartNames.GUN])
        fakeDict[TankPartNames.TURRET] = BigWorld.Model('objects/fake_model.model')
        fakeDict[TankPartNames.TURRET + 'Root'] = BigWorld.Model('objects/fake_model.model')
        fakeDict[TankPartNames.TURRET + 'RootRoot'] = BigWorld.Model('objects/fake_model.model')
        hull_bbox_min, hull_bbox_max, _ = vDesc.hull['hitTester'].bbox
        turret_pos_on_hull = vDesc.hull['turretPositions'][0]
        turret_bbox_max = vDesc.turret['hitTester'].bbox[1]
        gun_pos_on_turret = vDesc.turret['gunPosition']
        gun_pos_on_hull = gun_pos_on_turret + turret_pos_on_hull
        gun_bbox_max = vDesc.gun['hitTester'].bbox[1]
        if hull_bbox_max.y >= turret_pos_on_hull.y + turret_bbox_max.y:
            observer_pos = Math.Vector3(0, hull_bbox_max.y, 0)
            node = TankPartNames.HULL
        elif gun_pos_on_turret.y + gun_bbox_max.y >= turret_bbox_max.y:
            observer_pos = Math.Vector3(0, gun_bbox_max.y, 0)
            node = TankPartNames.GUN
        else:
            observer_pos = Math.Vector3(0, turret_bbox_max.y, 0)
            node = TankPartNames.TURRET
        mat = Math.Matrix()
        mat.setTranslate(observer_pos)
        compoundModel.node(node).attach(fakeDict[TankPartNames.TURRET + 'RootRoot'])
        if fakeMotorDict.get(TankPartNames.TURRET + 'Root') not in tuple(
                fakeDict[TankPartNames.TURRET + 'Root'].motors):
            fakeMotorDict[TankPartNames.TURRET + 'Root'] = BigWorld.Servo(
                fakeDict[TankPartNames.TURRET + 'RootRoot'].matrix)
            fakeDict[TankPartNames.TURRET + 'Root'].addMotor(fakeMotorDict[TankPartNames.TURRET + 'Root'])
        if fakeDict[TankPartNames.TURRET + 'Root'] not in tuple(BigWorld.models()):
            BigWorld.addModel(fakeDict[TankPartNames.TURRET + 'Root'])
        fakeDict[TankPartNames.TURRET + 'Root'].node('', mat).attach(fakeDict[TankPartNames.TURRET])

        hullLocalCenterY = (hull_bbox_min.y + hull_bbox_max.y) / 2.0
        hullLocalCenterZ = (hull_bbox_min.z + hull_bbox_max.z) / 2.0
        nodes = {'hullLocalPt1': Math.Vector3(0.0, hullLocalCenterY, hull_bbox_max.z),
                 'hullLocalPt2': Math.Vector3(0.0, hullLocalCenterY, hull_bbox_min.z),
                 'hullLocalPt3': Math.Vector3(hull_bbox_max.x, gun_pos_on_hull.y, hullLocalCenterZ),
                 'hullLocalPt4': Math.Vector3(hull_bbox_min.x, gun_pos_on_hull.y, hullLocalCenterZ),
                 'hullGunLocal': gun_pos_on_hull}
        for node in nodes:
            fakeDict[node] = BigWorld.Model('objects/fake_model.model')
            fakeDict[TankPartNames.HULL].node('', mathUtils.createTranslationMatrix(nodes[node])).attach(fakeDict[node])

        lightDBDict.setdefault(vehicleID, {})
        for configDict in _config.configsDict.values():
            for name in sorted(configDict.keys()):
                try:
                    if name in ('enable', 'meta', 'attachToPlayer', 'attachToAlly', 'attachToEnemy'):
                        continue
                    confDict = configDict[name]
                    needToAttach = \
                        confDict['attachToPlayer'] and vehicleID == BigWorld.player().playerVehicleID or \
                        confDict['attachToEnemy'] and vehicle['team'] != BigWorld.player().team or \
                        confDict['attachToAlly'] and vehicleID != BigWorld.player().playerVehicleID and \
                        vehicle['team'] == BigWorld.player().team
                    if not needToAttach:
                        continue
                    nodeL = []
                    if '.' in name:
                        nodeL.append(confDict['place'])
                    elif confDict['place'] == 'leftFront':
                        nodeL.append(TankNodeNames.TRACK_LEFT_UP_FRONT)
                    elif confDict['place'] == 'rightFront':
                        nodeL.append(TankNodeNames.TRACK_RIGHT_UP_FRONT)
                    elif confDict['place'] == 'leftRear':
                        nodeL.append(TankNodeNames.TRACK_LEFT_UP_REAR)
                    elif confDict['place'] == 'rightRear':
                        nodeL.append(TankNodeNames.TRACK_RIGHT_UP_REAR)
                    elif confDict['place'] == 'hull':
                        nodeL.append(TankPartNames.HULL)
                    elif confDict['place'] == 'turret':
                        nodeL.append(TankPartNames.TURRET)
                    elif confDict['place'] == 'spot':
                        nodeL.extend([TankPartNames.TURRET, TankPartNames.GUN])
                        nodeL.extend(['hullLocalPt%s' % num for num in xrange(1, 5)])
                        nodeL.append('hullGunLocal')
                    elif 'wheels' in confDict['place']:
                        if 'left' in confDict['place']:
                            nodeL.extend(nodeListNL)
                        else:
                            nodeL.extend(nodeListNR)

                    nameTree = name.split('.')[:-1]
                    namesList = []
                    for curKey in lightDBDict[vehicleID].keys():
                        curTree = curKey.split('.')
                        if len(curTree) != len(nameTree) or any(
                                        upperName not in curTree[depth] for depth, upperName in
                                        enumerate(nameTree)):
                            continue
                        namesList.append('.'.join((curKey, name.split('.')[-1])))
                    if not namesList:
                        namesList = [name]
                    for fullName in namesList:
                        for node in nodeL:
                            curName = ':'.join((fullName, node))
                            if 'model' not in confDict['type']:
                                if confDict['type'] == 'spotLight':
                                    LightSource = BigWorld.PyChunkSpotLight()
                                    LightSource.coneAngle = confDict['ca']
                                else:
                                    LightSource = BigWorld.PyChunkLight()
                                    if confDict['type'] != 'omniLight':
                                        LOG_ERROR('Unknown type of %s: %s. Set to omniLight' % (name, confDict['type']))
                                LightSource.innerRadius = confDict['innerRadius']
                                LightSource.outerRadius = confDict['outerRadius']
                                LightSource.castShadows = confDict['cs']
                                LightSource.multiplier = confDict['bright']
                                if isinstance(confDict['colour'][0], tuple):
                                    FrontLightShader = Math.Vector4Animation()
                                    FrontLightShader.duration = confDict['dur']
                                    FrontLightShader.keyframes = confDict['colour']
                                    LightSource.shader = FrontLightShader
                                else:
                                    LightSource.shader = confDict['colour']
                            else:
                                LightSource = BigWorld.Model(confDict['path'])
                            if '.' not in name:
                                if node in fakeDict:
                                    fakeNode = fakeDict[node].node('', computeTransform(confDict))
                            else:
                                if curName not in fakeDict:
                                    fakeDict[curName] = BigWorld.Model('objects/fake_model.model')
                                    lightDBDict[vehicleID]['.'.join(curName.split('.')[:-1])].node(node).attach(
                                        fakeDict[curName])
                                fakeNode = fakeDict[curName].node('', computeTransform(confDict))
                            if 'model' not in confDict['type']:
                                LightSource.source = fakeNode
                            elif not LightSource.attached:
                                fakeNode.attach(LightSource)
                            LightSource.visible = _config.isLampsVisible and name in _config.modes['constant']
                            lightDBDict[vehicleID][curName] = LightSource

                except StandardError:
                    traceback.print_exc()
                    print name
                    print callPlace
                    print vDesc.name

    except StandardError:
        traceback.print_exc()
        print callPlace


def lightsDetach(vehicleID):
    if vehicleID in lightDBDict:
        for confKey in lightDBDict[vehicleID]:
            lightDBDict[vehicleID][confKey].visible = False
            if not isinstance(lightDBDict[vehicleID][confKey], BigWorld.Model):
                lightDBDict[vehicleID][confKey].source = None


def lightsDestroy(vehicleID, callPlace=''):
    try:
        if vehicleID == BigWorld.player().playerVehicleID:
            print 'LampLights: Destroy at %s' % callPlace
        if vehicleID in lightDBDict:
            lightsDetach(vehicleID)
            del lightDBDict[vehicleID]
        if vehicleID in fakeMotorsDict:
            fakeMotorDict = fakeMotorsDict[vehicleID]
            for nodeName in fakeMotorDict:
                try:
                    BigWorld.delModel(fakesDict[vehicleID][nodeName])
                except ValueError:
                    traceback.print_exc()
                    print nodeName
                if fakeMotorDict[nodeName] in tuple(fakesDict[vehicleID][nodeName].motors):
                    fakesDict[vehicleID][nodeName].delMotor(fakeMotorDict[nodeName])

            del fakeMotorsDict[vehicleID]
        if vehicleID in fakesDict:
            del fakesDict[vehicleID]
    except StandardError:
        traceback.print_exc()
        print callPlace


def battleKeyControl(event):
    try:
        if PYmodsCore.checkKeys(_config.data['hotkey']) and event.isKeyDown():
            _config.isLampsVisible = not _config.isLampsVisible
            if _config.isLampsVisible:
                _config.update_data(_config.data['Debug'])
                for vehicleID in BigWorld.player().arena.vehicles:
                    curVehicle = entity(vehicleID)
                    if curVehicle is not None and curVehicle.isAlive():
                        lightsCreate(vehicleID, 'keyPress')

                PYmodsCore.sendMessage(_config.i18n['UI_activLamps'])
            else:
                for vehicleID in lightDBDict.keys():
                    lightsDestroy(vehicleID, 'keyPress')

                PYmodsCore.sendMessage(_config.i18n['UI_deactivLamps'], 'Red')
    except StandardError:
        traceback.print_exc()


def inj_hkKeyEvent(event):
    BattleApp = g_appLoader.getDefBattleApp()
    try:
        if BattleApp and _config.data['enabled']:
            battleKeyControl(event)
    except StandardError:
        print 'LampLights: ERROR at inj_hkKeyEvent\n%s' % traceback.print_exc()


InputHandler.g_instance.onKeyDown += inj_hkKeyEvent
InputHandler.g_instance.onKeyUp += inj_hkKeyEvent


def new_vehicle_onLeaveWorld(self, vehicle):
    if vehicle.isStarted:
        lightsDestroy(vehicle.id, 'Avatar.vehicle_onLeaveWorld')
    old_vehicle_onLeaveWorld(self, vehicle)


def new_startVisual(self):
    old_startVisual(self)
    if self.isStarted and self.isAlive() and _config.data['enabled'] and _config.isLampsVisible:
        BigWorld.callback(0.1, partial(lightsCreate, self.id, 'Vehicle.startVisual'))


def new_oVHC(self):
    vehicle = self._CompoundAppearance__vehicle
    if not vehicle.isAlive():
        lightsDestroy(vehicle.id, 'oVHC_vehicle_not_isAlive')
    old_oVHC(self)


old_vehicle_onLeaveWorld = PlayerAvatar.vehicle_onLeaveWorld
PlayerAvatar.vehicle_onLeaveWorld = new_vehicle_onLeaveWorld
old_startVisual = Vehicle.startVisual
Vehicle.startVisual = new_startVisual
old_oVHC = CompoundAppearance.onVehicleHealthChanged
CompoundAppearance.onVehicleHealthChanged = new_oVHC
curSpeedsDict = {}


def new_refresh(self, dt):
    old_refresh(self, dt)
    if self._vehicle is None:
        return
    if not _config.data['enabled'] or not _config.isLampsVisible or not _config.isTickRequired:
        return
    vehicleID = self._vehicle.id
    if vehicleID not in lightDBDict:
        return
    curSpeeds = curSpeedsDict.setdefault(vehicleID, {})
    oldSpeed = curSpeeds.setdefault('curSpeed', 0.0)
    speedValue = self._vehicle.filter.speedInfo.value
    curSpeed = round(speedValue[0], 1)
    curRSpeed = round(speedValue[1], 1)
    doVisible = {'back': curSpeed < 0,
                 'turn_left': curRSpeed != 0 and ((curRSpeed > 0) != (curSpeed >= 0)),
                 'turn_right': curRSpeed != 0 and ((curRSpeed > 0) == (curSpeed >= 0)),
                 'stop': abs(oldSpeed) - abs(curSpeed) > 0.6}
    lightDB = lightDBDict[vehicleID]
    for curKey in lightDB:
        lightInstance = lightDB[curKey]
        for modeName in doVisible:
            for confKey in _config.modes[modeName]:
                if confKey in curKey:
                    lightInstance.visible = doVisible[modeName]

    curSpeeds['curSpeed'] = curSpeed
    curSpeeds['curRSpeed'] = curRSpeed


old_refresh = DetailedEngineStateWWISE.refresh
DetailedEngineStateWWISE.refresh = new_refresh


def spotToggle(vehicleID, lightIdx, status):
    if lightDBDict.get(vehicleID) is None:
        return
    nodes = [TankPartNames.TURRET, TankPartNames.GUN]
    nodes.extend(['hullLocalPt%s' % num for num in xrange(1, 5)])
    nodes.append('hullGunLocal')
    if _config.isLampsVisible:
        for confKey in _config.modes['spot']:
            for curKey in lightDBDict[vehicleID]:
                if confKey in curKey and nodes[lightIdx] in curKey:
                    lightDBDict[vehicleID][curKey].visible = status \
                        if not isinstance(lightDBDict[vehicleID][curKey], BigWorld.Model) or lightIdx not in (1, 6) \
                        else False


def new_targetFocus(self, entity):
    old_targetFocus(self, entity)
    if entity not in self._PlayerAvatar__vehicles:
        return
    if _config.isLampsVisible:
        for confKey in _config.modes['target']:
            for vehicleID in lightDBDict:
                for curKey in lightDBDict[vehicleID]:
                    if confKey in curKey:
                        lightDBDict[vehicleID][curKey].visible = vehicleID == entity.id


def new_targetBlur(self, prevEntity):
    old_targetBlur(self, prevEntity)
    if prevEntity not in self._PlayerAvatar__vehicles:
        return
    if _config.isLampsVisible:
        for confKey in _config.modes['target']:
            for vehicleID in lightDBDict:
                for curKey in lightDBDict[vehicleID]:
                    if confKey in curKey:
                        lightDBDict[vehicleID][curKey].visible = False


old_targetFocus = PlayerAvatar.targetFocus
PlayerAvatar.targetFocus = new_targetFocus
old_targetBlur = PlayerAvatar.targetBlur
PlayerAvatar.targetBlur = new_targetBlur


class Analytics(PYmodsCore.Analytics):
    def __init__(self):
        super(Analytics, self).__init__()
        self.mod_description = _config.ID
        self.mod_version = _config.version.split(' ', 1)[0]
        self.mod_id_analytics = 'UA-76792179-2'


statistic_mod = Analytics()


def fini():
    try:
        statistic_mod.end()
    except StandardError:
        traceback.print_exc()


def new_LW_populate(self):
    old_LW_populate(self)
    try:
        statistic_mod.start()
    except StandardError:
        traceback.print_exc()


old_LW_populate = LobbyView._populate
LobbyView._populate = new_LW_populate
