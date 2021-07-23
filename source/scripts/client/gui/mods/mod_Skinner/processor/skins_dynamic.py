import Math
import ResMgr
import math_utils
import os
import traceback
from Avatar import PlayerAvatar
from PYmodsCore import overrideMethod
from gui.hangar_vehicle_appearance import HangarVehicleAppearance
from vehicle_systems import model_assembler
from vehicle_systems.tankStructure import TankNodeNames, TankPartNames
from .. import g_config


def apply(vDesc, modelsSet, skinName):
    vDesc.chassis.modelsSets['Skinner_dynamicData'] = data = []
    for partName in TankPartNames.ALL:
        try:
            nodeName = partName
            modelPath = 'vehicles/skins/models/' + skinName + '/' + '_dynamic'.join(
                os.path.splitext(getattr(vDesc, partName).modelsSets[modelsSet].undamaged))
            if not ResMgr.isFile(modelPath):
                print g_config.LOG, 'skin model not found:', modelPath
                continue
            if partName == TankPartNames.HULL:
                nodeName = 'V'
            if partName == TankPartNames.GUN:
                nodeName = TankNodeNames.GUN_INCLINATION
            data.append((partName, nodeName, modelPath, partName == TankPartNames.CHASSIS))
        except StandardError:
            print vDesc.name
            traceback.print_exc()


@overrideMethod(model_assembler, 'prepareCompoundAssembler')
def prepareCompoundAssembler(
        base, vehicleDesc, modelsSetParams, spaceID, isTurretDetached=False, lodIdx=model_assembler._DEFAULT_LOD_INDEX,
        skipMaterials=False, renderMode=None):
    result = base(vehicleDesc, modelsSetParams, spaceID, isTurretDetached, lodIdx, skipMaterials, renderMode)
    data = vehicleDesc.chassis.modelsSets.get('Skinner_dynamicData', ())
    for partName, nodeName, modelPath, needs_scale in data if modelsSetParams.state == 'undamaged' else ():
        scaleMatrix = math_utils.createIdentityMatrix()
        if needs_scale:
            scaleMatrix.setScale(Math.Vector3(1.01))
        result.addPart(modelPath, nodeName, g_config.ID + partName, scaleMatrix)
    return result


def switchDynamicPartsVisible(model, visible):
    if model is None:
        return
    for part in TankPartNames.ALL:
        nodeNames = (part, g_config.ID + part)
        nodes = tuple(model.node(node) for node in nodeNames)
        if None in nodes:
            continue
        handles = partHandle, moddedPartHandle = (model.findPartHandleByNode(node) for node in nodes)
        if 0xffffffff in handles:
            continue
        if part != TankPartNames.CHASSIS:
            model.setPartVisible(partHandle, not visible)
        model.setPartVisible(moddedPartHandle, visible)


@overrideMethod(HangarVehicleAppearance, '__setupModel')
def new_setupModel(base, self, buildIdx):
    base(self, buildIdx)
    switchDynamicPartsVisible(self.compoundModel, g_config.dynamicSkinEnabled and g_config.collisionMode != 2)


@overrideMethod(PlayerAvatar, 'targetFocus')
def new_targetFocus(base, self, entity):
    for vehicle in self.vehicles:
        try:
            switchDynamicPartsVisible(vehicle.model, vehicle.id == entity.id)
        except StandardError:
            traceback.print_exc()
    base(self, entity)


@overrideMethod(PlayerAvatar, 'targetBlur')
def new_targetBlur(base, self, prevEntity):
    base(self, prevEntity)
    for vehicle in self.vehicles:
        try:
            switchDynamicPartsVisible(vehicle.model, False)
        except StandardError:
            traceback.print_exc()
