import traceback
from Avatar import PlayerAvatar
from PYmodsCore import overrideMethod
from gui.hangar_vehicle_appearance import HangarVehicleAppearance
from vehicle_systems.tankStructure import TankNodeNames, TankPartNames
from . import attached_models
from .. import g_config


def create(vehicleID, vDesc, modelsSet, sname, visible=False):
    try:
        resList = []
        for partName in TankPartNames.ALL:
            modelPath = getattr(vDesc, partName).modelsSets[modelsSet].undamaged.replace(
                'vehicles/', 'vehicles/skins/models/%s/vehicles/' % sname)
            if partName == TankPartNames.CHASSIS:
                modelPath = modelPath.replace('Chassis', 'Chassis_dynamic')
            elif partName == TankPartNames.GUN:
                partName = TankNodeNames.GUN_INCLINATION
            resList.append((modelPath, partName))
        if resList:
            attached_models.create(vehicleID, 'skins_dynamic', 'attach_scale', resList, visible)
    except StandardError:
        traceback.print_exc()
        print vDesc.name


def attach(vehicleID, visible=False):
    attached_models.attach(vehicleID, 'skins_dynamic', visible)


def destroy(vehicleID):
    attached_models.detach(vehicleID, 'destroy', 'skins_dynamic')


@overrideMethod(HangarVehicleAppearance, '_HangarVehicleAppearance__setupModel')
def new_setupModel(base, self, buildIdx):
    base(self, buildIdx)
    attach(self._HangarVehicleAppearance__vEntity.id,
           g_config.dynamicSkinEnabled and g_config.collisionMode != 2)


@overrideMethod(PlayerAvatar, 'targetFocus')
def new_targetFocus(base, self, entity):
    base(self, entity)
    if entity in self._PlayerAvatar__vehicles:
        try:
            for vehicleID in attached_models.dynamic_db:
                attached_models.detach(vehicleID, modID='skins_dynamic', visible=vehicleID == entity.id)
        except StandardError:
            traceback.print_exc()


@overrideMethod(PlayerAvatar, 'targetBlur')
def new_targetBlur(base, self, prevEntity):
    base(self, prevEntity)
    if prevEntity in self._PlayerAvatar__vehicles:
        try:
            for vehicleID in attached_models.dynamic_db:
                attached_models.detach(vehicleID, modID='skins_dynamic')
        except StandardError:
            traceback.print_exc()
