import BigWorld
import Math
import math_utils
import traceback
from OpenModsCore import events, overrideMethod
from Vehicle import Vehicle
from adisp import adisp_async, adisp_process
from functools import partial
from gui.hangar_vehicle_appearance import HangarVehicleAppearance
from vehicle_systems.CompoundAppearance import CompoundAppearance

dynamic_db = {}


@adisp_process
def create(vehicleID, mod, mode, models):
    resList = []
    vehEntry = dynamic_db.setdefault(vehicleID, {})
    data = vehEntry.get(mod)
    if data is None:
        vehEntry[mod] = data = {
            'models': {modelPath: {'model': None, 'nodeName': nodeName} for modelPath, nodeName in models},
            'loaded': False, 'entered': False, 'mode': mode}
        for modelPath, _ in models:
            resList.append(modelPath)
    else:
        for modelPath in data['models'].keys():
            if not any(modelPath == info[0] for info in models):
                modelDict = data['models'][modelPath]
                model = modelDict['model']
                if model is not None:
                    model.visible = False
                    if 'motor' in modelDict:
                        model.delMotor(modelDict['motor'])
                        BigWorld.delModel(model)
                del data['models'][modelPath]
        for modelPath, nodeName in models:
            if modelPath not in data['models']:
                data['models'][modelPath] = {'model': None, 'nodeName': nodeName}
                data.update({'loaded': False})
                resList.append(modelPath)
    resourceRefs = yield adisp_async(lambda callback: BigWorld.loadResourceListBG(tuple(resList), callback))()
    if vehicleID not in dynamic_db:
        return
    data['loaded'] = True
    failList = []
    failed = resourceRefs.failedIDs
    resourceItems = resourceRefs.items()
    for modelPath in resList:
        if modelPath in failed:
            failList.append(modelPath)
            continue
        res = (None, None)
        for resItem in resourceItems:
            if resItem[0] == modelPath:
                res = resItem
                break
        if res[1] is not None:
            modelPath, model = res
            modelDict = data['models'][modelPath]
            modelDict['model'] = model
            modelDict['model'].visible = False
    if failList:
        data['loaded'] = False
        print mod, 'models load failed: models not found:', failList
    if data['entered']:
        attach(vehicleID, mod)


def attach(vehicleID, modID=None, visible=False):
    if vehicleID not in dynamic_db:
        return
    for mod, data in dynamic_db[vehicleID].iteritems():
        if modID is not None and modID != mod:
            continue
        data['entered'] = True
        if not data['loaded']:
            return
        vEntity = BigWorld.entity(vehicleID)
        if vEntity is None:
            return
        compoundModel = vEntity.model
        scaleMat = math_utils.createIdentityMatrix()
        attachMode = data['mode']
        if 'scale' in attachMode:
            scaleMat.setScale(Math.Vector3(1.025))
        for modelDict in data['models'].itervalues():
            model = modelDict['model']
            if model is not None:
                if 'attach' in attachMode:
                    if 'entity' in attachMode:
                        vEntity.addModel(model)
                    try:
                        compoundModel.node(modelDict['nodeName']).attach(model, scaleMat)
                    except StandardError:
                        traceback.print_exc()
                elif 'motor' in attachMode:
                    if model not in BigWorld.models():
                        modelDict['motor'] = motor = BigWorld.Servo(
                            math_utils.MatrixProviders.product(compoundModel.node(modelDict['nodeName']), scaleMat))
                        model.addMotor(motor)
                        BigWorld.addModel(model)
                model.visible = visible


def detach(vehicleID, action, modID=None, visible=False):
    if vehicleID not in dynamic_db:
        return
    for mod, data in dynamic_db[vehicleID].items():
        if modID is not None and mod != modID:
            continue
        if not data['loaded']:
            continue
        if 'destroy' in action:
            data['loaded'] = False
        for modelDict in data['models'].itervalues():
            model = modelDict['model']
            if model is not None:
                model.visible = visible
                if 'destroy' in action:
                    if 'motor' in modelDict:
                        model.delMotor(modelDict['motor'])
                        BigWorld.delModel(model)
                    elif 'entity' in data['mode']:
                        vEntity = BigWorld.entity(vehicleID)
                        if vEntity:
                            vEntity.delModel(model)
    if 'destroy' in action:
        del dynamic_db[vehicleID]


@overrideMethod(CompoundAppearance, 'onVehicleHealthChanged')
def new_oVHC(base, self, *a, **k):
    vehicle = self._vehicle
    if not vehicle.isAlive():
        detach(vehicle.id, 'destroy')
    return base(self, *a, **k)


@overrideMethod(Vehicle, 'startVisual')
def new_startVisual(base, self):
    base(self)
    if self.isStarted and self.isAlive():
        BigWorld.callback(0.1, partial(attach, self.id))


@overrideMethod(HangarVehicleAppearance, '__setupModel')
def new_setupModel(base, self, buildIdx):
    base(self, buildIdx)
    attach(self.id)


@overrideMethod(Vehicle, 'stopVisual')
def new_vehicle_onLeaveWorld(base, self, *a, **k):
    if self.isStarted:
        detach(self.id, 'visible')
    return base(self, *a, **k)


@events.PlayerAvatar.destroyGUI.before
def destroyGUI(*_, **__):
    for vehicleID in dynamic_db.keys():
        detach(vehicleID, 'destroy')


@overrideMethod(HangarVehicleAppearance, 'refresh')
def new_refresh(base, self, *a, **k):
    detach(self._HangarVehicleAppearance__vEntity.id, 'destroy')
    return base(self, *a, **k)


@overrideMethod(HangarVehicleAppearance, 'recreate')
def new_recreate(base, self, *a, **k):
    detach(self._HangarVehicleAppearance__vEntity.id, 'destroy')
    return base(self, *a, **k)


@overrideMethod(HangarVehicleAppearance, 'remove')
def new_remove(base, self, *a, **k):
    detach(self._HangarVehicleAppearance__vEntity.id, 'destroy')
    return base(self, *a, **k)


@overrideMethod(HangarVehicleAppearance, 'destroy')
def new_destroy(base, self, *a, **k):
    detach(self._HangarVehicleAppearance__vEntity.id, 'destroy')
    return base(self, *a, **k)
