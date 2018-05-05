import BigWorld
import GUI
import Math
import PYmodsCore
import material_kinds
from AvatarInputHandler import mathUtils
from gui.hangar_vehicle_appearance import HangarVehicleAppearance
from vehicle_systems.tankStructure import TankPartNames
from . import g_config


def clearCollision(self):
    vEntity = self._HangarVehicleAppearance__vEntity
    if getattr(self, 'collisionLoaded', False):
        for moduleName, moduleDict in self.modifiedModelsDesc.items():
            if moduleDict['model'] in tuple(vEntity.models):
                vEntity.delModel(moduleDict['model'])
                for motor in tuple(moduleDict['model'].motors):
                    moduleDict['model'].delMotor(motor)
    if hasattr(self, 'collisionTable'):
        del self.collisionTable


@PYmodsCore.overrideMethod(HangarVehicleAppearance, 'refresh')
def new_refresh(base, self, *args):
    clearCollision(self)
    base(self, *args)


@PYmodsCore.overrideMethod(HangarVehicleAppearance, 'recreate')
def new_recreate(base, self, *args):
    clearCollision(self)
    base(self, *args)


@PYmodsCore.overrideMethod(HangarVehicleAppearance, '_HangarVehicleAppearance__setupModel')
def new_setupModel(base, self, buildIdx):
    base(self, buildIdx)
    if not g_config.data['enabled']:
        return
    if any((g_config.collisionEnabled, g_config.collisionComparisonEnabled)):
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
            print 'RemodEnabler: collision load failed: models not found'
            print failList
        if not self.collisionLoaded:
            return
        # Getting offset matrices
        hullOffset = mathUtils.createTranslationMatrix(vDesc.chassis.hullPosition)
        self.modifiedModelsDesc[TankPartNames.CHASSIS]['matrix'] = fullChassisMP = mathUtils.createIdentityMatrix()
        hullMP = mathUtils.MatrixProviders.product(mathUtils.createIdentityMatrix(), hullOffset)
        self.modifiedModelsDesc[TankPartNames.HULL]['matrix'] = fullHullMP = mathUtils.MatrixProviders.product(
            hullMP, fullChassisMP)
        for idx, turretPosition in enumerate(vDesc.hull.turretPositions):
            if idx:
                print 'RemodEnabler: WARNING: multiple turrets are present!', vDesc.name
                break
            turretOffset = mathUtils.createTranslationMatrix(vDesc.hull.turretPositions[idx])
            gunOffset = mathUtils.createTranslationMatrix(vDesc.turret.gunPosition)
        # Getting local transform matrices
            turretMP = mathUtils.MatrixProviders.product(mathUtils.createIdentityMatrix(), turretOffset)
            gunMP = mathUtils.MatrixProviders.product(mathUtils.createIdentityMatrix(), gunOffset)
            # turretMP = mathUtils.MatrixProviders.product(vEntity.appearance.turretMatrix, turretOffset)
            # gunMP = mathUtils.MatrixProviders.product(vEntity.appearance.gunMatrix, gunOffset)
        # Getting full transform matrices relative to vehicle coordinate system
            self.modifiedModelsDesc[TankPartNames.TURRET]['matrix'] = fullTurretMP = mathUtils.MatrixProviders.product(
                turretMP, fullHullMP)
            self.modifiedModelsDesc[TankPartNames.GUN]['matrix'] = mathUtils.MatrixProviders.product(gunMP, fullTurretMP)
        for moduleName, moduleDict in self.modifiedModelsDesc.items():
            motor = BigWorld.Servo(mathUtils.MatrixProviders.product(moduleDict['matrix'], vEntity.matrix))
            moduleDict['model'].addMotor(motor)
            if moduleDict['model'] not in tuple(vEntity.models):
                try:
                    vEntity.addModel(moduleDict['model'])
                except StandardError:
                    pass
            moduleDict['model'].visible = True
        addCollisionGUI(self)
    if g_config.collisionEnabled:
        for moduleName in TankPartNames.ALL:
            # noinspection PyUnboundLocalVariable
            if compoundModel.node(moduleName) is not None:
                scaleMat = Math.Matrix()
                scaleMat.setScale((0.001, 0.001, 0.001))
                compoundModel.node(moduleName, scaleMat)
            else:
                print 'RemodEnabler: model rescale for %s failed' % moduleName


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
        super(self.__class__, self).__init__(GUI.Text(''), position, colour, size)
        self.GUIComponent.explicitSize = True
        self.GUIComponent.font = 'system_small'
        self.GUIComponent.text = text


class TexBox(GUIBox):
    def __init__(self, texturePath='', position=(0, 0, 1), size=(0.09, 0.045)):
        super(self.__class__, self).__init__(GUI.Simple(''), position, (255, 255, 255, 255), size)
        self.GUIComponent.widthMode = 'CLIP'
        self.GUIComponent.textureName = texturePath
        self.GUIComponent.mapping = ((0.0, 0.0), (0.0, 1.0), (1.0, 1.0), (1.0, 0.0))


def addCollisionGUI(self):
    vDesc = self._HangarVehicleAppearance__vDesc
    self.collisionTable = {}
    for moduleIdx, moduleName in enumerate(TankPartNames.ALL):
        self.collisionTable[moduleName] = curCollisionTable = {'textBoxes': [], 'texBoxes': [], 'armorValues': {}}
        moduleDict = getattr(vDesc, moduleName)
        for Idx, groupNum in enumerate(sorted(moduleDict.materials.keys())):
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
