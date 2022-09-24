import BigWorld
import random
from Account import Account
from Avatar import PlayerAvatar
from CurrentVehicle import g_currentPreviewVehicle, g_currentVehicle
from HeroTank import _HeroTankAppearance
from OpenModsCore import BigWorld_callback, loadJson, overrideMethod
from PlatoonTank import _PlatoonTankAppearance
from copy import deepcopy
from gui import g_tankActiveCamouflage
from gui.Scaleform.daapi.view.lobby.customization.shared import (
    CustomizationTabs, fitOutfit, getEditableStyleOutfitDiffComponent,
)
from gui.customization.shared import C11N_ITEM_TYPE_MAP, SEASON_TYPE_TO_NAME, __isTurretCustomizable as isTurretCustom
from gui.hangar_vehicle_appearance import HangarVehicleAppearance
from gui.shared.gui_items import GUI_ITEM_TYPE, GUI_ITEM_TYPE_INDICES, GUI_ITEM_TYPE_NAMES
from gui.shared.utils.HangarSpace import _ExecuteAfterHangarSpaceInited
from items.components.c11n_constants import CustomizationType, EMPTY_ITEM_ID, ItemTags, SeasonType
from items.customizations import CustomizationOutfit, EmptyComponent, InsigniaComponent, createNationalEmblemComponents
from items.vehicles import g_cache
from vehicle_outfit.outfit import Area, Outfit
from vehicle_outfit.packers import pickPacker
from vehicle_systems.CompoundAppearance import CompoundAppearance
from vehicle_systems.camouflages import getStyleProgressionOutfit
from vehicle_systems.tankStructure import TankPartNames
from . import g_config
from .constants import CUSTOM_GROUP_NAME, SEASON_NAME_TO_TYPE, getAvailableRegions

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


def getStyleFromId(styleId):
    return HangarVehicleAppearance.itemsFactory.createCustomization(g_cache.customization20().styles[styleId].compactDescr)


def getDefaultEmblemCD(vDesc=None):
    vDesc = vDesc or g_currentVehicle.item.descriptor
    cache = g_cache.customization20()
    return cache.decals[vDesc.type.defaultPlayerEmblemID].compactDescr


def getDefaultInsigniaCD(vDesc=None):
    vDesc = vDesc or g_currentVehicle.item.descriptor
    cache = g_cache.customization20()
    return cache.insignias[cache.defaultInsignias[vDesc.type.customizationNationID]].compactDescr


def getDefaultItemCDs(vDesc=None):
    return getDefaultEmblemCD(vDesc), getDefaultInsigniaCD(vDesc)


def addDefaultInsignia(outfit, vDesc=None):
    vDesc = vDesc or g_currentVehicle.item.descriptor
    insignia_slot = outfit.gun.slotFor(GUI_ITEM_TYPE.INSIGNIA)
    if not insignia_slot.getItemCD():
        insignia_slot.set(getDefaultInsigniaCD(vDesc), component=InsigniaComponent())  # emptyComponent for insignia is wrong
    return outfit.copy()


def createEmptyOutfit(vDesc, diffComp=None):
    component = CustomizationOutfit(decals=createNationalEmblemComponents(vDesc))
    if diffComp is not None:
        component = component.applyDiff(diffComp)
    return addDefaultInsignia(Outfit(component=component, vehicleCD=vDesc.makeCompactDescr()), vDesc)


def changeOutfitStyleData(outfit, style, season, level, vDesc=None):
    vDesc = vDesc or g_currentVehicle.item.descriptor
    old_style, new_style, old_season, new_season, old_level, new_level = style, style, season, season, level, level
    if isinstance(style, tuple):
        old_style, new_style = style
    if isinstance(season, tuple):
        old_season, new_season = season
    if isinstance(level, tuple):
        old_level, new_level = level
    baseOutfit = getOutfitFromStyle(old_style, old_season, old_level, vDesc)
    diffComp = getEditableStyleOutfitDiffComponent(outfit, baseOutfit)
    diffComp.styleId = new_style.id if new_style else 0
    outfit = getOutfitFromStyle(new_style, new_season, new_level, vDesc)
    return outfit.patch(createEmptyOutfit(vDesc, diffComp))


