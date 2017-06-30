import Math
import traceback
from Avatar import PlayerAvatar
from AvatarInputHandler import mathUtils
from Vehicle import Vehicle
from functools import partial

import BigWorld
import PYmodsCore
from vehicle_systems.CompoundAppearance import CompoundAppearance
from vehicle_systems.tankStructure import TankPartNames, TankNodeNames
from .. import g_config

dynamic_db = {}


def create(vehicleID, vDesc, visible=False):
    try:
        dynamic_db[vehicleID] = OS_dyn = {part: {'model': None} for part in TankPartNames.ALL[1:]}
        OS_dyn['loaded'] = False
        OS_dyn['entered'] = False
        OS_dyn['loading'] = True
        sname = g_config.OSDesc['dynamic'].name
        resList = []
        for modelName in TankPartNames.ALL[1:]:
            modelPath = getattr(vDesc, modelName)['models']['undamaged'].replace(
                'vehicles/', 'vehicles/skins/models/%s/vehicles/' % sname)
            resList.append(modelPath)
        BigWorld.loadResourceListBG(tuple(resList), partial(onLoad, vehicleID, visible))
    except StandardError:
        traceback.print_exc()
        print vDesc.name


def onLoad(vehicleID, visible, resourceRefs):
    if vehicleID not in dynamic_db:
        return
    OS_dyn = dynamic_db[vehicleID]
    OS_dyn['loading'] = False
    OS_dyn['loaded'] = True
    failList = []
    failed = resourceRefs.failedIDs
    resourceItems = resourceRefs.items()
    for idx, modelName in enumerate(TankPartNames.ALL[1:]):
        try:
            modelPath, model = resourceItems[idx]
            if modelPath not in failed and model is not None:
                moduleDict = OS_dyn[modelName]
                moduleDict['model'] = model
                moduleDict['model'].visible = False
            else:
                failList.append(modelPath)
        except IndexError as e:
            print e
            print idx, resourceItems
    if failList:
        print 'RemodEnabler: dynamic skin load failed: models not found:'
        OS_dyn['loaded'] = False
        print failList
    if OS_dyn['entered']:
        attach(vehicleID, visible)


def attach(vehicleID, visible=False):
    if vehicleID not in dynamic_db:
        return
    if not dynamic_db[vehicleID]['loaded']:
        if dynamic_db[vehicleID]['loading']:
            dynamic_db[vehicleID]['entered'] = True
        return
    vEntity = BigWorld.entity(vehicleID)
    if vEntity is None:
        return
    if hasattr(vEntity, 'appearance'):
        compoundModel = vEntity.appearance.compoundModel
    else:
        compoundModel = vEntity.model
    OS_dyn = dynamic_db[vehicleID]
    scaleMat = mathUtils.createIdentityMatrix()
    scaleMat.setScale(Math.Vector3(1.025))
    for modelName in TankPartNames.ALL[1:]:
        moduleDict = OS_dyn[modelName]
        if moduleDict['model'] is not None:
            if moduleDict['model'] not in vEntity.models:
                try:
                    if modelName == TankPartNames.GUN:
                        modelName = TankNodeNames.GUN_INCLINATION
                    compoundModel.node(modelName).attach(moduleDict['model'], scaleMat)
                except StandardError:
                    if g_config.data['isDebug']:
                        traceback.print_exc()
            moduleDict['model'].visible = visible


def detach(vehicleID):
    if vehicleID in dynamic_db:
        OS_dyn = dynamic_db[vehicleID]
        if not OS_dyn['loaded']:
            return
        OS_dyn['loaded'] = False
        vEntity = BigWorld.entity(vehicleID)
        if vEntity is None:
            return
        for moduleName in TankPartNames.ALL[1:]:
            moduleDict = OS_dyn[moduleName]
            if moduleDict['model'] is not None:
                moduleDict['model'].visible = False


def destroy(vehicleID):
    try:
        if vehicleID in dynamic_db:
            detach(vehicleID)
            del dynamic_db[vehicleID]
    except StandardError:
        traceback.print_exc()


@PYmodsCore.overrideMethod(CompoundAppearance, 'onVehicleHealthChanged')
def new_oVHC(base, self, showEffects=True):
    vehicle = self._CompoundAppearance__vehicle
    if not vehicle.isAlive():
        destroy(vehicle.id)
    base(self, showEffects)


@PYmodsCore.overrideMethod(Vehicle, 'startVisual')
def new_startVisual(base, self):
    base(self)
    if self.isStarted and self.isAlive() and g_config.data['enabled']:
        BigWorld.callback(0.1, partial(attach, self.id))


@PYmodsCore.overrideMethod(PlayerAvatar, 'vehicle_onLeaveWorld')
def new_vehicle_onLeaveWorld(base, self, vehicle):
    if vehicle.isStarted:
        destroy(vehicle.id)
    base(self, vehicle)


@PYmodsCore.overrideMethod(PlayerAvatar, 'targetFocus')
def new_targetFocus(base, self, entity):
    base(self, entity)
    if entity in self._PlayerAvatar__vehicles:
        try:
            for vehicleID in dynamic_db:
                if dynamic_db[vehicleID]['loaded']:
                    for moduleName in TankPartNames.ALL[1:]:
                        model = dynamic_db[vehicleID][moduleName]['model']
                        if model is not None:
                            model.visible = vehicleID == entity.id
        except StandardError:
            traceback.print_exc()


@PYmodsCore.overrideMethod(PlayerAvatar, 'targetBlur')
def new_targetBlur(base, self, prevEntity):
    base(self, prevEntity)
    if prevEntity in self._PlayerAvatar__vehicles:
        try:
            for vehicleID in dynamic_db:
                if dynamic_db[vehicleID]['loaded']:
                    for moduleName in TankPartNames.ALL[1:]:
                        model = dynamic_db[vehicleID][moduleName]['model']
                        if model is not None:
                            model.visible = False
        except StandardError:
            traceback.print_exc()
