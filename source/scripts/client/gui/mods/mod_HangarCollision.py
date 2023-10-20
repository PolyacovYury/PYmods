import BigWorld
import GUI
import Keys
import Math
import material_kinds
import math_utils
from OpenModsCore import SimpleConfigInterface, checkKeys, overrideMethod
from gui import SystemMessages as SM
from gui.hangar_vehicle_appearance import HangarVehicleAppearance
from vehicle_systems.tankStructure import TankPartNames


class ConfigInterface(SimpleConfigInterface):
    def __init__(self):
        self.collisionMode = 0
        super(ConfigInterface, self).__init__()

    def init(self):
        self.ID = '%(mod_ID)s'
        self.version = '1.0.0 (%(file_compile_date)s)'
        self.author = 'by Polyacov_Yury'
        self.modsGroup = 'PYmods'
        self.modSettingsID = 'PYmodsGUI'
        self.defaultKeys = {
            'CollisionHotkey': [Keys.KEY_F4, [Keys.KEY_LCONTROL, Keys.KEY_RCONTROL]]
        }
        self.data = {
            'enabled': True,
            'debug': True,
            'CollisionHotkey': self.defaultKeys['CollisionHotkey'],
        }
        self.i18n = {
            'name': 'Hangar Collision',
            'UI_setting_CollisionHotkey_text': 'Collision view switch hotkey',
            'UI_setting_CollisionHotkey_tooltip': (
                '<b>WARNING: this module is non-functional. Apologies for the inconvenience.</b>\n'
                'This hotkey will switch collision preview mode in hangar.\n'
                '<b>Available modes:</b>\n • OFF\n • Model replace\n • Model add'),
            'UI_setting_debug_text': 'Enable extended log printing',
            'UI_setting_debug_tooltip': 'If enabled, your python.log will be harassed with mod\'s debug information.',
            'collision_compare_enable': '<b>RemodEnabler:</b>\nEnabling collision comparison mode.',
            'collision_compare_disable': '<b>RemodEnabler:</b>\nDisabling collision comparison mode.',
            'collision_enable': '<b>RemodEnabler:</b>\nEnabling collision mode.',
            'collision_unavailable': 'Collision displaying is currently not supported.',
        }

    def createTemplate(self):
        return {
            'modDisplayName': self.i18n['name'], 'enabled': self.data['enabled'],
            'column1': [
                self.tb.createHotKey('CollisionHotkey'),
            ],
            'column2': [
                self.tb.createControl('debug'),
            ]}

    def onHotkeyPressed(self, event):
        if (not hasattr(BigWorld.player(), 'databaseID') or not self.data['enabled'] or not event.isKeyDown()
                or self.isMSAOpen):
            return
        if checkKeys(self.data['CollisionHotkey'], event.key):
            SM.pushMessage('temp_SM<b>%s:</b>\n%s' % (
                self.i18n['name'], self.i18n['collision_unavailable']), SM.SM_TYPE.Warning)
            return
            # noinspection PyUnreachableCode
            self.collisionMode += 1
            self.collisionMode %= 3
            if self.collisionMode == 0:
                debugMsg = 'disabling collision displaying'
                msg = self.i18n['collision_compare_disable']
            elif self.collisionMode == 2:
                debugMsg = 'enabling collision display comparison mode'
                msg = self.i18n['collision_compare_enable']
            else:
                debugMsg = 'enabling collision display'
                msg = self.i18n['collision_enable']
            if self.data['debug']:
                print self.LOG, debugMsg
            SM.pushMessage('temp_SM' + msg, SM.SM_TYPE.CustomizationForGold)
            refreshCurrentVehicle()


g_config = ConfigInterface()


def clearCollision(self):
    vEntity = self._HangarVehicleAppearance__vEntity
    if getattr(self, 'collisionLoaded', False):
        for moduleDict in self.modifiedModelsDesc.itervalues():
            if moduleDict['model'] in tuple(vEntity.models):
                vEntity.delModel(moduleDict['model'])
                for motor in tuple(moduleDict['model'].motors):
                    moduleDict['model'].delMotor(motor)
    if hasattr(self, 'collisionTable'):
        del self.collisionTable