def getOutfitFromStyle(style, season, level, vDesc=None):
    vDesc = vDesc or g_currentVehicle.item.descriptor
    vehicleCD = vDesc.makeCompactDescr()
    if style is None:
        baseOutfit = createEmptyOutfit(vDesc)
    else:
        component = deepcopy(style.descriptor.outfits[season])
        if ItemTags.ADD_NATIONAL_EMBLEM in style.tags:
            component.decals.extend(createNationalEmblemComponents(vDesc))
        baseOutfit = Outfit(component=component, vehicleCD=vehicleCD)
        if style.isProgressive:
            baseOutfit = getStyleProgressionOutfit(baseOutfit, level, season)
    fitOutfit(baseOutfit, {areaId: {
        slotType: getAvailableRegions(areaId, slotType, vDesc) for slotType in CustomizationTabs.SLOT_TYPES.itervalues()}
        for areaId in Area.ALL})
    return addDefaultInsignia(baseOutfit, vDesc)


def applyStyleOverride(vDesc, outfit, seasonName, seasonCache, clean):
    old_style = getStyleFromId(outfit.id) if outfit.id else None
    old_season = SEASON_NAME_TO_TYPE[seasonName]
    old_level = outfit.progressionLevel if outfit.style and outfit.style.isProgression else 1
    styleInfo = seasonCache.get('style', {})
    styleId = styleInfo.get('id')
    if styleId is None:
        return addDefaultInsignia(outfit, vDesc)
    if styleId == EMPTY_ITEM_ID:
        if not outfit.id:
            if clean:  # item is being deleted while not applied at all. possible change after last cache
                seasonCache.pop('style', None)  # so we remove an obsolete key
            return addDefaultInsignia(outfit, vDesc)
        return changeOutfitStyleData(outfit, (old_style, None), old_season, old_level, vDesc)
    if styleId not in g_cache.customization20().itemTypes[CustomizationType.STYLE]:
        print g_config.LOG, 'style', styleId, 'for', vDesc.name, 'deleted from game client.'
        seasonCache.pop('style', None)
        return addDefaultInsignia(outfit, vDesc)
    new_style = getStyleFromId(styleId)
    new_season = SEASON_NAME_TO_TYPE[styleInfo.get('season', seasonName)]
    new_level = styleInfo.get('progressionLevel', 1)
    return changeOutfitStyleData(outfit, (old_style, new_style), (old_season, new_season), (old_level, new_level), vDesc)


def applyOutfitCache(vDesc, outfit, seasonName, seasonCache, clean=True):
    try:
        outfit = applyStyleOverride(vDesc, outfit, seasonName, seasonCache, clean)
        itemDBs = g_cache.customization20().itemTypes
        for itemTypeName, itemCache in seasonCache.items():
            if itemTypeName == 'style':
                continue
            slotType = GUI_ITEM_TYPE_INDICES[itemTypeName]
            for areaName, areaCache in itemCache.items():
                slot = outfit.getContainer(
                    (Area.MISC if areaName == 'misc' else TankPartNames.getIdx(areaName))).slotFor(slotType)
                for regionKey in areaCache.keys():
                    _applyRegionCache(itemDBs, itemTypeName, slotType, slot, areaName, areaCache, regionKey, clean)
        outfit.invalidate()
        return outfit
    except AttributeError:
        __import__('pprint').pprint(seasonCache)
        raise


def _applyRegionCache(itemDBs, itemTypeName, slotType, slot, areaName, areaCache, regionKey, clean):
    itemID = areaCache[regionKey]['id']
    if itemID is None:
        if slot.getItemCD(int(regionKey)):
            slot.remove(int(regionKey))
        elif clean:  # item is being deleted while not applied at all. possible change after last cache
            del areaCache[regionKey]  # so we remove an obsolete key
        return
    if slotType == GUI_ITEM_TYPE.INSCRIPTION and 'number' in areaCache[regionKey]:
        slotType = GUI_ITEM_TYPE.PERSONAL_NUMBER
    cType = C11N_ITEM_TYPE_MAP[slotType]
    itemDB = itemDBs[cType]
    if isinstance(itemID, basestring):
        itemID = g_config.modded_lookup_name[cType].get(itemID, itemID)
    if itemID not in itemDB:
        print g_config.LOG, itemTypeName, 'ID', itemID, 'on', areaName, 'region', regionKey, 'not found'
        del areaCache[regionKey]
        return
    item = itemDB[itemID]
    areaCache[regionKey]['id'] = g_config.getItemKeys(itemID, item)[1]
    component = (pickPacker(slotType).getRawComponent() or EmptyComponent)()
    [setattr(component, k, v) for k, v in areaCache[regionKey].items()]
    slot.set(item.compactDescr, int(regionKey), component)


