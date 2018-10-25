import BigWorld
import PYmodsCore
import traceback
from gui import SystemMessages
from gui.hangar_vehicle_appearance import HangarVehicleAppearance
from items.vehicles import CompositeVehicleDescriptor
from vehicle_systems import appearance_cache
from vehicle_systems.tankStructure import TankPartNames
from . import skins_dynamic, skins_static
from .. import g_config

try:
    from gui.mods.mod_remodenabler import g_config as re_config
except ImportError:
    re_config = None


def skins_find(curVehName, isPlayerVehicle, isAlly, skinType):
    if not g_config.skinsData['enabled']:
        return
    curTankType = 'player' if isPlayerVehicle else 'ally' if isAlly else 'enemy'
    for curSName in g_config.skinsData['priorities'][skinType][curTankType]:
        curPRecord = g_config.skinsData['models'][skinType][curSName]
        if curVehName not in curPRecord['whitelist'] and curVehName.lower() not in curPRecord['whitelist']:
            continue
        return curPRecord


def debugOutput(xmlName, vehName, playerName, staticDesc, dynamicDesc):
    if not g_config.data['isDebug']:
        return
    info = []
    header = g_config.ID + ': %s (%s)' % (xmlName, vehName)
    if playerName is not None:
        header += ', player: ' + playerName
    if staticDesc is not None:
        info.append('static skinDesc: ' + staticDesc['name'])
    if dynamicDesc is not None:
        info.append('dynamic skinDesc: ' + dynamicDesc['name'])
    if info:
        print header + ' processed:', ', '.join(info)


def vDesc_process(vehicleID, vDesc, mode):
    if mode == 'battle':
        player = BigWorld.player()
        isPlayerVehicle = vehicleID == player.playerVehicleID
        vehInfoVO = player.guiSessionProvider.getArenaDP().getVehicleInfo(vehicleID)
        playerName = vehInfoVO.player.name
        isAlly = vehInfoVO.team == player.team
    elif mode == 'hangar':
        currentMode = g_config.currentMode
        isPlayerVehicle = currentMode == 'player'
        playerName = None
        isAlly = currentMode == 'ally'
    else:
        return
    xmlName = vDesc.name.split(':')[1].lower()
    staticDesc = None
    dynamicDesc = None
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
    collisionNotVisible = re_config is None or not (re_config.collisionEnabled or re_config.collisionComparisonEnabled)
    vehNation, vehName = vDesc.chassis.models.undamaged.split('/')[1:3]
    vehDefNation = vDesc.chassis.hitTester.bspModelName.split('/')[1]
    if g_config.skinsData['found']:
        if vehNation == vehDefNation:
            dynamicDesc = skins_find(vehName, isPlayerVehicle, isAlly, 'dynamic')
            if dynamicDesc is not None:
                skins_dynamic.create(vehicleID, vDesc, dynamicDesc['name'], mode == 'hangar' and (
                        g_config.dynamicSkinEnabled and not g_config.collisionComparisonEnabled))
                if g_config.dynamicSkinEnabled and collisionNotVisible:
                    message = g_config.i18n['UI_install_skin_dynamic'] + '<b>' + dynamicDesc['name'] + '</b>.'
            staticDesc = skins_find(vehName, isPlayerVehicle, isAlly, 'static')
            if staticDesc is not None:
                skins_static.apply(vDesc, staticDesc['name'])
        elif g_config.data['isDebug']:
            print g_config.ID + ': unknown vehicle nation for', vehName + ':', vehNation
        if g_config.data['isDebug'] and (dynamicDesc is None or not g_config.dynamicSkinEnabled) and collisionNotVisible:
            if staticDesc is not None:
                message = g_config.i18n['UI_install_skin'] + '<b>' + staticDesc['name'] + '</b>.'
            else:
                message = g_config.i18n['UI_install_default']
    if message is not None and mode == 'hangar':
        SystemMessages.pushMessage('temp_SM' + message, SystemMessages.SM_TYPE.CustomizationForGold)
    debugOutput(xmlName, vehName, playerName, staticDesc, dynamicDesc)


@PYmodsCore.overrideMethod(appearance_cache._AppearanceCache, '_AppearanceCache__cacheApperance')
def new_cacheAppearance(base, self, vId, info, *args):
    if g_config.data['enabled'] and getattr(info.typeDescr, 'modelDesc', None) is None:
        vDesc_process(vId, info.typeDescr, 'battle')
    return base(self, vId, info, *args)


@PYmodsCore.overrideMethod(HangarVehicleAppearance, '_HangarVehicleAppearance__startBuild')
def new_startBuild(base, self, vDesc, vState):
    if g_config.data['enabled'] and getattr(vDesc, 'modelDesc', None) is None:
        vDesc_process(self._HangarVehicleAppearance__vEntity.id, vDesc, 'hangar')
    base(self, vDesc, vState)
