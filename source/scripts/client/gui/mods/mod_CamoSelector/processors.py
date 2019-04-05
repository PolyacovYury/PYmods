import traceback

import BigWorld
import items.vehicles
import random
from Account import Account
from Avatar import PlayerAvatar
from CurrentVehicle import g_currentVehicle, g_currentPreviewVehicle
from PYmodsCore import overrideMethod, loadJson
from gui import g_tankActiveCamouflage
from gui.Scaleform.daapi.view.lobby.customization.shared import SEASON_TYPE_TO_NAME
from gui.Scaleform.framework import ViewTypes
from gui.app_loader import g_appLoader
from gui.customization.shared import C11N_ITEM_TYPE_MAP
from gui.customization.shared import __isTurretCustomizable as isTurretCustom
from gui.hangar_vehicle_appearance import HangarVehicleAppearance
from gui.shared.gui_items import GUI_ITEM_TYPE, GUI_ITEM_TYPE_INDICES, GUI_ITEM_TYPE_NAMES
from gui.shared.gui_items.customization.c11n_items import Camouflage
from gui.shared.gui_items.customization.containers import emptyComponent
from gui.shared.gui_items.customization.outfit import Outfit, Area
from helpers import dependency
from items.components.c11n_constants import SeasonType
from skeletons.gui.shared import IItemsCache
from vehicle_systems.CompoundAppearance import CompoundAppearance
from vehicle_systems.tankStructure import TankPartNames
from . import g_config

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
            print g_config.ID + ': exception while reading camouflages cache for', vehName, 'in', areaName + ':', e.message
            continue
        slot = outfit.getContainer(areaId).slotFor(GUI_ITEM_TYPE.CAMOUFLAGE)
        if seasonCache[areaName]['0']['id'] is None:
            try:
                slot.remove(0)
            except KeyError:
                pass
            continue
        camoID, paletteIdx, scale = [seasonCache[areaName]['0'][k] for k in ('id', 'palette', 'patternSize')]
        if camoID not in camouflages:
            print '%s: wrong camouflage ID for %s:' % (g_config.ID, areaName), camoID
            del seasonCache[areaName]
            continue
        intCD = camouflages[camoID].compactDescr
        if itemsCache.items.isSynced():
            item = itemsCache.items.getItemByCD(intCD)
        else:
            item = Camouflage(intCD)
        if paletteIdx > len(item.palettes):
            print g_config.ID + ': wrong palette idx for', areaName, 'camouflage:', paletteIdx, '(available: %s)' % range(
                len(item.palettes))
            del seasonCache[areaName]
            continue
        if scale > len(item.scales):
            print g_config.ID + ': wrong scale for', areaName, 'camouflage:', scale, '(available: %s)' % range(
                len(item.scales))
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
        itemType = GUI_ITEM_TYPE_INDICES[itemTypeName]
        itemDB = items.vehicles.g_cache.customization20().itemTypes[C11N_ITEM_TYPE_MAP[itemType]]
        for areaName in seasonCache[itemTypeName].keys():
            if itemType in (GUI_ITEM_TYPE.MODIFICATION, GUI_ITEM_TYPE.PROJECTION_DECAL):
                if areaName != 'misc':
                    print g_config.ID + ': wrong area name for', vehName, 'modification:', areaName
                    del seasonCache[itemTypeName][areaName]
                    continue
                else:
                    areaId = Area.MISC
            else:
                areaId = TankPartNames.getIdx(areaName)
            slot = outfit.getContainer(areaId).slotFor(itemType)
            for regionIdx in seasonCache[itemTypeName][areaName].keys():
                itemID = seasonCache[itemTypeName][areaName][regionIdx]['id']
                if itemID is None:
                    try:
                        slot.remove(int(regionIdx))
                    except KeyError:  # a paint is being deleted while not applied at all. possible change after last cache
                        del seasonCache[itemTypeName][areaName][regionIdx]  # so we remove an obsolete key
                    continue
                if itemID not in itemDB:
                    print '%s: wrong item ID for %s, idx %s:' % (g_config.ID, areaName, regionIdx), itemID
                    del seasonCache[itemTypeName][areaName][regionIdx]
                    continue
                intCD = itemDB[itemID].compactDescr
                if itemsCache.items.isSynced():
                    item = itemsCache.items.getItemByCD(intCD)
                else:
                    item = itemsCache.items.itemsFactory.createCustomization(intCD)
                component = emptyComponent(itemType)
                [setattr(component, k, v) for k, v in seasonCache[itemTypeName][areaName][regionIdx].items()]
                slot.set(item, int(regionIdx), component)
            if not seasonCache[itemTypeName][areaName]:
                del seasonCache[itemTypeName][areaName]
    outfit.invalidate()


def processRandomCamouflages(outfit, seasonName, seasonCache, vDesc, vID=None):
    if not g_config.camoForSeason:
        g_config.collectCamouflageData()
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
        if not isTurretCustom(vDesc) and container.getAreaID() == Area.TURRET:
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
        if areaName == TankPartNames.CHASSIS or not isTurretCustom(vDesc) and areaName == TankPartNames.TURRET:
            continue
        slot = outfit.getContainer(areaId).slotFor(GUI_ITEM_TYPE.CAMOUFLAGE)
        item = slot.getItem(0)
        if item is not None:
            continue
        if areaName in seasonCache:
            if seasonCache[areaName]:
                camoID, palette, patternSize = [seasonCache[areaName]['0'][k] for k in ('id', 'palette', 'patternSize')]
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
            seasonCache[areaName] = {'0': {'id': camoID, 'palette': palette, 'patternSize': patternSize}}
        else:
            seasonCache[areaName] = {'0': {'id': None}}
    random.seed()


