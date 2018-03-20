import PYmodsCore
import traceback
from Avatar import PlayerAvatar
from gui.hangar_vehicle_appearance import HangarVehicleAppearance
from vehicle_systems.tankStructure import TankNodeNames, TankPartNames
from . import attached_models
from .. import g_config


def create(vehicleID, vDesc, visible=False):
    try:
        sname = g_config.OSDesc['dynamic'].name
        resList = []
        for partName in TankPartNames.ALL:
            modelPath = getattr(vDesc, partName).models.undamaged.replace(
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


@PYmodsCore.overrideMethod(HangarVehicleAppearance, '_HangarVehicleAppearance__setupModel')
def new_setupModel(base, self, buildIdx):
    base(self, buildIdx)
    if g_config.OSDesc['dynamic'] is not None:
        attach(self._HangarVehicleAppearance__vEntity.id,
               g_config.dynamicSkinEnabled and not g_config.collisionComparisonEnabled)


@PYmodsCore.overrideMethod(PlayerAvatar, 'targetFocus')
def new_targetFocus(base, self, entity):
    base(self, entity)
    if entity in self._PlayerAvatar__vehicles:
        try:
            for vehicleID, dyn in attached_models.dynamic_db.iteritems():
                attached_models.detach(vehicleID, modID='skins_dynamic', visible=vehicleID == entity.id)
        except StandardError:
            traceback.print_exc()


@PYmodsCore.overrideMethod(PlayerAvatar, 'targetBlur')
def new_targetBlur(base, self, prevEntity):
    base(self, prevEntity)
    if prevEntity in self._PlayerAvatar__vehicles:
        try:
            for vehicleID in attached_models.dynamic_db:
                attached_models.detach(vehicleID, modID='skins_dynamic')
        except StandardError:
            traceback.print_exc()
