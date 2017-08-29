import BigWorld
import PYmodsCore
import traceback
from CurrentVehicle import _RegularPreviewAppearance, g_currentPreviewVehicle
from gui import SystemMessages
from gui.ClientHangarSpace import _VehicleAppearance
from items.vehicles import CompositeVehicleDescriptor
from vehicle_systems import appearance_cache
from vehicle_systems.tankStructure import TankPartNames
from .. import g_config
from . import remods, skins_dynamic, skins_static


@PYmodsCore.overrideMethod(_RegularPreviewAppearance, 'refreshVehicle')
def new_refreshVehicle(base, self, item):
    if item and (g_config.OMDesc is not None or any(g_config.OSDesc.values())):
        item = g_currentPreviewVehicle._CurrentPreviewVehicle__item = g_currentPreviewVehicle._CurrentPreviewVehicle__getPreviewVehicle(item.intCD)
    base(self, item)


def skins_find(curVehName, isPlayerVehicle, isAlly, currentMode='battle', skinType='static'):
    g_config.OSDesc[skinType] = None
    if not g_config.OS.enabled:
        return
    curTankType = 'Player' if isPlayerVehicle else 'Ally' if isAlly else 'Enemy'
    if currentMode != 'remod':
        for curSName in g_config.OS.priorities[skinType][curTankType]:
            curPRecord = g_config.OS.models[skinType][curSName]
            if curVehName not in curPRecord.whitelist and curVehName.lower() not in curPRecord.whitelist:
                continue
            else:
                g_config.OSDesc[skinType] = curPRecord
                break


def debugOutput(xmlName, vehName, playerName=None):
    if not g_config.data['isDebug']:
        return
    info = []
    header = 'RemodEnabler: %s (%s)' % (xmlName, vehName)
    if playerName is not None:
        header += ', player: %s' % playerName
    if g_config.OMDesc is not None:
        info.append('OMDesc: %s' % g_config.OMDesc.name)
    if g_config.OSDesc['static'] is not None:
        info.append('static OSDesc: %s' % g_config.OSDesc['static'].name)
    if g_config.OSDesc['dynamic'] is not None:
        info.append('dynamic OSDesc: %s' % g_config.OSDesc['dynamic'].name)
    if info:
        print header + ' processed:', ', '.join(info)


def vDesc_process(vehicleID, vDesc, mode):
    if mode == 'battle':
        currentMode = mode
        isPlayerVehicle = vehicleID == BigWorld.player().playerVehicleID
        playerName = BigWorld.player().arena.vehicles.get(vehicleID)['name']
        isAlly = BigWorld.player().arena.vehicles.get(vehicleID)['team'] == BigWorld.player().team
    elif mode == 'hangar':
        currentMode = g_config.data['currentMode']
        isPlayerVehicle = currentMode == 'player'
        playerName = None
        isAlly = currentMode == 'ally'
    else:
        return
    xmlName = vDesc.name.split(':')[1].lower()
    remods.find(xmlName, isPlayerVehicle, isAlly, currentMode)
    for partName in TankPartNames.ALL + ('engine',):
        for descr in (vDesc,) if not isinstance(vDesc, CompositeVehicleDescriptor) else (
                vDesc.defaultVehicleDescr, vDesc.siegeVehicleDescr):
            try:
                setattr(descr, partName, getattr(descr, partName).copy())
            except StandardError:
                traceback.print_exc()
                print partName
    message = None
    collisionNotVisible = not g_config.data['collisionEnabled'] and not g_config.data['collisionComparisonEnabled']
    vehNation, vehName = vDesc.chassis.models.undamaged.split('/')[1:3]
    vehDefNation = vDesc.chassis.hitTester.bspModelName.split('/')[1]
    if g_config.OMDesc is None:
        if vehNation == vehDefNation:
            if g_config.data['skinsFound']:
                skins_find(vehName, isPlayerVehicle, isAlly, currentMode, skinType='dynamic')
                if g_config.OSDesc['dynamic'] is not None:
                    skins_dynamic.create(vehicleID, vDesc, mode == 'hangar' and (
                        g_config.data['dynamicSkinEnabled'] and not g_config.data['collisionComparisonEnabled']))
                    if g_config.data['dynamicSkinEnabled'] and collisionNotVisible:
                        message = g_config.i18n['UI_install_skin_dynamic'] + g_config.OSDesc['dynamic'].name.join(
                            ('<b>', '</b>.'))
                skins_find(vehName, isPlayerVehicle, isAlly, currentMode)
                skins_static.apply(vDesc)
        elif g_config.data['isDebug']:
            print 'RemodEnabler: unknown vehicle nation for %s: %s' % (vehName, vehNation)
        if g_config.data['isDebug'] and (
                g_config.OSDesc['dynamic'] is None or not g_config.data['dynamicSkinEnabled']) and collisionNotVisible:
            if g_config.OSDesc['static'] is not None:
                message = g_config.i18n['UI_install_skin'] + g_config.OSDesc['static'].name.join(('<b>', '</b>.'))
            else:
                message = g_config.i18n['UI_install_default']
    else:
        for descr in (vDesc,) if not isinstance(vDesc, CompositeVehicleDescriptor) else (
                vDesc.defaultVehicleDescr, vDesc.siegeVehicleDescr):
            remods.apply(descr)
        if collisionNotVisible:
            message = g_config.i18n['UI_install_remod'] + g_config.OMDesc.name.join(
                ('<b>', '</b>.')) + '\n' + g_config.OMDesc.authorMessage
    remods.glass_create(vehicleID, vDesc, True)
    if message is not None and mode == 'hangar':
        SystemMessages.pushMessage('PYmods_SM' + message, SystemMessages.SM_TYPE.CustomizationForGold)
    debugOutput(xmlName, vehName, playerName)


@PYmodsCore.overrideMethod(appearance_cache._AppearanceCache, '_AppearanceCache__cacheApperance')
def new_cacheAppearance(base, self, vId, info, *args):
    if g_config.data['enabled']:
        vDesc_process(vId, info.typeDescr, 'battle')
    return base(self, vId, info, *args)


@PYmodsCore.overrideMethod(_VehicleAppearance, '_VehicleAppearance__startBuild')
def new_startBuild(base, self, vDesc, vState):
    if g_config.data['enabled']:
        g_config.curVehicleName = vDesc.name.split(':')[1].lower()
        vDesc_process(self._VehicleAppearance__vEntityId, vDesc, 'hangar')
    base(self, vDesc, vState)
