import BigWorld
import items.vehicles
import random
from Account import Account
from Avatar import PlayerAvatar
from CurrentVehicle import g_currentPreviewVehicle, g_currentVehicle
from HeroTank import _HeroTankAppearance
from PYmodsCore import loadJson, overrideMethod
from PlatoonTank import _PlatoonTankAppearance
from gui import g_tankActiveCamouflage
from gui.Scaleform.daapi.view.lobby.customization.shared import (
    CustomizationTabs, fitOutfit, getEditableStyleOutfitDiff, getEditableStyleOutfitDiffComponent,
)
from gui.customization.shared import C11N_ITEM_TYPE_MAP, SEASON_TYPE_TO_NAME, __isTurretCustomizable as isTurretCustom
from gui.hangar_vehicle_appearance import HangarVehicleAppearance
from gui.shared.gui_items import GUI_ITEM_TYPE, GUI_ITEM_TYPE_INDICES, GUI_ITEM_TYPE_NAMES
from helpers import dependency
from items import makeIntCompactDescrByID
from items.components.c11n_constants import CustomizationType, EMPTY_ITEM_ID, SeasonType
from items.customizations import CustomizationOutfit, EmptyComponent, createNationalEmblemComponents
from skeletons.gui.shared.gui_items import IGuiItemsFactory
from vehicle_outfit.outfit import Area
from vehicle_outfit.packers import pickPacker
from vehicle_systems.CompoundAppearance import CompoundAppearance
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
    styleCD = makeIntCompactDescrByID('customizationItem', CustomizationType.STYLE, styleId)
    return dependency.instance(IGuiItemsFactory).createCustomization(styleCD)


def createEmptyOutfit(vDesc, diffComp=None):
    component = CustomizationOutfit(decals=createNationalEmblemComponents(vDesc))
    if diffComp is not None:
        component = component.applyDiff(diffComp)
    return dependency.instance(IGuiItemsFactory).createOutfit(component=component, vehicleCD=vDesc.makeCompactDescr())


def applyStyleOverride(vDesc, outfit, seasonName, seasonCache, clean):
    season = SEASON_NAME_TO_TYPE[seasonName]
    vehicleCD = vDesc.makeCompactDescr()
    itemDB = items.vehicles.g_cache.customization20().itemTypes[CustomizationType.STYLE]
    styleInfo = seasonCache.get('style', {})
    styleId = styleInfo.get('id')
    if styleId is None:
        return outfit
    availableRegions = {areaId: {slotType: getAvailableRegions(
        areaId, slotType, vDesc) for slotType in CustomizationTabs.SLOT_TYPES.itervalues()} for areaId in Area.ALL}
    if styleId == EMPTY_ITEM_ID:
        if not outfit.id:
            if clean:  # item is being deleted while not applied at all. possible change after last cache
                seasonCache.pop('style', None)  # so we remove an obsolete key
            return outfit
        style = getStyleFromId(outfit.id)
        baseOutfit = style.getOutfit(season, vehicleCD=vehicleCD)
        if style.isProgressive:
            addOutfit = style.getAdditionalOutfit(outfit.progressionLevel, season, vehicleCD)
            if addOutfit is not None:
                baseOutfit = baseOutfit.patch(addOutfit)
        fitOutfit(baseOutfit, availableRegions)
        fitOutfit(outfit, availableRegions)
        diffComp = getEditableStyleOutfitDiffComponent(outfit, baseOutfit)
        diffComp.styleId = 0
        outfit = createEmptyOutfit(vDesc, diffComp)
        fitOutfit(outfit, availableRegions)
        return outfit
    if styleId not in itemDB:
        print g_config.ID + ': style', styleId, 'for', vDesc.name, 'deleted from game client.'
        seasonCache.pop('style', None)
        return outfit
    style = getStyleFromId(styleId)
    style_season = SEASON_NAME_TO_TYPE[styleInfo.get('season', seasonName)]
    outfit_level = outfit.progressionLevel if outfit.style and outfit.style.isProgression else 1
    if outfit.id != styleId:
        outfit = style.getOutfit(season, vehicleCD=vehicleCD)
        outfit_level = outfit.progressionLevel if outfit.style and outfit.style.isProgression else 1
    elif style_season != season:
        baseOutfit = style.getOutfit(season, vehicleCD=vehicleCD)
        if style.isProgressive:
            addOutfit = style.getAdditionalOutfit(outfit.progressionLevel, season, vehicleCD)
            if addOutfit is not None:
                baseOutfit = baseOutfit.patch(addOutfit)
        fitOutfit(baseOutfit, availableRegions)
        fitOutfit(outfit, availableRegions)
        outfit = style.getOutfit(style_season, vehicleCD=vehicleCD, diff=getEditableStyleOutfitDiff(outfit, baseOutfit))
        outfit_level = outfit.progressionLevel if outfit.style and outfit.style.isProgression else 1
    style_level = styleInfo.get('progressionLevel', 1)
    if style.isProgressive and outfit_level != style_level:
        outfit = style.getStyleProgressionOutfit(outfit, style_level, style_season)
    fitOutfit(outfit, availableRegions)
    return outfit