def getRandomCamoID(camoIDs, requirement):
    unchecked = list(camoIDs)
    while unchecked:
        result = random.choice(unchecked)
        if not requirement(result):
            unchecked.remove(result)
        else:
            return result
    return random.choice(list(camoIDs))


def processRandomCamouflages(outfit, seasonName, seasonCache, processTurret, vID=None):
    if not g_config.camoForSeason:
        g_config.collectCamouflageData()
    seasonCache = seasonCache.setdefault(GUI_ITEM_TYPE_NAMES[GUI_ITEM_TYPE.CAMOUFLAGE], {})
    if vID is not None:
        isAlly = BigWorld.player().guiSessionProvider.getArenaDP().getVehicleInfo(vID).team == BigWorld.player().team
        teamMode = 'ally' if isAlly else 'enemy'
        requirement = lambda _i: True
    else:
        teamMode = None
        from gui.shared.utils.requesters import REQ_CRITERIA
        # TODO: paid/unpaid changes here
        # requirement = REQ_CRITERIA.EMPTY  # paid
        # the rest is for unpaid
        from gui.customization.shared import createCustomizationBaseRequestCriteria
        itemRequirement = ((createCustomizationBaseRequestCriteria(
            g_currentVehicle.item, g_currentVehicle.item.eventsCache.questsProgress, ()
        ) if g_currentVehicle.item else REQ_CRITERIA.EMPTY) | REQ_CRITERIA.CUSTOM(
            lambda _item: _item.buyCount > 0)) ^ REQ_CRITERIA.CUSTOMIZATION.PRICE_GROUP(CUSTOM_GROUP_NAME)
        requirement = lambda itemID: itemRequirement(g_currentVehicle.itemsCache.items.getItem(
            GUI_ITEM_TYPE.CUSTOMIZATION, CustomizationType.CAMOUFLAGE, itemID))
    random.seed(vID)
    camoID, palette, patternSize = None, None, None
    camouflages = g_cache.customization20().camouflages
    outfitItemIDs = set()
    outfitItems = set()
    for container in outfit.containers():
        if not processTurret and container.getAreaID() == Area.TURRET:
            continue
        slot = container.slotFor(GUI_ITEM_TYPE.CAMOUFLAGE)
        if not slot:
            continue
        itemCD = slot.getItemCD(0)
        if not itemCD:
            continue
        component = slot.getComponent(0)
        outfitItemIDs.add(component.id)
        outfitItems.add((component.id, component.palette, component.patternSize))
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
                if isinstance(camoID, basestring):
                    camoID = g_config.modded_lookup_name[CustomizationType.CAMOUFLAGE].get(camoID, camoID)
        elif camoID is None or not g_config.data['uniformOutfit'] or not canBeUniform:
            camoForSeason = g_config.camoForSeason[seasonName]
            if teamMode is None or not camoForSeason[teamMode]:
                if camoForSeason['random']:
                    camoID = getRandomCamoID(camoForSeason['random'], requirement)
                    item = camouflages[camoID]
                    patternSize = random.randrange(len(item.scales))
                    palette = random.randrange(len(item.palettes))
            elif g_config.teamCamo[teamMode] is None:
                camoID = getRandomCamoID(camoForSeason[teamMode], requirement)
                item = camouflages[camoID]
                patternSize = random.randrange(len(item.scales))
                palette = random.randrange(len(item.palettes))
                g_config.teamCamo[teamMode] = (camoID, palette, patternSize)
            else:
                camoID, palette, patternSize = g_config.teamCamo[teamMode]
        if camoID is not None:
            slot.set(camouflages[camoID].compactDescr)
            component = slot.getComponent()
            component.palette = palette
            component.patternSize = patternSize
            seasonCache[areaName] = {'0': {'id': camoID, 'palette': palette, 'patternSize': patternSize}}
        else:
            seasonCache[areaName] = {'0': {'id': None}}
    random.seed()