@overrideMethod(HangarVehicleAppearance, 'refresh')
def new_refresh(base, self, *args, **kwargs):
    clearCollision(self)
    return base(self, *args, **kwargs)


@overrideMethod(HangarVehicleAppearance, 'recreate')
def new_recreate(base, self, *args, **kwargs):
    clearCollision(self)
    return base(self, *args, **kwargs)


@overrideMethod(HangarVehicleAppearance, '__setupModel')
def new_setupModel(base, self, buildIdx, *args, **kwargs):
    base(self, buildIdx, *args, **kwargs)
    if not g_config.data['enabled']:
        return
    if g_config.collisionMode:
        vEntity = self._HangarVehicleAppearance__vEntity
        vDesc = self._HangarVehicleAppearance__vDesc
        compoundModel = vEntity.model
        self.collisionLoaded = True
        self.modifiedModelsDesc = {}
        failList = []
        for partName in TankPartNames.ALL:
            modelName = ''
            try:
                modelName = getattr(vDesc, partName).hitTester.bspModelName
                model = BigWorld.Model(modelName)
                model.visible = False
                self.modifiedModelsDesc[partName] = {'model': model, 'matrix': None}
            except StandardError:
                self.collisionLoaded = False
                failList.append(modelName if modelName else partName)
        if failList:
            print g_config.LOG, 'collision load failed: models not found', failList
        if not self.collisionLoaded:
            return
        # Getting offset matrices
        hullOffset = math_utils.createTranslationMatrix(vDesc.chassis.hullPosition)
        self.modifiedModelsDesc[TankPartNames.CHASSIS]['matrix'] = fullChassisMP = math_utils.createIdentityMatrix()
        hullMP = math_utils.MatrixProviders.product(math_utils.createIdentityMatrix(), hullOffset)
        self.modifiedModelsDesc[TankPartNames.HULL]['matrix'] = fullHullMP = math_utils.MatrixProviders.product(
            hullMP, fullChassisMP)
        for idx in xrange(len(vDesc.hull.turretPositions)):
            if idx:
                print g_config.LOG, 'WARNING: multiple turrets are present!', vDesc.name
                break
            turretOffset = math_utils.createTranslationMatrix(vDesc.hull.turretPositions[idx])
            gunOffset = math_utils.createTranslationMatrix(vDesc.turret.gunPosition)
            # Getting local transform matrices
            turretMP = math_utils.MatrixProviders.product(math_utils.createIdentityMatrix(), turretOffset)
            gunMP = math_utils.MatrixProviders.product(math_utils.createIdentityMatrix(), gunOffset)
            # turretMP = math_utils.MatrixProviders.product(vEntity.appearance.turretMatrix, turretOffset)
            # gunMP = math_utils.MatrixProviders.product(vEntity.appearance.gunMatrix, gunOffset)
            # Getting full transform matrices relative to vehicle coordinate system
            self.modifiedModelsDesc[TankPartNames.TURRET]['matrix'] = fullTurretMP = math_utils.MatrixProviders.product(
                turretMP, fullHullMP)
            self.modifiedModelsDesc[TankPartNames.GUN]['matrix'] = math_utils.MatrixProviders.product(gunMP, fullTurretMP)
        for moduleDict in self.modifiedModelsDesc.itervalues():
            motor = BigWorld.Servo(math_utils.MatrixProviders.product(moduleDict['matrix'], vEntity.matrix))
            moduleDict['model'].addMotor(motor)
            if moduleDict['model'] not in tuple(vEntity.models):
                try:
                    vEntity.addModel(moduleDict['model'])
                except StandardError:
                    pass
            moduleDict['model'].visible = True
        addCollisionGUI(self)
    if g_config.collisionMode == 1:
        for moduleName in TankPartNames.ALL:
            # noinspection PyUnboundLocalVariable
            if compoundModel.node(moduleName) is not None:
                scaleMat = Math.Matrix()
                scaleMat.setScale((0.001, 0.001, 0.001))
                compoundModel.node(moduleName, scaleMat)
            else:
                print g_config.LOG, 'model rescale for', moduleName, 'failed'


