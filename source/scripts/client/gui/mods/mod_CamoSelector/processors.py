import BigWorld
import items.vehicles
import random
from Account import Account
from Avatar import PlayerAvatar
from CurrentVehicle import g_currentVehicle, g_currentPreviewVehicle
from PYmodsCore import overrideMethod
from gui import g_tankActiveCamouflage
from gui.customization.shared import C11N_ITEM_TYPE_MAP
from gui.hangar_vehicle_appearance import HangarVehicleAppearance
from gui.Scaleform.daapi.view.lobby.customization.shared import SEASON_TYPE_TO_NAME
from gui.Scaleform.framework import ViewTypes
from gui.Scaleform.genConsts.SEASONS_CONSTANTS import SEASONS_CONSTANTS
from gui.app_loader import g_appLoader
from gui.shared.gui_items import GUI_ITEM_TYPE, GUI_ITEM_TYPE_INDICES
from gui.shared.gui_items.customization.c11n_items import Camouflage, Paint
from gui.shared.gui_items.customization.outfit import Outfit, Area
from helpers import dependency
from items.components.c11n_constants import SeasonType
from skeletons.gui.shared import IItemsCache
from vehicle_systems.CompoundAppearance import CompoundAppearance
from vehicle_systems.tankStructure import TankPartNames
from .settings import g_config
from .settings.shared import RandMode, TeamMode

try:
    import gui.mods.mod_statpaints  # camouflage removal should work even with CamoSelector, so it has to be imported first
except ImportError:
    pass


def applyCamoCache(outfit, vehName, seasonCache):
    itemsCache = dependency.instance(IItemsCache)
    camouflages = items.vehicles.g_cache.customization20().camouflages
    applied = False
    cleaned = False
    for areaName in seasonCache.keys():
        try:
            areaId = TankPartNames.getIdx(areaName)
        except Exception as e:
            print '%s: exception while reading camouflages cache for %s in %s: %s' % (
                g_config.ID, vehName, areaName, e.message)
            continue
        slot = outfit.getContainer(areaId).slotFor(GUI_ITEM_TYPE.CAMOUFLAGE)
        if not seasonCache[areaName]:
            slot.remove(0)
            continue
        camoID, paletteIdx, scale = seasonCache[areaName]
        if camoID not in camouflages:
            print '%s: wrong camouflage ID for %s: %s' % (g_config.ID, areaName, camoID)
            del seasonCache[areaName]
            continue
        intCD = camouflages[camoID].compactDescr
        if itemsCache.items.isSynced():
            item = itemsCache.items.getItemByCD(intCD)
        else:
            item = Camouflage(intCD)
        if paletteIdx > len(item.palettes):
            print '%s: wrong palette idx for %s camouflage: %s (available: %s)' % (
                g_config.ID, areaName, paletteIdx, range(len(item.palettes)))
            del seasonCache[areaName]
            continue
        if scale > len(item.scales):
            print '%s: wrong scale for %s camouflage: %s (available: %s)' % (
                g_config.ID, areaName, scale, range(len(item.scales)))
        slot.set(item)
        component = slot.getComponent()
        component.palette = paletteIdx
        component.patternSize = scale
        applied = True
    if not seasonCache:
        cleaned = True
    outfit.invalidate()
    return applied, cleaned


def applyPlayerCache(outfit, vehName, seasonCache):
    itemsCache = dependency.instance(IItemsCache)
    for itemTypeName in seasonCache.keys():
        if itemTypeName not in ('paint', 'modification', 'emblem', 'inscription'):
            if itemTypeName != 'camo':
                print '%s: invalid item type in outfit cache for %s: %s' % (g_config.ID, vehName, itemTypeName)
                del seasonCache[itemTypeName]
            continue
        itemDB = items.vehicles.g_cache.customization20().itemTypes[C11N_ITEM_TYPE_MAP[GUI_ITEM_TYPE_INDICES[itemTypeName]]]
        for areaName in seasonCache[itemTypeName].keys():
            if itemTypeName == 'modification':
                if areaName != 'misc':
                    print '%s: wrong area name for %s modification: %s' % (g_config.ID, vehName, areaName)
                    del seasonCache[itemTypeName][areaName]
                    continue
                else:
                    areaId = Area.MISC
            else:
                try:
                    areaId = TankPartNames.getIdx(areaName)
                except Exception as e:
                    print '%s: exception while reading outfit cache for %s in %s: %s' % (
                        g_config.ID, vehName, areaName, e.message)
                    continue
            slot = outfit.getContainer(areaId).slotFor(GUI_ITEM_TYPE_INDICES[itemTypeName])
            for regionIdx in seasonCache[itemTypeName][areaName].keys():
                itemID = seasonCache[itemTypeName][areaName][regionIdx]
                if not itemID:
                    try:
                        slot.remove(int(regionIdx))
                    except KeyError:  # a paint is being deleted while not applied at all. possible change after last cache
                        del seasonCache[itemTypeName][areaName][regionIdx]  # so we remove an obsolete key
                    continue
                if itemID not in itemDB:
                    print '%s: wrong item ID for %s, idx %s: %s' % (g_config.ID, areaName, regionIdx, itemID)
                    del seasonCache[itemTypeName][areaName][regionIdx]
                    continue
                intCD = itemDB[itemID].compactDescr
                if itemsCache.items.isSynced():
                    item = itemsCache.items.getItemByCD(intCD)
                else:
                    item = itemsCache.items.itemsFactory.createCustomization(intCD)
                slot.set(item, int(regionIdx))
            if not seasonCache[itemTypeName][areaName]:
                del seasonCache[itemTypeName][areaName]
    outfit.invalidate()


