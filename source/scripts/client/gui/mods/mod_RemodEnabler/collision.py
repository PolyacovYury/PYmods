import BigWorld
import GUI
import Math
import PYmodsCore
import material_kinds
from AvatarInputHandler import mathUtils
from gui.ClientHangarSpace import _VehicleAppearance
from vehicle_systems.tankStructure import TankPartNames
from . import g_config


def clearCollision(self):
    vEntityId = self._VehicleAppearance__vEntityId
    if getattr(self, 'collisionLoaded', False):
        for moduleName, moduleDict in self.modifiedModelsDesc.items():
            if moduleDict['model'] in tuple(BigWorld.entity(vEntityId).models):
                BigWorld.entity(vEntityId).delModel(moduleDict['model'])
                if moduleDict['motor'] in tuple(moduleDict['model'].motors):
                    moduleDict['model'].delMotor(moduleDict['motor'])
    if hasattr(self, 'collisionTable'):
        del self.collisionTable


@PYmodsCore.overrideMethod(_VehicleAppearance, 'refresh')
def new_refresh(base, self):
    clearCollision(self)
    base(self)


@PYmodsCore.overrideMethod(_VehicleAppearance, 'recreate')
def new_recreate(base, self, vDesc, vState, onVehicleLoadedCallback=None):
    clearCollision(self)
    base(self, vDesc, vState, onVehicleLoadedCallback)


@PYmodsCore.overrideMethod(_VehicleAppearance, '_VehicleAppearance__setupModel')
def new_setupModel(base, self, buildIdx):
    base(self, buildIdx)
    if not g_config.data['enabled']:
        return
    vEntityId = self._VehicleAppearance__vEntityId
    vEntity = BigWorld.entity(vEntityId)
    vDesc = self._VehicleAppearance__vDesc
    model = vEntity.model
    self.collisionLoaded = True
    self.modifiedModelsDesc = dict(
        [(part, {'model': None, 'motor': None, 'matrix': None}) for part in TankPartNames.ALL])
    failList = []
    for part in self.modifiedModelsDesc.keys():
        try:
            self.modifiedModelsDesc[part]['model'] = BigWorld.Model(getattr(vDesc, part).hitTester.bspModelName)
            self.modifiedModelsDesc[part]['model'].visible = False
        except StandardError:
            self.collisionLoaded = False
            failList.append(getattr(vDesc, part).hitTester.bspModelName)

    if failList:
        print 'RemodEnabler: collision load failed: models not found'
        print failList
    if not self.collisionLoaded:
        return
    if any((g_config.data['collisionEnabled'], g_config.data['collisionComparisonEnabled'])):
        # Getting offset matrices
        hullOffset = mathUtils.createTranslationMatrix(vEntity.typeDescriptor.chassis.hullPosition)
        turretOffset = mathUtils.createTranslationMatrix(vEntity.typeDescriptor.hull.turretPositions[0])
        gunOffset = mathUtils.createTranslationMatrix(vEntity.typeDescriptor.turret.gunPosition)
        # Getting local transform matrices
        hullMP = mathUtils.MatrixProviders.product(mathUtils.createIdentityMatrix(), hullOffset)
        turretMP = mathUtils.MatrixProviders.product(mathUtils.createIdentityMatrix(), turretOffset)
        gunMP = mathUtils.MatrixProviders.product(mathUtils.createIdentityMatrix(), gunOffset)
        # turretMP = mathUtils.MatrixProviders.product(vEntity.appearance.turretMatrix, turretOffset)
        # gunMP = mathUtils.MatrixProviders.product(vEntity.appearance.gunMatrix, gunOffset)
        # Getting full transform matrices relative to vehicle coordinate system
        self.modifiedModelsDesc[TankPartNames.CHASSIS]['matrix'] = fullChassisMP = mathUtils.createIdentityMatrix()
        self.modifiedModelsDesc[TankPartNames.HULL]['matrix'] = fullHullMP = mathUtils.MatrixProviders.product(
            hullMP, fullChassisMP)
        self.modifiedModelsDesc[TankPartNames.TURRET][
            'matrix'] = fullTurretMP = mathUtils.MatrixProviders.product(turretMP, fullHullMP)
        self.modifiedModelsDesc[TankPartNames.GUN]['matrix'] = mathUtils.MatrixProviders.product(gunMP, fullTurretMP)
        for moduleName, moduleDict in self.modifiedModelsDesc.items():
            if moduleDict['motor'] not in tuple(moduleDict['model'].motors):
                moduleDict['motor'] = BigWorld.Servo(
                    mathUtils.MatrixProviders.product(moduleDict['matrix'], vEntity.matrix))
                moduleDict['model'].addMotor(moduleDict['motor'])
            if moduleDict['model'] not in tuple(vEntity.models):
                try:
                    vEntity.addModel(moduleDict['model'])
                except StandardError:
                    pass
            moduleDict['model'].visible = True
        addCollisionGUI(self)
    if g_config.data['collisionEnabled']:
        for moduleName in TankPartNames.ALL:
            if model.node(moduleName) is not None:
                scaleMat = Math.Matrix()
                scaleMat.setScale((0.001, 0.001, 0.001))
                model.node(moduleName, scaleMat)
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
    vDesc = self._VehicleAppearance__vDesc
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