class GUIBox(object):
    def __init__(self, obj, position, colour, size):
        self.GUIComponent = obj
        self.GUIComponent.verticalAnchor = 'CENTER'
        self.GUIComponent.horizontalAnchor = 'CENTER'
        self.GUIComponent.verticalPositionMode = 'CLIP'
        self.GUIComponent.horizontalPositionMode = 'CLIP'
        self.GUIComponent.heightMode = 'CLIP'
        self.GUIComponent.materialFX = 'BLEND'
        self.GUIComponent.colour = colour
        self.GUIComponent.position = position
        self.GUIComponent.size = size
        self.GUIComponent.visible = True

    def addRoot(self):
        GUI.addRoot(self.GUIComponent)

    def delRoot(self):
        GUI.delRoot(self.GUIComponent)

    def __del__(self):
        self.delRoot()


class TextBox(GUIBox):
    def __init__(self, text='', position=(0, 0.6, 1), colour=(255, 255, 255, 255), size=(0, 0.04)):
        super(TextBox, self).__init__(GUI.Text(''), position, colour, size)
        self.GUIComponent.explicitSize = True
        self.GUIComponent.font = 'system_small'
        self.GUIComponent.text = text


class TexBox(GUIBox):
    def __init__(self, texturePath='', position=(0, 0, 1), size=(0.09, 0.045)):
        super(TexBox, self).__init__(GUI.Simple(''), position, (255, 255, 255, 255), size)
        self.GUIComponent.widthMode = 'CLIP'
        self.GUIComponent.textureName = texturePath
        self.GUIComponent.mapping = ((0.0, 0.0), (0.0, 1.0), (1.0, 1.0), (1.0, 0.0))


def addCollisionGUI(self):
    vDesc = self._HangarVehicleAppearance__vDesc
    self.collisionTable = {}
    for moduleIdx, moduleName in enumerate(TankPartNames.ALL):
        self.collisionTable[moduleName] = curCollisionTable = {'textBoxes': [], 'texBoxes': [], 'armorValues': {}}
        moduleDict = getattr(vDesc, moduleName)
        for groupNum in sorted(moduleDict.materials.keys()):
            armorValue = int(moduleDict.materials[groupNum].armor)
            curCollisionTable['armorValues'].setdefault(armorValue, [])
            if groupNum not in curCollisionTable['armorValues'][armorValue]:
                curCollisionTable['armorValues'][armorValue].append(groupNum)
        for Idx, armorValue in enumerate(sorted(curCollisionTable['armorValues'], reverse=True)):
            x = (6 + moduleIdx) / 10.0 + 0.025
            y = (-1 - Idx) / 20.0 - 0.002
            textBox = TextBox('%s' % armorValue, (x, y, 0.7), (240, 240, 240, 255))
            textBox.addRoot()
            curCollisionTable['textBoxes'].append(textBox)
            textBox = TextBox('%s' % armorValue, (x, y, 0.725), (0, 0, 0, 255))
            textBox.addRoot()
            curCollisionTable['textBoxes'].append(textBox)
            kindsCap = len(curCollisionTable['armorValues'][armorValue])
            for matIdx, matKind in enumerate(curCollisionTable['armorValues'][armorValue]):
                matKindName = material_kinds.IDS_BY_NAMES.keys()[material_kinds.IDS_BY_NAMES.values().index(matKind)]
                texName = 'objects/misc/collisions_mat/%s.dds' % matKindName
                colWidth = 0.09
                colPad = colWidth / 2.0
                x = (6 + moduleIdx) / 10.0 + 0.025 - colPad + colPad / float(kindsCap) + (
                        colWidth / float(kindsCap) * float(matIdx))
                y = (-1 - Idx) / 20.0
                texBox = TexBox(texName, (x, y, 0.8), (0.09 / float(kindsCap), 0.045))
                texBox.addRoot()
                curCollisionTable['texBoxes'].append(texBox)
        GUI.reSort()
