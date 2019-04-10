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
from .constants import SEASON_NAME_TO_TYPE

try:
    import gui.mods.mod_statpaints  # camouflage removal should work even with CamoSelector, so it has to be imported first
except ImportError:
    pass


def deleteEmpty(settings):
    for key, value in settings.items():
        if key == GUI_ITEM_TYPE_NAMES[GUI_ITEM_TYPE.CAMOUFLAGE] and not isTurretCustom(g_currentVehicle.item.descriptor):
            value.pop(Area.TURRET, None)
        elif isinstance(value, dict):
            deleteEmpty(value)
            if not value:
                del settings[key]


def hasNoCamo(outfit):
    return not any(GUI_ITEM_TYPE.CAMOUFLAGE in slot.getTypes() and not slot.isEmpty() for slot in outfit.slots())


def applyOutfitCache(outfit, seasonCache):
    itemsCache = dependency.instance(IItemsCache)
    for itemTypeName, itemCache in seasonCache.items():
        itemType = GUI_ITEM_TYPE_INDICES[itemTypeName]
        itemDB = items.vehicles.g_cache.customization20().itemTypes[C11N_ITEM_TYPE_MAP[itemType]]
        for areaName, areaCache in itemCache.items():
            areaId = (Area.MISC if areaName == 'misc' else TankPartNames.getIdx(areaName))
            slot = outfit.getContainer(areaId).slotFor(itemType)
            for regionIdx in areaCache.keys():
                itemID = areaCache[regionIdx]['id']
                if itemID is None:
                    if slot.getItem(int(regionIdx)) is not None:
                        slot.remove(int(regionIdx))
                    else:  # item is being deleted while not applied at all. possible change after last cache
                        del areaCache[regionIdx]  # so we remove an obsolete key
                    continue
                if itemID not in itemDB:
                    print g_config.ID + ': wrong item ID for %s, idx %s:' % (areaName, regionIdx), itemID
                    del areaCache[regionIdx]
                    continue
                intCD = itemDB[itemID].compactDescr
                item = (itemsCache.items.getItemByCD if itemsCache.items.isSynced() else
                        itemsCache.items.itemsFactory.createCustomization)(intCD)
                component = emptyComponent(itemType)
                [setattr(component, k, v) for k, v in areaCache[regionIdx].items()]
                slot.set(item, int(regionIdx), component)
    outfit.invalidate()


def processRandomCamouflages(outfit, seasonName, seasonCache, processTurret, vID=None):
    if not g_config.camoForSeason:
        g_config.collectCamouflageData()
    if outfit.modelsSet:  # might add a checkbox in settings to still process styled outfits, thus this will become necessary
        return
    seasonCache = seasonCache.setdefault(GUI_ITEM_TYPE_NAMES[GUI_ITEM_TYPE.CAMOUFLAGE], {})
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
        if not processTurret and container.getAreaID() == Area.TURRET:
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
        if areaName == TankPartNames.CHASSIS or not processTurret and areaName == TankPartNames.TURRET:
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
                        g_config.teamCamo[teamMode] = (camoID, palette, patternSize)
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


def applyOutfitInfo(outfit, seasonName, vDesc, randomCache, vID=None, isPlayerVehicle=True):
    nationName, vehicleName = vDesc.name.split(':')
    if isPlayerVehicle:
        vehCache = g_config.outfitCache.get(nationName, {}).get(vehicleName, {})
        styleCache = vehCache.get('style', {'intCD': None, 'applied': False})
        if styleCache['applied']:
            styleCD = styleCache['intCD']
            if styleCD is not None:
                itemsCache = dependency.instance(IItemsCache)
                style = (itemsCache.items.getItemByCD if itemsCache.items.isSynced() else
                         itemsCache.items.itemsFactory.createCustomization)(styleCD)
                if not style:
                    print g_config.ID + ': style', styleCD, 'for', vehicleName, 'deleted from game client.'
                    styleCache.update(intCD=None, applied=False)
                else:
                    outfit = style.getOutfit(SEASON_NAME_TO_TYPE[seasonName]).copy()
            else:
                outfit = Outfit()
                outfit._id = 20000
        else:
            if outfit.id and any(v for k, v in vehCache.iteritems() if k != 'style') and not vehCache.get(
                    'style', {}).get('applied', False):
                outfit = Outfit()
            applyOutfitCache(outfit, vehCache.get(seasonName, {}))
        deleteEmpty(vehCache)
        loadJson(g_config.ID, 'outfitCache', g_config.outfitCache, g_config.configPath, True)
    if outfit.id:
        randomCache.clear()
    elif g_config.data['doRandom'] and (g_config.data['fillEmptySlots'] or hasNoCamo(outfit)):
        processRandomCamouflages(outfit, seasonName, randomCache, isTurretCustom(vDesc), vID)
        applyOutfitCache(outfit, randomCache)
    return outfit