def applyOutfitInfo(outfit, seasonName, vDesc, randomCache, isPlayerVehicle=True, vID=None, clean=False):
    nationName, vehicleName = vDesc.name.split(':')
    try:
        isTurretCustomizable = isTurretCustom(vDesc)
    except ValueError:
        print g_config.LOG, 'turret customization check for', vehicleName, 'failed:'
        __import__('traceback').print_exc()
        isTurretCustomizable = False
    if isPlayerVehicle:
        vehCache = g_config.outfitCache.get(nationName, {}).get(vehicleName, {})
        outfit = applyOutfitCache(vDesc, outfit, seasonName, vehCache.get(seasonName, {}), clean)
        deleteEmpty(vehCache, isTurretCustomizable)
        loadJson(g_config.ID, 'outfitCache', g_config.outfitCache, g_config.configPath, True)
    if g_config.data['doRandom'] and (g_config.data['fillEmptySlots'] or hasNoCamo(outfit)):
        processRandomCamouflages(outfit, seasonName, randomCache, isTurretCustomizable, vID)
        outfit = applyOutfitCache(vDesc, outfit, seasonName, randomCache)
    return outfit


@overrideMethod(HangarVehicleAppearance, '_getActiveOutfit')
@overrideMethod(_HeroTankAppearance, '_getActiveOutfit')
@overrideMethod(_PlatoonTankAppearance, '_getActiveOutfit')
def new_getActiveOutfit(base, self, vDesc):
    outfit = base(self, vDesc)
    if (not g_config.data['enabled'] or not vDesc or vDesc.name in g_config.disabledVehicles
            or not vDesc.turret.customizableVehicleAreas['camouflage']  # can be empty on event vehicles, everything breaks
            or (vDesc.type.hasCustomDefaultCamouflage and g_config.data['disableWithDefault'])):
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
        descCD = vDesc.type.compactDescr
        season = g_tankActiveCamouflage.get(descCD, SeasonType.EVENT)
        if g_config.data['hangarCamoKind'] < 3:
            g_tankActiveCamouflage[descCD] = SeasonType.fromArenaKind(g_config.data['hangarCamoKind'])
        elif season in (SeasonType.UNDEFINED, SeasonType.EVENT):
            g_tankActiveCamouflage[descCD] = vehicle.getAnyOutfitSeason() if vehicle else SeasonType.SUMMER
        if season != g_tankActiveCamouflage[descCD]:
            season = g_tankActiveCamouflage[descCD]
            if vehicle:
                outfit = vehicle.getOutfit(season)
    seasonName = SEASON_TYPE_TO_NAME[season]
    outfit = outfit.copy() if outfit else createEmptyOutfit(vDesc)
    seasonCache = g_config.hangarCamoCache.setdefault(nation, {}).setdefault(vehicleName, {}).setdefault(seasonName, {})
    return applyOutfitInfo(outfit, seasonName, vDesc, seasonCache, isinstance(self, HangarVehicleAppearance))


@overrideMethod(CompoundAppearance, '_prepareOutfit')
def new_prepareOutfit(base, self, *a, **kw):
    outfit = base(self, *a, **kw).copy()
    vDesc = self.typeDescriptor
    if not vDesc:
        return outfit
    if (not g_config.data['enabled'] or vDesc.name in g_config.disabledVehicles
            or not vDesc.turret.customizableVehicleAreas['camouflage']  # can be empty on event vehicles, everything breaks
            or (vDesc.type.hasCustomDefaultCamouflage and g_config.data['disableWithDefault'])):
        return outfit
    if not g_config.data['useBought']:
        outfit = createEmptyOutfit(vDesc)
    seasonName = SEASON_TYPE_TO_NAME[SeasonType.fromArenaKind(BigWorld.player().arena.arenaType.vehicleCamouflageKind)]
    return applyOutfitInfo(outfit, seasonName, vDesc, g_config.arenaCamoCache.setdefault(
        self.id, {}), self.id == BigWorld.player().playerVehicleID, self.id, bool(outfit.pack().insignias))


@overrideMethod(PlayerAvatar, 'onBecomePlayer')
def new_onBecomePlayer(base, self, *args, **kwargs):
    base(self, *args, **kwargs)
    g_config.arenaCamoCache.clear(), g_config.collectCamouflageData()


@overrideMethod(Account, 'onBecomePlayer')
def new_onBecomePlayer(base, self):
    base(self)
    g_config.hangarCamoCache.clear(), g_config.collectCamouflageData()
    g_config.teamCamo = dict.fromkeys(('ally', 'enemy'))


@overrideMethod(_ExecuteAfterHangarSpaceInited)
def _executeEnqueuedCalls(base, self, *a, **k):
    BigWorld_callback(0, base, self, *a, **k)
