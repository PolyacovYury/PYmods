import BigWorld
import PYmodsCore
import traceback
from HeroTank import HeroTank
from gui import SystemMessages
from gui.hangar_vehicle_appearance import HangarVehicleAppearance
from items.vehicles import CompositeVehicleDescriptor
from vehicle_systems import appearance_cache
from vehicle_systems.tankStructure import TankPartNames
from . import remods, g_config


def debugOutput(xmlName, vehName, playerName, modelDesc):
    if not g_config.data['isDebug']:
        return
    info = ''
    header = g_config.ID + ': %s (%s)' % (xmlName, vehName)
    if playerName is not None:
        header += ', player: ' + playerName
    if modelDesc is not None:
        info = 'modelDesc: ' + modelDesc['name']
    if info:
        print header + ' processed:', info


def vDesc_process(vehicleID, vDesc, mode):
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
        return
    xmlName = vDesc.name.split(':')[1].lower()
    modelDesc = g_config.findModelDesc(xmlName, currentTeam, isinstance(BigWorld.entity(vehicleID), HeroTank))
    vDesc.installComponent(vDesc.chassis.compactDescr)
    vDesc.installComponent(vDesc.gun.compactDescr)
    if len(vDesc.type.hulls) == 1:
        vDesc.hull = vDesc.type.hulls[0]
    for descr in (vDesc,) if not isinstance(vDesc, CompositeVehicleDescriptor) else (
            vDesc.defaultVehicleDescr, vDesc.siegeVehicleDescr):
        for partName in TankPartNames.ALL + ('engine',):
            try:
                setattr(descr, partName, getattr(descr, partName).copy())
                part = getattr(descr, partName)
                if getattr(part, 'modelsSets', None) is not None:
                    part.modelsSets = part.modelsSets.copy()
            except StandardError:
                traceback.print_exc()
                print partName
    message = None
    vehNation, vehName = vDesc.chassis.models.undamaged.split('/')[1:3]
    if modelDesc is not None:
        if vDesc.chassis.generalWheelsAnimatorConfig is not None:
            print g_config.ID + ':', (
                'WARNING: wheeled vehicles are NOT processed. At least until WG moves params processing out of Vehicular, '
                'which is an inaccessible part of game engine.')
            if xmlName in modelDesc['whitelist']:
                modelDesc['whitelist'].remove(xmlName)
            g_config.modelsData['selected'][currentTeam].pop(xmlName, None)
            SystemMessages.pushMessage(g_config.i18n['UI_install_wheels_unsupported'], SystemMessages.SM_TYPE.Warning)
            modelDesc = None
        else:
            for descr in (vDesc,) if not isinstance(vDesc, CompositeVehicleDescriptor) else (
                    vDesc._CompositeVehicleDescriptor__vehicleDescr, vDesc._CompositeVehicleDescriptor__siegeDescr):
                remods.apply(descr, modelDesc)
            if not g_config.collisionMode:
                message = g_config.i18n['UI_install_remod'] + '<b>' + modelDesc['name'] + '</b>.\n' + modelDesc['message']
    if message is not None and mode == 'hangar':
        SystemMessages.pushMessage('temp_SM' + message, SystemMessages.SM_TYPE.CustomizationForGold)
    debugOutput(xmlName, vehName, playerName, modelDesc)
    vDesc.modelDesc = modelDesc
    return modelDesc


@PYmodsCore.overrideMethod(appearance_cache._AppearanceCache, '_AppearanceCache__cacheApperance')
def new_cacheAppearance(base, self, vId, info, *args, **kwargs):
    if g_config.data['enabled']:
        vDesc_process(vId, info.typeDescr, 'battle')
    return base(self, vId, info, *args, **kwargs)


@PYmodsCore.overrideMethod(HangarVehicleAppearance, '_HangarVehicleAppearance__startBuild')
def new_startBuild(base, self, vDesc, vState):
    if g_config.data['enabled']:
        vDesc_process(self._HangarVehicleAppearance__vEntity.id, vDesc, 'hangar')
    base(self, vDesc, vState)