@overrideMethod(HangarVehicleAppearance, '__startBuild')
def new_startBuild(base, self, *a, **kw):
    traceback.print_stack()
    return base(self, *a, **kw)


@overrideMethod(HangarVehicleAppearance, '_HangarVehicleAppearance__assembleModel')
def new_assembleModel(base, self, *a, **kw):
    result = base(self, *a, **kw)
    if self._HangarVehicleAppearance__isVehicleDestroyed:
        return result
    manager = g_appLoader.getDefLobbyApp().containerManager
    if manager is not None:
        container = manager.getContainer(ViewTypes.LOBBY_SUB)
        if container is not None:
            c11nView = container.getView()
            if c11nView is not None and hasattr(c11nView, 'getCurrentOutfit'):
                outfit = c11nView.getCurrentOutfit()  # fix for HangarFreeCam
                self.updateCustomization(outfit)
                return result
    print g_config.hangarCamoCache
    if g_currentPreviewVehicle.isPresent():
        vehicle = g_currentPreviewVehicle.item
    elif g_currentVehicle.isPresent():
        vehicle = g_currentVehicle.item
    else:
        vehicle = None
    vDesc = self._HangarVehicleAppearance__vDesc
    if not (g_config.data['enabled'] or vDesc.name in g_config.disable or (
            vDesc.type.hasCustomDefaultCamouflage and g_config.data['disableWithDefault'])):
        return result
    nationName, vehicleName = vDesc.name.split(':')
    intCD = vDesc.type.compactDescr
    if g_config.data['useBought']:
        if g_config.data['hangarCamoKind'] < 3:
            g_tankActiveCamouflage[intCD] = SeasonType.fromArenaKind(g_config.data['hangarCamoKind'])
        elif g_tankActiveCamouflage.get(intCD, SeasonType.EVENT) == SeasonType.EVENT:
            active = [season for season in SeasonType.SEASONS if vehicle and vehicle.hasOutfitWithItems(season)]
            g_tankActiveCamouflage[intCD] = random.choice(active) if active else SeasonType.SUMMER
        season = g_tankActiveCamouflage[intCD]
        outfit = None
        if vehicle:
            outfit = vehicle.getOutfit(season)
        if not outfit:
            outfit = self._HangarVehicleAppearance__outfit or self.itemsFactory.createOutfit()
        outfit = outfit.copy()
    else:
        outfit = self.itemsFactory.createOutfit()
    seasonName = SEASON_TYPE_TO_NAME[g_tankActiveCamouflage[intCD]]
    vehCache = g_config.outfitCache.get(nationName, {}).get(vehicleName, {})
    applyPlayerCache(outfit, vehicleName, vehCache.get(seasonName, {}))
    applied, cleaned = applyCamoCache(
        outfit, vehicleName, vehCache.get(seasonName, {}).get(GUI_ITEM_TYPE_NAMES[GUI_ITEM_TYPE.CAMOUFLAGE], {}))
    if cleaned:
        vehCache.get(seasonName, {}).pop(GUI_ITEM_TYPE_NAMES[GUI_ITEM_TYPE.CAMOUFLAGE], None)
    if not vehCache.get(seasonName, None):
        vehCache.pop(seasonName, None)
    if g_config.data['doRandom'] and (not applied or cleaned or g_config.data['fillEmptySlots']):
        seasonCache = g_config.hangarCamoCache.setdefault(nationName, {}).setdefault(vehicleName, {}).setdefault(
            seasonName, {})
        processRandomCamouflages(outfit, seasonName, seasonCache, vDesc)
        applyCamoCache(outfit, vehicleName, seasonCache)
    self._HangarVehicleAppearance__outfit = outfit
    self.updateCustomization(outfit)
    loadJson(g_config.ID, 'outfitCache', g_config.outfitCache, g_config.configPath, True)
    print g_config.hangarCamoCache
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
            applied, cleaned = applyCamoCache(
                result, vehicleName, vehCache.get(seasonName, {}).get(GUI_ITEM_TYPE_NAMES[GUI_ITEM_TYPE.CAMOUFLAGE], {}))
            if cleaned:
                vehCache.get(seasonName, {}).pop(GUI_ITEM_TYPE_NAMES[GUI_ITEM_TYPE.CAMOUFLAGE], None)
            if not vehCache.get(seasonName, None):
                vehCache.pop(seasonName, None)
            loadJson(g_config.ID, 'outfitCache', g_config.outfitCache, g_config.configPath, True)
        if g_config.data['doRandom'] and (not applied or cleaned or g_config.data['fillEmptySlots']):
            seasonCache = g_config.arenaCamoCache.setdefault(vID, {})
            processRandomCamouflages(result, seasonName, seasonCache, vDesc, vID)
            applyCamoCache(result, vehicleName, seasonCache)
    self._CompoundAppearance__outfit = result
    base(self, *a, **kw)


@overrideMethod(PlayerAvatar, 'onBecomePlayer')
def new_onBecomePlayer(base, self, *args, **kwargs):
    base(self, *args, **kwargs)
    g_config.arenaCamoCache.clear()
    g_config.collectCamouflageData()


@overrideMethod(Account, 'onBecomePlayer')
def new_onBecomePlayer(base, self):
    base(self)
    g_config.hangarCamoCache.clear()
    g_config.collectCamouflageData()
    g_config.teamCamo = dict.fromkeys(('ally', 'enemy'))