def collectCamouflageData():
    camouflages = items.vehicles.g_cache.customization20().camouflages
    g_config.camoForSeason = {}
    for season in SEASONS_CONSTANTS.SEASONS:
        g_config.camoForSeason[season] = {'random': [], 'ally': [], 'enemy': []}
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
                        itemSeason |= getattr(SeasonType, season.upper())
        for season in SeasonType.COMMON_SEASONS:
            camoForSeason = g_config.camoForSeason[SEASON_TYPE_TO_NAME[season]]
            if itemSeason & season:
                if itemMode == RandMode.RANDOM:
                    camoForSeason['random'].append(camoID)
                elif itemMode == RandMode.TEAM:
                    for team in (TeamMode.ALLY, TeamMode.ENEMY):
                        if itemTeam & team:
                            camoForSeason[TeamMode.NAMES[team]].append(camoID)


def processRandomCamouflages(outfit, seasonName, seasonCache, vID=None, isGunCarriage=True):
    if not g_config.camoForSeason:
        collectCamouflageData()
    if vID is not None:
        isAlly = BigWorld.player().guiSessionProvider.getArenaDP().getVehicleInfo(vID).team == BigWorld.player().team
        teamMode = 'ally' if isAlly else 'enemy'
    else:
        teamMode = None
    random.seed(vID)
    camoID = None
    palette = None
    patternSize = None
    camouflages = items.vehicles.g_cache.customization20().camouflages
    itemsCache = dependency.instance(IItemsCache)
    outfitItemIDs = set()
    outfitItems = set()
    for container in outfit.containers():
        if isGunCarriage and container.getAreaID() == Area.TURRET:
            continue
        for slot in container.slots():
            item = slot.getItem(0)
            if item is not None and item.itemTypeID == GUI_ITEM_TYPE.CAMOUFLAGE:
                component = slot.getComponent(0)
                outfitItemIDs.add(item.id)
                outfitItems.add((item.id, component.palette, component.patternSize))
    canBeUniform = len(outfitItemIDs) <= 1
    if canBeUniform and outfitItemIDs:
        camoID, palette, patternSize = outfitItems.pop()
    for areaId, areaName in enumerate(TankPartNames.ALL):
        if areaName == TankPartNames.CHASSIS or isGunCarriage and areaName == TankPartNames.TURRET:
            continue
        slot = outfit.getContainer(areaId).slotFor(GUI_ITEM_TYPE.CAMOUFLAGE)
        item = slot.getItem(0)
        if item is not None:
            continue
        if areaName in seasonCache:
            if seasonCache[areaName]:
                camoID, palette, patternSize = seasonCache[areaName]
        else:
            if camoID is None or not g_config.data['uniformOutfit'] or not canBeUniform:
                camoForSeason = g_config.camoForSeason[seasonName]
                if teamMode is not None and camoForSeason[teamMode]:
                    if g_config.teamCamo[teamMode] is None:
                        camoID = random.choice(camoForSeason[teamMode])
                        item = camouflages[camoID]
                        patternSize = random.randrange(len(item.scales))
                        palette = random.randrange(len(item.palettes))
                        g_config.teamCamo[teamMode] = [camoID, palette, patternSize]
                    else:
                        camoID, palette, patternSize = g_config.teamCamo[teamMode]
                elif camoForSeason['random']:
                    camoID = random.choice(camoForSeason['random'])
                    item = camouflages[camoID]
                    patternSize = random.randrange(len(item.scales))
                    palette = random.randrange(len(item.palettes))
        if camoID is not None:
            intCD = camouflages[camoID].compactDescr
            if itemsCache.items.isSynced():
                item = itemsCache.items.getItemByCD(intCD)
            else:
                item = Camouflage(intCD)
            slot.set(item)
            component = slot.getComponent()
            component.palette = palette
            component.patternSize = patternSize
            seasonCache[areaName] = [camoID, palette, patternSize]
        else:
            seasonCache[areaName] = []
    random.seed()