def applyOutfitCache(vDesc, outfit, seasonName, seasonCache, clean=True):
    try:
        outfit = applyStyleOverride(vDesc, outfit, seasonName, seasonCache, clean)
        itemDBs = items.vehicles.g_cache.customization20().itemTypes
        for itemTypeName, itemCache in seasonCache.items():
            if itemTypeName == 'style':
                continue
            slotType = GUI_ITEM_TYPE_INDICES[itemTypeName]
            itemDB = itemDBs[C11N_ITEM_TYPE_MAP[slotType]]
            for areaName, areaCache in itemCache.items():
                slot = outfit.getContainer(
                    (Area.MISC if areaName == 'misc' else TankPartNames.getIdx(areaName))).slotFor(slotType)
                for regionKey in areaCache.keys():
                    itemID = areaCache[regionKey]['id']
                    if itemID is None:
                        if slot.getItemCD(int(regionKey)):
                            slot.remove(int(regionKey))
                        elif clean:  # item is being deleted while not applied at all. possible change after last cache
                            del areaCache[regionKey]  # so we remove an obsolete key
                        continue
                    is_number = slotType == GUI_ITEM_TYPE.INSCRIPTION and 'number' in areaCache[regionKey]
                    if is_number:
                        itemDB = itemDBs[C11N_ITEM_TYPE_MAP[GUI_ITEM_TYPE.PERSONAL_NUMBER]]
                    if itemID not in itemDB:
                        print g_config.ID + ':', itemTypeName, 'ID', itemID, 'on', areaName, 'region', regionKey, 'not found'
                        del areaCache[regionKey]
                        itemDB = itemDBs[C11N_ITEM_TYPE_MAP[slotType]]
                        continue
                    component = (
                            pickPacker(slotType if not is_number else GUI_ITEM_TYPE.PERSONAL_NUMBER).getRawComponent()
                            or EmptyComponent)()
                    [setattr(component, k, v) for k, v in areaCache[regionKey].items()]
                    slot.set(itemDB[itemID].compactDescr, int(regionKey), component)
                    itemDB = itemDBs[C11N_ITEM_TYPE_MAP[slotType]]
        outfit.invalidate()
        return outfit
    except AttributeError:
        __import__('pprint').pprint(seasonCache)
        raise


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
        # TODO: paid/unpaid changes here
        # requirement = lambda _i: True  # paid
        # the rest is for unpaid
        from gui.customization.shared import createCustomizationBaseRequestCriteria
        from gui.shared.utils.requesters import REQ_CRITERIA
        itemRequirement = (createCustomizationBaseRequestCriteria(
            g_currentVehicle.item, g_currentVehicle.item.eventsCache.questsProgress, ()
        ) | REQ_CRITERIA.CUSTOM(lambda _item: not _item.isHiddenInUI())) ^ REQ_CRITERIA.CUSTOM(
            lambda _i: (_i.priceGroup == CUSTOM_GROUP_NAME)
        )
        requirement = lambda itemID: itemRequirement(g_currentVehicle.itemsCache.items.getItemByCD(makeIntCompactDescrByID(
            'customizationItem', CustomizationType.CAMOUFLAGE, itemID)))
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
        itemCD = slot.getItemCD(0)
        if not itemCD:
            continue
        item = dependency.instance(IGuiItemsFactory).createCustomization(itemCD)
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
                        camoID = getRandomCamoID(camoForSeason[teamMode], requirement)
                        item = camouflages[camoID]
                        patternSize = random.randrange(len(item.scales))
                        palette = random.randrange(len(item.palettes))
                        g_config.teamCamo[teamMode] = (camoID, palette, patternSize)
                    else:
                        camoID, palette, patternSize = g_config.teamCamo[teamMode]
                elif camoForSeason['random']:
                    camoID = getRandomCamoID(camoForSeason['random'], requirement)
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


def applyOutfitInfo(outfit, seasonName, vDesc, randomCache, isPlayerVehicle=True, vID=None):
    nationName, vehicleName = vDesc.name.split(':')
    try:
        isTurretCustomizable = isTurretCustom(vDesc)
    except ValueError:
        print g_config.ID + ': turret customization check for', vehicleName, 'failed:'
        __import__('traceback').print_exc()
        isTurretCustomizable = False
    if isPlayerVehicle:
        vehCache = g_config.outfitCache.get(nationName, {}).get(vehicleName, {})
        outfit = applyOutfitCache(vDesc, outfit, seasonName, vehCache.get(seasonName, {}))
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
    if (not g_config.data['enabled'] or not vDesc or vDesc.name in g_config.disabledVehicles or (
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
    if not g_config.data['enabled'] or vDesc.name in g_config.disabledVehicles or (
            vDesc.type.hasCustomDefaultCamouflage and g_config.data['disableWithDefault']):
        return outfit
    if not g_config.data['useBought']:
        outfit = createEmptyOutfit(vDesc)
    seasonName = SEASON_TYPE_TO_NAME[SeasonType.fromArenaKind(BigWorld.player().arena.arenaType.vehicleCamouflageKind)]
    return applyOutfitInfo(outfit, seasonName, vDesc, g_config.arenaCamoCache.setdefault(
        self.id, {}), self.id == BigWorld.player().playerVehicleID, self.id)


@overrideMethod(PlayerAvatar, 'onBecomePlayer')
def new_onBecomePlayer(base, self, *args, **kwargs):
    base(self, *args, **kwargs)
    g_config.arenaCamoCache.clear(), g_config.collectCamouflageData()


@overrideMethod(Account, 'onBecomePlayer')
def new_onBecomePlayer(base, self):
    base(self)
    g_config.hangarCamoCache.clear(), g_config.collectCamouflageData()
    g_config.teamCamo = dict.fromkeys(('ally', 'enemy'))
