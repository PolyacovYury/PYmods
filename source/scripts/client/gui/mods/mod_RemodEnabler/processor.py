import BigWorld
from HeroTank import HeroTank
from PYmodsCore import overrideMethod, refreshCurrentVehicle
from gui import SystemMessages
from gui.Scaleform.daapi.settings.views import VIEW_ALIAS
from gui.Scaleform.framework.entities.View import ViewKey
from gui.app_loader import g_appLoader
from gui.customization import CustomizationService
from gui.hangar_vehicle_appearance import HangarVehicleAppearance
from gui.shared.gui_items.customization.outfit import Outfit
from items.vehicles import CompositeVehicleDescriptor as CompVDesc
from vehicle_systems import appearance_cache, camouflages
from vehicle_systems.tankStructure import TankPartNames
from . import remods, g_config


def debugOutput(xmlName, vehName, playerName, modelsSet, modelDesc):
    if not g_config.data['isDebug']:
        return
    info = ''
    header = g_config.ID + ': %s (%s)' % (xmlName, vehName)
    if playerName is not None:
        header += ', player: ' + playerName
    if modelsSet != 'default':
        header += ', modelsSet: ' + modelsSet
    if modelDesc is not None:
        info = 'modelDesc: ' + modelDesc['name']
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
    xmlName = vDesc.name.split(':')[1].lower()
    modelDesc = g_config.findModelDesc(xmlName, currentTeam, isinstance(BigWorld.entity(vehicleID), HeroTank))
    if modelDesc is not None and vDesc.chassis.generalWheelsAnimatorConfig is not None:
        print g_config.ID + ':', (
            'WARNING: wheeled vehicles are NOT processed. At least until WG moves params processing out of Vehicular.')
        if xmlName in modelDesc['whitelist']:
            modelDesc['whitelist'].remove(xmlName)
        g_config.modelsData['selected'][currentTeam].pop(xmlName, None)
        SystemMessages.pushMessage(g_config.i18n['UI_install_wheels_unsupported'], SystemMessages.SM_TYPE.Warning)
        modelDesc = None
    return modelDesc, playerName


def applyModelDesc(vDesc, modelDesc, modelsSet, playerName):
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
            remods.apply(descr, modelDesc, modelsSet)
        if not g_config.collisionMode:
            message = g_config.i18n['UI_install_remod'] + '<b>' + modelDesc['name'] + '</b>.\n' + modelDesc['message']
    if message is not None and playerName is None:
        SystemMessages.pushMessage('temp_SM' + message, SystemMessages.SM_TYPE.CustomizationForGold)
    debugOutput(xmlName, vehName, playerName, modelsSet, modelDesc)
    vDesc.modelDesc = modelDesc


@overrideMethod(appearance_cache._AppearanceCache, '_AppearanceCache__cacheApperance')
def new_cacheAppearance(base, self, vId, info, *args, **kwargs):
    if g_config.data['enabled']:
        outfitComponent = camouflages.getOutfitComponent(info.outfitCD)
        outfit = Outfit(component=outfitComponent)
        player = BigWorld.player()
        forceHistorical = player.isHistoricallyAccurate and player.playerVehicleID != vId and not outfit.isHistorical()
        outfit = Outfit() if forceHistorical else outfit
        modelDesc, playerName = getModelDescInfo(vId, info.typeDescr, 'battle')
        applyModelDesc(info.typeDescr, modelDesc, outfit.modelsSet or 'default', playerName)
    return base(self, vId, info, *args, **kwargs)


@overrideMethod(HangarVehicleAppearance, '_HangarVehicleAppearance__startBuild')
def new_startBuild(base, self, vDesc, vState):
    if g_config.data['enabled']:
        modelDesc, playerName = getModelDescInfo(self._HangarVehicleAppearance__vEntity.id, vDesc, 'hangar')
        view = g_appLoader.getDefLobbyApp().containerManager.getViewByKey(ViewKey(VIEW_ALIAS.LOBBY_CUSTOMIZATION))
        if getattr(vDesc, 'modelDesc', None) is not None and modelDesc is not None and view is not None:
            SystemMessages.pushMessage(g_config.i18n['UI_install_customization'], SystemMessages.SM_TYPE.Warning)
            vDesc.modelDesc = None
        else:
            applyModelDesc(vDesc, modelDesc, self._HangarVehicleAppearance__outfit.modelsSet or 'default', playerName)
    base(self, vDesc, vState)


@overrideMethod(CustomizationService, 'showCustomization')
def new_showCustomization(base, *a, **kw):
    if g_config.data['enabled']:
        BigWorld.callback(4, refreshCurrentVehicle)
    return base(*a, **kw)
