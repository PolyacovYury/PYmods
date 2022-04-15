import BigWorld
import traceback
from DetachedTurret import DetachedTurret
from OpenModsCore import BigWorld_callback, overrideMethod
from common_tank_appearance import CommonTankAppearance
from gui import SystemMessages
from gui.hangar_vehicle_appearance import HangarVehicleAppearance
from items.vehicles import CompositeVehicleDescriptor as CompVDesc
from vehicle_systems.camouflages import prepareBattleOutfit
from vehicle_systems.tankStructure import TankPartNames
from . import skins_crash, skins_dynamic, skins_static
from .. import g_config


def skins_find(vehicleName, modelsSet, team):
    for skinType in ('static', 'dynamic'):
        if not g_config.skinsData['whitelists']:
            yield
        for skinName in g_config.skinsData['priorities'][skinType][team]:
            if (vehicleName + '/' + modelsSet).lower() in g_config.skinsData['whitelists'][skinName]:
                yield skinName
                break
        else:
            yield


def debugOutput(xmlName, vehName, playerName, modelsSet, staticSkin=None, dynamicSkin=None):
    if not g_config.data['isDebug']:
        return
    traceback.print_stack()
    info = []
    header = g_config.LOG, '%s (%s)' % (xmlName, vehName)
    if playerName is not None:
        header += ', player: ' + playerName
    if modelsSet != 'default':
        header += ', modelsSet: ' + modelsSet
    if staticSkin is not None:
        info.append('static skinDesc: ' + staticSkin)
    if dynamicSkin is not None:
        info.append('dynamic skinDesc: ' + dynamicSkin)
    if info:
        print header, 'processed:', ', '.join(info)
    else:
        print header, 'processed.'


def vDesc_process(vehicleID, vDesc, is_hangar, modelsSet, isCrashed):
    if is_hangar:
        team = g_config.currentTeam
        playerName = None
    else:
        player = BigWorld.player()
        vehInfoVO = player.guiSessionProvider.getArenaDP().getVehicleInfo(vehicleID)
        playerName = vehInfoVO.player.name
        team = 'player' if vehicleID == player.playerVehicleID else 'ally' if vehInfoVO.team == player.team else 'enemy'
    vDesc.installComponent(vDesc.chassis.compactDescr)
    vDesc.installComponent(vDesc.gun.compactDescr)
    if len(vDesc.type.hulls) == 1:
        vDesc.hull = vDesc.type.hulls[0]
    for descr in (vDesc,) if not isinstance(vDesc, CompVDesc) else (vDesc.defaultVehicleDescr, vDesc.siegeVehicleDescr):
        for partName in TankPartNames.ALL + ('engine',):
            try:
                setattr(descr, partName, getattr(descr, partName).copy())
                part = getattr(descr, partName)
                if getattr(part, 'modelsSets', None) is not None:
                    part.modelsSets = part.modelsSets.copy()
            except StandardError:
                traceback.print_exc()
                print partName
        xmlName = descr.name.split(':')[1].lower()
        modelsSetDir = modelsSet
        modelPath = descr.chassis.modelsSets[modelsSet].undamaged
        if modelPath.count('/') > 5:
            vehNation, vehName, _, modelsSetDir = modelPath.split('/')[1:5]
        else:
            vehNation, vehName = modelPath.split('/')[1:3]
        vehDefNation = descr.hitTesters.chassis.bspModelName.split('/')[1]
        if not g_config.skinsData['whitelists']:
            return debugOutput(xmlName, vehName, playerName, modelsSetDir)
        message, staticSkin, dynamicSkin = None, None, None
        if vehNation == vehDefNation:
            descr.chassis.modelsSets['Skinner_dynamicData'] = []
            skins_crash.apply(descr, modelsSet, isCrashed)
            if not isCrashed:
                staticSkin, dynamicSkin = skins_find(vehName, modelsSetDir, team)
                if dynamicSkin is not None:
                    skins_dynamic.apply(descr, modelsSet, dynamicSkin)
                    if g_config.dynamicSkinEnabled and not g_config.collisionMode:
                        message = g_config.i18n['UI_install_skin_dynamic'] + '<b>' + dynamicSkin + '</b>.'
                if staticSkin is not None:
                    skins_static.apply(descr, modelsSet, staticSkin)
        elif g_config.data['isDebug']:
            print g_config.LOG, 'unknown vehicle nation for', vehName + ':', vehNation
        if g_config.data['isDebug'] and (
                dynamicSkin is None or not g_config.dynamicSkinEnabled) and not g_config.collisionMode:
            if staticSkin is not None:
                message = g_config.i18n['UI_install_skin'] + '<b>' + staticSkin + '</b>.'
            else:
                message = g_config.i18n['UI_install_default']
        if message is not None and is_hangar:
            SystemMessages.pushMessage('temp_SM' + message, SystemMessages.SM_TYPE.CustomizationForGold)
        debugOutput(xmlName, vehName, playerName, modelsSetDir, staticSkin, dynamicSkin)


@overrideMethod(CommonTankAppearance, 'prerequisites')
def new_prerequisites(base, self, typeDescriptor, vID, health, isCrewActive, isTurretDetached, outfitCD, *a, **k):
    if g_config.data['enabled'] and typeDescriptor.chassis.modelsSets.get('RemodEnabler_modelDesc', None) is None:
        self.damageState.update(health, isCrewActive, False)
        isDamaged = self.damageState.isCurrentModelDamaged
        callback = getattr(self, '_CompoundAppearance__requestModelsRefresh', None)
        if isDamaged and callback is not None and not getattr(BigWorld.player(), 'initCompleted', False):
            BigWorld_callback(1, callback)
        else:
            self._CommonTankAppearance__typeDesc = typeDescriptor
            self._CommonTankAppearance__vID = vID
            outfit = self._prepareOutfit(outfitCD)
            vDesc_process(vID, typeDescriptor, False, outfit.modelsSet or 'default', isDamaged)
    return base(self, typeDescriptor, vID, health, isCrewActive, isTurretDetached, outfitCD, *a, **k)


@overrideMethod(CommonTankAppearance, '_onRequestModelsRefresh')
def new_onRequestModelsRefresh(base, self, *a, **k):
    if g_config.data['enabled'] and self.typeDescriptor.chassis.modelsSets.get('RemodEnabler_modelDesc', None) is None:
        vDesc_process(
            self.id, self.typeDescriptor, False, self.outfit.modelsSet or 'default', self.damageState.isCurrentModelDamaged)
    return base(self, *a, **k)


@overrideMethod(DetachedTurret, '__prepareModelAssembler')
def new_prepareModelAssembler(base, self, *a, **k):
    typeDescriptor = self._DetachedTurret__vehDescr
    if g_config.data['enabled'] and typeDescriptor.chassis.modelsSets.get('RemodEnabler_modelDesc', None) is None:
        outfit = prepareBattleOutfit(self.outfitCD, typeDescriptor, self.vehicleID)
        vDesc_process(self.vehicleID, typeDescriptor, False, outfit.modelsSet or 'default', True)
    return base(self, *a, **k)


@overrideMethod(HangarVehicleAppearance, '__startBuild')
def new_startBuild(base, self, vDesc, vState):
    if g_config.data['enabled'] and vDesc.chassis.modelsSets.get('RemodEnabler_modelDesc', None) is None:
        vDesc_process(self.id, vDesc, True, self.outfit.modelsSet or 'default', vState != 'undamaged')
    return base(self, vDesc, vState)
