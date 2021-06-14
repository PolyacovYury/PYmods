import BigWorld
import items.vehicles
import random
from Account import Account
from Avatar import PlayerAvatar
from CurrentVehicle import g_currentVehicle, g_currentPreviewVehicle
from HeroTank import _HeroTankAppearance
from PYmodsCore import overrideMethod, loadJson
from PlatoonTank import _PlatoonTankAppearance
from gui import g_tankActiveCamouflage
from gui.customization.shared import C11N_ITEM_TYPE_MAP, SEASON_TYPE_TO_NAME
from gui.customization.shared import __isTurretCustomizable as isTurretCustom
from gui.hangar_vehicle_appearance import HangarVehicleAppearance
from gui.shared.gui_items import GUI_ITEM_TYPE, GUI_ITEM_TYPE_INDICES, GUI_ITEM_TYPE_NAMES
from helpers import dependency
from items.components.c11n_constants import SeasonType
from items.customizations import createNationalEmblemComponents, CustomizationOutfit
from skeletons.gui.shared.gui_items import IGuiItemsFactory
from vehicle_outfit.containers import emptyComponent
from vehicle_outfit.outfit import Outfit, Area
from vehicle_systems.CompoundAppearance import CompoundAppearance
from vehicle_systems.tankStructure import TankPartNames
from . import g_config
from .constants import SEASON_NAME_TO_TYPE

try:
    import gui.mods.mod_statpaints  # camouflage removal should work even with CamoSelector, so it has to be imported first
except ImportError:
    pass


def deleteEmpty(settings, isTurretCustomisable=True):
    for key, value in settings.items():
        if key == GUI_ITEM_TYPE_NAMES[GUI_ITEM_TYPE.CAMOUFLAGE] and not isTurretCustomisable:
            value.pop(TankPartNames.TURRET, None)
        if isinstance(value, dict):
            deleteEmpty(value, isTurretCustomisable)
            if not value:
                del settings[key]


def hasNoCamo(outfit):
    return not any(GUI_ITEM_TYPE.CAMOUFLAGE in slot.getTypes() and not slot.isEmpty() for slot in outfit.slots())


def applyOutfitCache(outfit, seasonCache, clean=True):
    try:
        for itemTypeName, itemCache in seasonCache.items():
            itemType = GUI_ITEM_TYPE_INDICES[itemTypeName]
            itemDB = items.vehicles.g_cache.customization20().itemTypes[C11N_ITEM_TYPE_MAP[itemType]]
            for areaName, areaCache in itemCache.items():
                areaId = (Area.MISC if areaName == 'misc' else TankPartNames.getIdx(areaName))
                slot = outfit.getContainer(areaId).slotFor(itemType)
                for regionIdx in areaCache.keys():
                    itemID = areaCache[regionIdx]['id']
                    if itemID is None:
                        if slot.getItemCD(int(regionIdx)):
                            slot.remove(int(regionIdx))
                        elif clean:  # item is being deleted while not applied at all. possible change after last cache
                            del areaCache[regionIdx]  # so we remove an obsolete key
                        continue
                    if itemID not in itemDB:
                        print g_config.ID + ': wrong item ID for %s, idx %s:' % (areaName, regionIdx), itemID
                        del areaCache[regionIdx]
                        continue
                    component = emptyComponent(itemType)
                    [setattr(component, k, v) for k, v in areaCache[regionIdx].items()]
                    slot.set(itemDB[itemID].compactDescr, int(regionIdx), component)
        outfit.invalidate()
    except AttributeError:
        __import__('pprint').pprint(seasonCache)
        raise


def processRandomCamouflages(outfit, seasonName, seasonCache, processTurret, vID=None):
    if not g_config.camoForSeason:
        g_config.collectCamouflageData()
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
    outfitItemIDs = set()
    outfitItems = set()
    for container in outfit.containers():
        if not processTurret and container.getAreaID() == Area.TURRET:
            continue
        slot = container.slotFor(GUI_ITEM_TYPE.CAMOUFLAGE)
        if not slot:
            continue
        intCD = slot.getItemCD(0)
        if not intCD:
            continue
        item = dependency.instance(IGuiItemsFactory).createCustomization(intCD)
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
        if slot.getItemCD(0):
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
            slot.set(camouflages[camoID].compactDescr)
            component = slot.getComponent()
            component.palette = palette
            component.patternSize = patternSize
            seasonCache[areaName] = {'0': {'id': camoID, 'palette': palette, 'patternSize': patternSize}}
        else:
            seasonCache[areaName] = {'0': {'id': None}}
    random.seed()


