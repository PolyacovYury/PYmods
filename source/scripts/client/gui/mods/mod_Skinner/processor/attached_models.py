import BigWorld
import Math
import traceback
from AvatarInputHandler import mathUtils
from PYmodsCore import overrideMethod, events
from Vehicle import Vehicle
from functools import partial
from gui.hangar_vehicle_appearance import HangarVehicleAppearance
from vehicle_systems.CompoundAppearance import CompoundAppearance
from .. import g_config

dynamic_db = {}


def create(vehicleID, mod, mode, models, visible=False):
    try:
        resList = []
        vehEntry = dynamic_db.setdefault(vehicleID, {})
        if mod not in vehEntry:
            vehEntry[mod] = {
                'models': {modelPath: {'model': None, 'nodeName': nodeName} for modelPath, nodeName in models},
                'loaded': False, 'entered': False, 'loading': True, 'mode': mode, 'visible': visible}
            for modelPath, _ in models:
                resList.append(modelPath)
        else:
            for modelPath in vehEntry[mod]['models'].keys():
                if not any(modelPath == info[0] for info in models):
                    modelDict = vehEntry[mod]['models'][modelPath]
                    model = modelDict['model']
                    if model is not None:
                        model.visible = visible
                        if 'motor' in modelDict:
                            model.delMotor(modelDict['motor'])
                            BigWorld.delModel(model)
                    del vehEntry[mod]['models'][modelPath]
            for modelPath, nodeName in models:
                if modelPath not in vehEntry[mod]['models']:
                    vehEntry[mod]['models'][modelPath] = {'model': None, 'nodeName': nodeName}
                    vehEntry[mod].update({'loaded': False, 'entered': False, 'loading': True})
                    resList.append(modelPath)
        BigWorld.loadResourceListBG(tuple(resList), partial(onLoad, vehicleID, mod, resList, visible))
    except StandardError:
        traceback.print_exc()


def onLoad(vehicleID, mod, models, visible, resourceRefs):
    if vehicleID not in dynamic_db:
        return
    dyn = dynamic_db[vehicleID][mod]
    dyn['loading'] = False
    dyn['loaded'] = True
    failList = []
    failed = resourceRefs.failedIDs
    resourceItems = resourceRefs.items()
    for modelPath in models:
        if modelPath not in failed:
            res = (None, None)
            for resItem in resourceItems:
                if resItem[0] == modelPath:
                    res = resItem
                    break
            if res[1] is not None:
                modelPath, model = res
                modelDict = dyn['models'][modelPath]
                modelDict['model'] = model
                modelDict['model'].visible = False
        else:
            failList.append(modelPath)
    if failList:
        dyn['loaded'] = False
        print g_config.ID + ':', mod, 'models load failed: models not found:', failList
    if dyn['entered']:
        attach(vehicleID, mod, visible)


def attach(vehicleID, modID=None, visible=False):
    if vehicleID not in dynamic_db:
        return
    for mod, dyn in dynamic_db[vehicleID].iteritems():
        if modID is not None and modID != mod:
            continue
        dyn['entered'] = True
        if not dyn['loaded']:
            return
        vEntity = BigWorld.entity(vehicleID)
        if vEntity is None:
            return
        compoundModel = vEntity.model
        scaleMat = mathUtils.createIdentityMatrix()
        attachMode = dyn['mode']
        if 'scale' in attachMode:
            scaleMat.setScale(Math.Vector3(1.025))
        for modelDict in dyn['models'].itervalues():
            model = modelDict['model']
            if model is not None:
                if 'attach' in attachMode:
                    try:
                        compoundModel.node(modelDict['nodeName']).attach(model, scaleMat)
                    except StandardError:
                        if g_config.data['isDebug']:
                            traceback.print_exc()
                elif 'motor' in attachMode:
                    if model not in BigWorld.models():
                        modelDict['motor'] = motor = BigWorld.Servo(
                            mathUtils.MatrixProviders.product(compoundModel.node(modelDict['nodeName']), scaleMat))
                        model.addMotor(motor)
                        BigWorld.addModel(model)
                model.visible = visible and dyn['visible']


def detach(vehicleID, mode='visible', modID=None, visible=False):
    if vehicleID in dynamic_db:
        for mod, dyn in dynamic_db[vehicleID].items():
            if modID is not None and mod != modID:
                continue
            if not dyn['loaded']:
                continue
            if 'destroy' in mode:
                dyn['loaded'] = False
            for modelDict in dyn['models'].itervalues():
                model = modelDict['model']
                if model is not None:
                    model.visible = visible
                    if 'destroy' in mode and 'motor' in modelDict:
                        model.delMotor(modelDict['motor'])
                        BigWorld.delModel(model)
        if 'destroy' in mode:
            del dynamic_db[vehicleID]


def destroy_all():
    for vehicleID in dynamic_db.keys():
        detach(vehicleID, 'destroy')


@overrideMethod(CompoundAppearance, 'onVehicleHealthChanged')
def new_oVHC(base, self, *args, **kwargs):
    vehicle = self._CompoundAppearance__vehicle
    if not vehicle.isAlive():
        detach(vehicle.id, 'destroy')
    base(self, *args, **kwargs)


@overrideMethod(Vehicle, 'startVisual')
def new_startVisual(base, self):
    base(self)
    if self.isStarted and self.isAlive() and g_config.data['enabled']:
        BigWorld.callback(0.1, partial(attach, self.id, visible=True))


@overrideMethod(Vehicle, 'stopVisual')
def new_vehicle_onLeaveWorld(base, self, *args, **kwargs):
    if self.isStarted:
        detach(self.id)
    base(self, *args, **kwargs)


@events.PlayerAvatar.destroyGUI.before
def destroyGUI(*_, **__):
    destroy_all()


@overrideMethod(HangarVehicleAppearance, 'refresh')
def new_refresh(base, self, *args, **kwargs):
    detach(self._HangarVehicleAppearance__vEntity.id, 'destroy')
    base(self, *args, **kwargs)


@overrideMethod(HangarVehicleAppearance, 'recreate')
def new_recreate(base, self, *args, **kwargs):
    detach(self._HangarVehicleAppearance__vEntity.id, 'destroy')
    base(self, *args, **kwargs)


@overrideMethod(HangarVehicleAppearance, 'remove')
def new_remove(base, self, *args, **kwargs):
    detach(self._HangarVehicleAppearance__vEntity.id, 'destroy')
    base(self, *args, **kwargs)


@overrideMethod(HangarVehicleAppearance, 'destroy')
def new_destroy(base, self, *args, **kwargs):
    detach(self._HangarVehicleAppearance__vEntity.id, 'destroy')
    base(self, *args, **kwargs)