@overrideMethod(HangarVehicleAppearance, '_HangarVehicleAppearance__reload')
def new_reload(base, self, vDesc, vState, outfit):
    if vState != 'undamaged':
        return base(self, vDesc, vState, outfit)
    manager = g_appLoader.getDefLobbyApp().containerManager
    if manager is not None:
        container = manager.getContainer(ViewTypes.LOBBY_SUB)
        if container is not None:
            c11nView = container.getView()
            if c11nView is not None and hasattr(c11nView, 'service'):
                outfit = c11nView.service.getCtx().currentOutfit
                return base(self, vDesc, vState, outfit)
    if (not g_config.data['enabled'] or vDesc.name in g_config.disable or (
            vDesc.type.hasCustomDefaultCamouflage and g_config.data['disableWithDefault'])):
        return base(self, vDesc, vState, outfit)
    for descr in g_currentPreviewVehicle, g_currentVehicle:
        if descr.isPresent() and descr.item.descriptor.name == vDesc.name:
            vehicle = descr.item
            break
    else:
        vehicle = None
    nation, vehicleName = vDesc.name.split(':')
    intCD = vDesc.type.compactDescr
    season = g_tankActiveCamouflage.get(intCD, SeasonType.EVENT)
    if g_config.data['hangarCamoKind'] < 3:
        g_tankActiveCamouflage[intCD] = SeasonType.fromArenaKind(g_config.data['hangarCamoKind'])
    elif season in (SeasonType.UNDEFINED, SeasonType.EVENT):
        active = [season for season in SeasonType.SEASONS if vehicle and vehicle.hasOutfitWithItems(season)]
        g_tankActiveCamouflage[intCD] = random.choice(active) if active else SeasonType.SUMMER
    if season not in (g_tankActiveCamouflage[intCD], SeasonType.UNDEFINED, SeasonType.EVENT):
        season = g_tankActiveCamouflage[intCD]
        if vehicle:
            outfit = vehicle.getOutfit(season)
    if outfit:
        outfit = outfit.copy()
    seasonName = SEASON_TYPE_TO_NAME[g_tankActiveCamouflage[intCD]]
    seasonCache = g_config.hangarCamoCache.setdefault(nation, {}).setdefault(vehicleName, {}).setdefault(seasonName, {})
    outfit = applyOutfitInfo(outfit, seasonName, vDesc, seasonCache)
    return base(self, vDesc, vState, outfit)


@overrideMethod(CompoundAppearance, '_CompoundAppearance__applyVehicleOutfit')
def new_applyVehicleOutfit(base, self, *a, **kw):
    outfit = self._CompoundAppearance__outfit.copy()
    vID = self._CompoundAppearance__vID
    vDesc = self._CompoundAppearance__typeDesc
    if not vDesc:
        return base(self, *a, **kw)
    if g_config.data['enabled'] and vDesc.name not in g_config.disable and not (
            vDesc.type.hasCustomDefaultCamouflage and g_config.data['disableWithDefault']):
        if not g_config.data['useBought']:
            outfit = Outfit()
        seasonName = SEASON_TYPE_TO_NAME[SeasonType.fromArenaKind(BigWorld.player().arena.arenaType.vehicleCamouflageKind)]
        outfit = applyOutfitInfo(outfit, seasonName, vDesc, g_config.arenaCamoCache.setdefault(vID, {}),
                                 vID, self._CompoundAppearance__vID == BigWorld.player().playerVehicleID)
    self._CompoundAppearance__outfit = outfit
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