def applyOutfitInfo(outfit, seasonName, vDesc, randomCache, vID=None, isPlayerVehicle=True):
    nationName, vehicleName = vDesc.name.split(':')
    try:
        isTurretCustomizable = isTurretCustom(vDesc)
    except ValueError:
        print g_config.ID + ': turret customization check for', vehicleName, 'failed:'
        __import__('traceback').print_exc()
        isTurretCustomizable = False
    if isPlayerVehicle:
        vehCache = g_config.outfitCache.get(nationName, {}).get(vehicleName, {})
        styleCache = vehCache.get('style', {'intCD': None, 'applied': False})
        if styleCache['applied']:
            styleCD = styleCache['intCD']
            if styleCD is not None:
                style = dependency.instance(IGuiItemsFactory).createCustomization(styleCD)
                if not style:
                    print g_config.ID + ': style', styleCD, 'for', vehicleName, 'deleted from game client.'
                    styleCache.update(intCD=None, applied=False)
                else:
                    outfit = style.getOutfit(SEASON_NAME_TO_TYPE[seasonName]).copy()
            else:
                outfit = Outfit()
                outfit._id = 20000
        else:
            if outfit.modelsSet and any(v for k, v in vehCache.iteritems() if k != 'style'):
                outfit = Outfit()
            applyOutfitCache(outfit, vehCache.get(seasonName, {}))
        deleteEmpty(vehCache, isTurretCustomizable)
        loadJson(g_config.ID, 'outfitCache', g_config.outfitCache, g_config.configPath, True)
    if outfit.modelsSet or outfit.id == 20000:
        randomCache.clear()
    elif g_config.data['doRandom'] and (g_config.data['fillEmptySlots'] or hasNoCamo(outfit)):
        processRandomCamouflages(outfit, seasonName, randomCache, isTurretCustomizable, vID)
        applyOutfitCache(outfit, randomCache)
    return outfit


@overrideMethod(HangarVehicleAppearance, '_getActiveOutfit')
@overrideMethod(_HeroTankAppearance, '_getActiveOutfit')
@overrideMethod(_PlatoonTankAppearance, '_getActiveOutfit')
def new_getActiveOutfit(base, self, vDesc):
    outfit = base(self, vDesc)
    if (not g_config.data['enabled'] or not vDesc or vDesc.name in g_config.disable or (
            vDesc.type.hasCustomDefaultCamouflage and g_config.data['disableWithDefault'])):
        return outfit
    nation, vehicleName = vDesc.name.split(':')
    if isinstance(self, _HeroTankAppearance):
        if g_config.data['hangarCamoKind'] < 3:
            season = SeasonType.fromArenaKind(g_config.data['hangarCamoKind'])
            if self._HeroTankAppearance__season != season:
                self._HeroTankAppearance__season = season
                outfit = base(self, vDesc)
        season = self._HeroTankAppearance__season
    elif isinstance(self, _PlatoonTankAppearance):
        if g_config.data['hangarCamoKind'] < 3:
            season = SeasonType.fromArenaKind(g_config.data['hangarCamoKind'])
            if self._PlatoonTankAppearance__tankInfo.seasonType != season:
                self._PlatoonTankAppearance__tankInfo = self._PlatoonTankAppearance__tankInfo._replace(seasonType=season)
                outfit = base(self, vDesc)
        season = self._PlatoonTankAppearance__tankInfo.seasonType
    else:  # self.__class__ == HangarVehicleAppearance
        for descr in (g_currentPreviewVehicle, g_currentVehicle):
            if descr.isPresent() and descr.item.descriptor.name == vDesc.name:
                vehicle = descr.item
                break
        else:
            vehicle = None
        intCD = vDesc.type.compactDescr
        season = g_tankActiveCamouflage.get(intCD, SeasonType.EVENT)
        if g_config.data['hangarCamoKind'] < 3:
            g_tankActiveCamouflage[intCD] = SeasonType.fromArenaKind(g_config.data['hangarCamoKind'])
        elif season in (SeasonType.UNDEFINED, SeasonType.EVENT):
            g_tankActiveCamouflage[intCD] = vehicle.getAnyOutfitSeason() if vehicle else SeasonType.SUMMER
        if season not in (g_tankActiveCamouflage[intCD], SeasonType.UNDEFINED, SeasonType.EVENT):
            season = g_tankActiveCamouflage[intCD]
            if vehicle:
                outfit = vehicle.getOutfit(season)
    seasonName = SEASON_TYPE_TO_NAME[season]
    outfit = outfit.copy() if outfit else self.customizationService.getEmptyOutfitWithNationalEmblems(
        vehicleCD=vDesc.makeCompactDescr())
    seasonCache = g_config.hangarCamoCache.setdefault(nation, {}).setdefault(vehicleName, {}).setdefault(seasonName, {})
    return applyOutfitInfo(outfit, seasonName, vDesc, seasonCache)


@overrideMethod(CompoundAppearance, '_prepareOutfit')
def new_prepareOutfit(base, self, *a, **kw):
    outfit = base(self, *a, **kw).copy()
    vDesc = self.typeDescriptor
    if not vDesc:
        return outfit
    if not g_config.data['enabled'] or vDesc.name in g_config.disable or (
            vDesc.type.hasCustomDefaultCamouflage and g_config.data['disableWithDefault']):
        return outfit
    if not g_config.data['useBought']:
        outfit = self.itemsFactory.createOutfit(
            component=(CustomizationOutfit(decals=createNationalEmblemComponents(vDesc))), vehicleCD=vDesc.makeCompactDescr())
    seasonName = SEASON_TYPE_TO_NAME[SeasonType.fromArenaKind(BigWorld.player().arena.arenaType.vehicleCamouflageKind)]
    return applyOutfitInfo(outfit, seasonName, vDesc, g_config.arenaCamoCache.setdefault(self.id, {}),
                           self.id, self.id == BigWorld.player().playerVehicleID)


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
