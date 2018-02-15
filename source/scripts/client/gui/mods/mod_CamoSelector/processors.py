import BigWorld
import items.vehicles
from Account import Account
from Avatar import PlayerAvatar
from CurrentVehicle import g_currentVehicle
from PYmodsCore import overrideMethod
from gui import g_tankActiveCamouflage
from gui.ClientHangarSpace import OutfitComponent, _VehicleAppearance
from gui.Scaleform.daapi.view.lobby.customization.shared import SEASON_TYPE_TO_NAME
from gui.Scaleform.framework import ViewTypes
from gui.Scaleform.genConsts.SEASONS_CONSTANTS import SEASONS_CONSTANTS
from gui.app_loader import g_appLoader
from gui.shared.gui_items import GUI_ITEM_TYPE
from gui.shared.gui_items.customization.outfit import Outfit
from helpers import dependency
from items.components.c11n_constants import SeasonType
from skeletons.gui.shared import IItemsCache
from vehicle_systems.CompoundAppearance import CompoundAppearance
from vehicle_systems.tankStructure import TankPartNames
from .settings import g_config
from .settings.shared import RandMode, SEASON_NAME_TO_TYPE, TeamMode


def applyCache(outfit, season, vehName, vehCache):
    season = SEASON_TYPE_TO_NAME[season]
    itemsCache = dependency.instance(IItemsCache)
    camouflages = items.vehicles.g_cache.customization20().camouflages
    seasonConfig = vehCache.get(season, {})
    applied = False
    cleaned = False
    for areaName in seasonConfig.keys():
        try:
            areaId = TankPartNames.getIdx(areaName)
        except Exception as e:
            print '%s: exception while reading camouflages cache for %s in %s: %s' % (
                g_config.ID, vehName, areaName, e.message)
            continue
        slot = outfit.getContainer(areaId).slotFor(GUI_ITEM_TYPE.CAMOUFLAGE)
        if not seasonConfig[areaName]:
            slot.remove(0)
            continue
        camoID, paletteIdx, scale = seasonConfig[areaName]
        if camoID not in camouflages:
            print '%s: wrong camouflage ID for %s: %s' % (g_config.ID, areaName, camoID)
            del seasonConfig[areaName]
            continue
        item = itemsCache.items.getItemByCD(camouflages[camoID].compactDescr)
        if paletteIdx > len(item.palettes):
            print '%s: wrong palette idx for %s camouflage: %s (available: %s)' % (
                g_config.ID, areaName, paletteIdx, range(len(item.palettes)))
            del seasonConfig[areaName]
            continue
        if scale > len(item.scales):
            print '%s: wrong scale for %s camouflage: %s (available: %s)' % (
                g_config.ID, areaName, scale, range(len(item.scales)))
        slot.set(item)
        component = slot.getComponent()
        component.palette = paletteIdx
        component.patternSize = scale
        applied = True
    if not seasonConfig:
        vehCache.pop(season, {})
        cleaned = True
    outfit.invalidate()
    return applied, cleaned


def collectCamouflageData():
    camouflages = items.vehicles.g_cache.customization20().camouflages
    g_config.camoForSeason = dict.fromkeys(SEASONS_CONSTANTS.SEASONS, {'random': [], 'ally': [], 'enemy': []})
    for camoID, camouflage in camouflages.iteritems():
        itemName, itemKey = (camouflage.userKey, 'custom') if camouflage.priceGroup == 'custom' else (
            camoID, 'remap')
        itemSeason = camouflage.season
        itemMode = RandMode.RANDOM
        itemTeam = TeamMode.BOTH
        if itemName in g_config.camouflages[itemKey]:
            camoCfg = g_config.camouflages[itemKey][itemName]
            itemMode = camoCfg.get('random_mode', itemMode)
            itemTeam = 0 | (camoCfg.get('useForAlly', True) and TeamMode.ALLY) | (
                    camoCfg.get('useForEnemy', True) and TeamMode.ENEMY)
            if 'season' in camoCfg:
                itemSeason = SeasonType.UNDEFINED
                for season in SEASONS_CONSTANTS.SEASONS:
                    if season in camoCfg['season']:
                        itemSeason |= SEASON_NAME_TO_TYPE[season]
        for season in SeasonType.COMMON_SEASONS:
            camoForSeason = g_config.camoForSeason[SEASON_TYPE_TO_NAME[season]]
            if itemSeason & season:
                if itemMode == RandMode.RANDOM:
                    camoForSeason['random'].append(camoID)
                elif itemMode == RandMode.TEAM:
                    for team in (TeamMode.ALLY, TeamMode.ENEMY):
                        if itemTeam & team:
                            camoForSeason[TeamMode.NAMES[team]].append(camoID)