@overrideMethod(HangarVehicleAppearance, '_HangarVehicleAppearance__assembleModel')
def new_assembleModel(base, self, *a, **kw):
    result = base(self, *a, **kw)
    if not self._HangarVehicleAppearance__isVehicleDestroyed:
        manager = g_appLoader.getDefLobbyApp().containerManager
        if manager is not None:
            container = manager.getContainer(ViewTypes.LOBBY_SUB)
            if container is not None:
                c11nView = container.getView()
                if c11nView is not None and hasattr(c11nView, 'getCurrentOutfit'):
                    outfit = c11nView.getCurrentOutfit()  # fix for HangarFreeCam
                    self.updateCustomization(outfit)
                    return result
        if g_currentPreviewVehicle.isPresent():
            vehicle = g_currentPreviewVehicle.item
        elif g_currentVehicle.isPresent():
            vehicle = g_currentVehicle.item
        else:
            vehicle = None
        vDesc = self._HangarVehicleAppearance__vDesc
        if g_config.data['enabled'] and vDesc.name not in g_config.disable and not (
                vDesc.type.hasCustomDefaultCamouflage and g_config.data['disableWithDefault']):
            nationName, vehicleName = vDesc.name.split(':')
            intCD = vDesc.type.compactDescr
            if g_config.data['hangarCamoKind'] < 3:
                idx = g_config.data['hangarCamoKind']
                season = SeasonType.fromArenaKind(idx)
                outfit = vehicle.getOutfit(season).copy() if vehicle else self.itemsFactory.createOutfit()
                g_tankActiveCamouflage[intCD] = season
            else:
                outfit = self._getActiveOutfit().copy()
                if g_tankActiveCamouflage.get(intCD, SeasonType.EVENT) == SeasonType.EVENT:
                    active = []
                    for season in SeasonType.SEASONS:
                        if vehicle and vehicle.hasOutfitWithItems(season):
                            active.append(season)
                    g_tankActiveCamouflage[intCD] = random.choice(active) if active else SeasonType.SUMMER
            if not g_config.data['useBought']:
                outfit = self.itemsFactory.createOutfit()
            seasonName = SEASON_TYPE_TO_NAME[g_tankActiveCamouflage[intCD]]
            vehCache = g_config.outfitCache.get(nationName, {}).get(vehicleName, {})
            applyPlayerCache(outfit, vehicleName, vehCache.get(seasonName, {}))
            applied, cleaned = applyCamoCache(outfit, vehicleName, vehCache.get(seasonName, {}).get('camo', {}))
            if cleaned:
                vehCache.get(seasonName, {}).pop('camo', None)
            if not vehCache.get(seasonName, None):
                vehCache.pop(seasonName, None)
            if g_config.data['doRandom'] and (not applied or cleaned or g_config.data['fillEmptySlots']):
                seasonCache = g_config.hangarCamoCache.setdefault(nationName, {}).setdefault(vehicleName, {}).setdefault(
                    seasonName, {})
                processRandomCamouflages(outfit, seasonName, seasonCache, isGunCarriage=vDesc.turret.isGunCarriage)
                applyCamoCache(outfit, vehicleName, seasonCache)
            self._HangarVehicleAppearance__outfit = outfit
            self.updateCustomization(outfit)
    return result


@overrideMethod(CompoundAppearance, '_CompoundAppearance__applyVehicleOutfit')
def new_applyVehicleOutfit(base, self, *a, **kw):
    result = self._CompoundAppearance__outfit.copy()
    vID = self._CompoundAppearance__vID
    vDesc = self._CompoundAppearance__typeDesc
    if not vDesc:
        return base(self, *a, **kw)
    if g_config.data['enabled'] and vDesc.name not in g_config.disable and not (
            vDesc.type.hasCustomDefaultCamouflage and g_config.data['disableWithDefault']):
        if not g_config.data['useBought']:
            result = Outfit()
        seasonName = SEASON_TYPE_TO_NAME[SeasonType.fromArenaKind(BigWorld.player().arena.arenaType.vehicleCamouflageKind)]
        nationName, vehicleName = vDesc.name.split(':')
        applied = False
        cleaned = False
        if self._CompoundAppearance__vID == BigWorld.player().playerVehicleID:
            vehCache = g_config.outfitCache.get(nationName, {}).get(vehicleName, {})
            applyPlayerCache(result, vehicleName, vehCache.get(seasonName, {}))
            applied, cleaned = applyCamoCache(result, vehicleName, vehCache.get(seasonName, {}).get('camo', {}))
            if cleaned:
                vehCache.get(seasonName, {}).pop('camo', None)
            if not vehCache.get(seasonName, None):
                vehCache.pop(seasonName, None)
        if g_config.data['doRandom'] and (not applied or cleaned or g_config.data['fillEmptySlots']):
            seasonCache = g_config.arenaCamoCache.setdefault(vID, {})
            processRandomCamouflages(result, seasonName, seasonCache, vID, isGunCarriage=vDesc.turret.isGunCarriage)
            applyCamoCache(result, vehicleName, seasonCache)
    self._CompoundAppearance__outfit = result
    base(self, *a, **kw)


@overrideMethod(PlayerAvatar, 'onBecomePlayer')
def new_onBecomePlayer(base, self, *args, **kwargs):
    base(self, *args, **kwargs)
    g_config.arenaCamoCache.clear()
    collectCamouflageData()


@overrideMethod(Account, 'onBecomePlayer')
def new_onBecomePlayer(base, self):
    base(self)
    g_config.hangarCamoCache.clear()
    collectCamouflageData()
    g_config.teamCamo = dict.fromkeys(('ally', 'enemy'))
