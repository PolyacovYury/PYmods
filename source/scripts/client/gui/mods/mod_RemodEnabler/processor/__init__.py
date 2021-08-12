import BigWorld
import Event
import Math
import math_utils
from HangarVehicle import HangarVehicle
from PYmodsCore import overrideMethod, refreshCurrentVehicle
from VehicleGunRotator import MatrixAnimator
from common_tank_appearance import CommonTankAppearance
from gui import SystemMessages
from gui.Scaleform.daapi.settings.views import VIEW_ALIAS
from gui.Scaleform.daapi.view.lobby.customization.main_view import MainView
from gui.Scaleform.framework.entities.View import ViewKey
from gui.hangar_vehicle_appearance import HangarVehicleAppearance
from gui.shared.personality import ServicesLocator as SL
from gui.simple_turret_rotator import SimpleTurretRotator as WGRotator, logger
from items.vehicles import CompositeVehicleDescriptor as CompVDesc
from vehicle_systems.tankStructure import TankPartNames
from . import remods
from .. import g_config


def debugOutput(xmlName, vehName, playerName, modelsSet, modelDesc):
    if not g_config.data['isDebug']:
        return
    info = ''
    header = g_config.LOG, '%s (%s)' % (xmlName, vehName)
    if playerName is not None:
        header += ', player: ' + playerName
    if modelsSet != 'default':
        header += ', modelsSet: ' + modelsSet
    if modelDesc is not None:
        info = 'modelDesc: ' + modelDesc.name
    if info:
        print header, 'processed:', info
    else:
        print header, 'processed.'


def getModelDescInfo(vehicleID, vDesc, mode):
    currentTeam = 'enemy'
    if mode == 'battle':
        player = BigWorld.player()
        vehInfoVO = player.guiSessionProvider.getArenaDP().getVehicleInfo(vehicleID)
        playerName = vehInfoVO.player.name
        if vehicleID == player.playerVehicleID:
            currentTeam = 'player'
        elif vehInfoVO.team == player.team:
            currentTeam = 'ally'
    elif mode == 'hangar':
        currentTeam = g_config.currentTeam
        playerName = None
    else:
        return None, None
    return (g_config.findModelDesc(vDesc.name.split(':')[1].lower(), currentTeam, isinstance(
        BigWorld.entity(vehicleID), HangarVehicle))), playerName


def applyModelDesc(vDesc, modelDesc, outfit, playerName):
    xmlName = vDesc.name.split(':')[1].lower()
    vDesc.installComponent(vDesc.chassis.compactDescr)
    vDesc.installComponent(vDesc.gun.compactDescr)
    if len(vDesc.type.hulls) == 1:
        vDesc.hull = vDesc.type.hulls[0]
    message = None
    vehName = vDesc.chassis.models.undamaged.split('/')[2]
    if modelDesc is not None:
        for descr in (vDesc,) if not isinstance(vDesc, CompVDesc) else (vDesc.defaultVehicleDescr, vDesc.siegeVehicleDescr):
            for partName in TankPartNames.ALL + ('engine',):
                setattr(descr, partName, getattr(descr, partName).copy())
                part = getattr(descr, partName)
                if getattr(part, 'modelsSets', None) is not None:
                    part.modelsSets = part.modelsSets.copy()
            remods.apply(descr, modelDesc, outfit)
        if not g_config.collisionMode:
            message = g_config.i18n['UI_install_remod'] + '<b>' + modelDesc.name + '</b>.'
            if modelDesc.message:
                message += '\n' + modelDesc.message
    if message is not None and playerName is None:
        SystemMessages.pushMessage('temp_SM' + message, SystemMessages.SM_TYPE.CustomizationForGold)
    debugOutput(xmlName, vehName, playerName, outfit.modelsSet or 'default', modelDesc)
    vDesc.chassis.modelsSets['RemodEnabler_modelDesc'] = modelDesc


@overrideMethod(CommonTankAppearance, 'prerequisites')
def new_prerequisites(base, self, typeDescriptor, vID, health, isCrewActive, isTurretDetached, outfitCD, *a, **k):
    if g_config.data['enabled']:
        self._CommonTankAppearance__typeDesc = typeDescriptor
        self._CommonTankAppearance__vID = vID
        outfit = self._prepareOutfit(outfitCD)
        modelDesc, playerName = getModelDescInfo(vID, typeDescriptor, 'battle')
        applyModelDesc(typeDescriptor, modelDesc, outfit, playerName)
        outfitCD = outfit.pack().makeCompDescr()
    return base(self, typeDescriptor, vID, health, isCrewActive, isTurretDetached, outfitCD, *a, **k)


@overrideMethod(CommonTankAppearance, '_onRequestModelsRefresh')
def new_onRequestModelsRefresh(base, self, *a, **k):
    if g_config.data['enabled']:
        modelDesc, playerName = getModelDescInfo(self.id, self.typeDescriptor, 'battle')
        applyModelDesc(self.typeDescriptor, modelDesc, self.outfit, playerName)
    return base(self, *a, **k)


@overrideMethod(HangarVehicleAppearance, '__startBuild')
def new_startBuild(base, self, vDesc, vState):
    if g_config.data['enabled']:
        modelDesc, playerName = getModelDescInfo(self.id, vDesc, 'hangar')
        view = SL.appLoader.getDefLobbyApp().containerManager.getViewByKey(ViewKey(VIEW_ALIAS.LOBBY_CUSTOMIZATION))
        if view is not None:
            if modelDesc is not None and vDesc.chassis.modelsSets.get('RemodEnabler_modelDesc', None) is not None:
                SystemMessages.pushMessage(g_config.i18n['UI_install_customization'], SystemMessages.SM_TYPE.Warning)
            modelDesc = None
            vDesc.chassis.modelsSets.pop('RemodEnabler_modelDesc', None)
        applyModelDesc(vDesc, modelDesc, self.outfit, playerName)
    return base(self, vDesc, vState)


@overrideMethod(MainView, '_populate')
def new_populate(base, self, *a, **kw):
    if g_config.data['enabled']:
        BigWorld.callback(0, refreshCurrentVehicle)
        BigWorld.callback(0.2, self._MainView__onVehicleChanged)
    return base(self, *a, **kw)


class SimpleTurretRotator(WGRotator):
    def __init__(
            self, compoundModel=None, currTurretYaw=0.0, _=Math.Vector3(0.0, 0.0, 0.0), __=0.0,
            easingCls=math_utils.Easing.linearEasing):
        self.__isStarted = False
        self.__turretYaw = self.__targetTurretYaw = currTurretYaw
        self.__rotationTime = 0.0
        self.__timerID = None
        self.__turretMatrixAnimator = MatrixAnimator()
        self.__easingCls = easingCls
        self.__easing = None
        if compoundModel is not None:
            self.__updateTurretMatrix(currTurretYaw, 0.0)
            compoundModel.node(TankPartNames.TURRET, self.__turretMatrixAnimator.matrix)
        else:
            logger.error('CompoundModel is not set!')
        self._eventsManager = Event.EventManager()
        self.onTurretRotationStarted = Event.Event(self._eventsManager)
        self.onTurretRotated = Event.Event(self._eventsManager)

    def __updateTurretMatrix(self, yaw, time):
        m = Math.Matrix()
        m.setRotateY(yaw)
        self.__turretMatrixAnimator.update(m, time)
        self.__turretYaw = yaw


@overrideMethod(WGRotator, '__new__')
def new(base, _, *a, **kw):
    return base(SimpleTurretRotator, *a, **kw)