def processRandomOutfit(outfit, season, vehCache, vID=None):
    if vID is not None:
        isAlly = BigWorld.player().guiSessionProvider.getArenaDP().getVehicleInfo(vID).team == BigWorld.player().team
        teamMode = 'ally' if isAlly else 'enemy'
    else:
        teamMode = None
    camoID = None
    season = SEASON_TYPE_TO_NAME[season]
    camouflages = items.vehicles.g_cache.customization20().camouflages
    itemsCache = dependency.instance(IItemsCache)
    outfitItems = set(item.id for item in outfit.items() if item and item.itemTypeID == GUI_ITEM_TYPE.CAMOUFLAGE)
    canBeUniform = len(outfitItems) <= 1
    if canBeUniform:
        camoID = None if not outfitItems else outfitItems.pop()
    for areaId, areaName in enumerate(TankPartNames.ALL):
        if not areaId:
            continue
        slot = outfit.getContainer(areaId).slotFor(GUI_ITEM_TYPE.CAMOUFLAGE)
        item = slot.getItem(0)
        if item is not None:
            continue
        if areaName in vehCache:
            if vehCache[areaName]:
                camoID, palette, patternSize = vehCache[areaName]
        else:
            if camoID is None or not g_config.data['uniformOutfit'] or not canBeUniform:
                camoForSeason = g_config.camoForSeason[season]
                if teamMode is not None and camoForSeason[teamMode]:
                    if g_config.teamCamo[teamMode] is None:
                        g_config.teamCamo[teamMode] = camoID = camoForSeason[teamMode][vID % len(camoForSeason[teamMode])]
                    else:
                        camoID = g_config.teamCamo[teamMode]
                elif camoForSeason['random']:
                    camoID = camoForSeason['random'][vID % len(camoForSeason['random'])]
            patternSize = vID % len(item.scales)
            palette = vID % len(item.palettes)
        if camoID is not None:
            item = itemsCache.items.getItemByCD(camouflages[camoID].compactDescr)
            slot.set(item)
            component = slot.getComponent()
            component.palette = palette
            component.patternSize = patternSize
            vehCache[areaName] = [camoID, palette, patternSize]
        else:
            vehCache[areaName] = []


@overrideMethod(_VehicleAppearance, '_VehicleAppearance__assembleModel')
def new_assembleModel(base, self, *a, **kw):
    result = base(self, *a, **kw)
    if not self._VehicleAppearance__isVehicleDestroyed:
        manager = g_appLoader.getDefLobbyApp().containerManager
        if manager is not None:
            container = manager.getContainer(ViewTypes.LOBBY_SUB)
            if container is not None:
                c11nView = container.getView()
                if c11nView is not None and hasattr(c11nView, 'getCurrentOutfit'):
                    outfit = c11nView.getCurrentOutfit()  # fix for HangarFreeCam
                    self.updateCustomization(outfit, OutfitComponent.ALL)
                    return result
        vehicle = g_currentVehicle.item
        vDesc = vehicle.descriptor
        if g_config.data['enabled'] and vDesc.name not in g_config.disable and not (
                vDesc.type.hasCustomDefaultCamouflage and g_config.data['disableWithDefault']):
            nationName, vehicleName = vDesc.name.split(':')
            if g_config.data['hangarCamoKind'] < 3:
                idx = g_config.data['hangarCamoKind']
                season = SeasonType.fromArenaKind(idx)
                outfit = vehicle.getOutfit(season).copy()
                g_tankActiveCamouflage[vehicle.intCD] = season
            else:
                outfit = self._VehicleAppearance__getActiveOutfit().copy()
            if not g_config.data['useBought']:
                outfit = Outfit()
            season = g_tankActiveCamouflage[vehicle.intCD]
            vehCache = g_config.camouflagesCache.get(nationName, {}).get(vehicleName, {})
            applied, cleaned = applyCache(outfit, season, vehicleName, vehCache)
            if g_config.data['doRandom'] and (not applied or cleaned or g_config.data['fillEmptySlots']):
                vehCache = g_config.hangarCamoCache.setdefault(nationName, {}).setdefault(vehicleName, {})
                processRandomOutfit(outfit, season, vehCache)
                applyCache(outfit, season, vehicleName, vehCache)
            self.updateCustomization(outfit, OutfitComponent.ALL)
    return result


@overrideMethod(CompoundAppearance, '_CompoundAppearance__getVehicleOutfit')
def new_getVehicleOutfit(base, self, *a, **kw):
    result = base(self, *a, **kw).copy()
    vDesc = self._CompoundAppearance__typeDesc
    if not self._CompoundAppearance__vehicle or not vDesc:
        return result
    if g_config.data['enabled'] and vDesc.name not in g_config.disable and not (
            vDesc.type.hasCustomDefaultCamouflage and g_config.data['disableWithDefault']):
        if not g_config.data['useBought']:
            result = Outfit()
        vID = self._CompoundAppearance__vehicle.id
        season = SeasonType.fromArenaKind(BigWorld.player().arena.arenaType.vehicleCamouflageKind)
        nationName, vehicleName = vDesc.name.split(':')
        applied = False
        cleaned = False
        if self._CompoundAppearance__vehicle.isPlayerVehicle:
            vehCache = g_config.camouflagesCache.get(nationName, {}).get(vehicleName, {})
            applied, cleaned = applyCache(result, season, vehicleName, vehCache)
        if g_config.data['doRandom'] and (not applied or cleaned or g_config.data['fillEmptySlots']):
            vehCache = g_config.arenaCamoCache.setdefault(vID, {})
            processRandomOutfit(result, season, vehCache, vID)
            applyCache(result, season, vehicleName, vehCache)
    return result


@overrideMethod(PlayerAvatar, 'onBecomePlayer')
def new_onBecomePlayer(base, self, *args, **kwargs):
    base(self, *args, **kwargs)
    collectCamouflageData()


@overrideMethod(Account, 'onBecomeNonPlayer')
def new_onBecomePlayer(base, self):
    base(self)
    collectCamouflageData()
    g_config.hangarCamoCache.clear()
    g_config.teamCamo = dict.fromkeys(('ally', 'enemy'))
