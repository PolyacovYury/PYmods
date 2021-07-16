import BigWorld
import nations
import os
import re
from BWUtil import AsyncReturn
from CurrentVehicle import g_currentVehicle
from async import async, await
from frameworks.wulf import WindowLayer
from functools import partial
from gui.customization.shared import AREA_ID_BY_REGION
from gui.hangar_cameras.hangar_camera_common import CameraRelatedEvents
from gui.impl.backport import text
from gui.impl.dialogs import dialogs
from gui.impl.dialogs.builders import InfoDialogBuilder, WarningDialogBuilder, _setupButtonsBasedOnRes
from gui.impl.gen import R
from gui.impl.pub.dialog_window import DialogButtons as DButtons
from gui.shared import EVENT_BUS_SCOPE, g_eventBus
from gui.shared.gui_items import GUI_ITEM_TYPE
from gui.shared.personality import ServicesLocator as SL
from items.components.c11n_constants import ItemTags, MAX_PROJECTION_DECALS_PER_AREA, ProjectionDecalFormTags, SeasonType
from items.vehicles import g_cache, getItemByCompactDescr
from vehicle_outfit.outfit import Area
from .. import g_config
from ..constants import CUSTOM_GROUP_NAME, SEASON_NAME_TO_TYPE, TYPES_ORDER, insignia_names


def onVehicleLoadedOnce(handler, *a, **k):
    entity = BigWorld.player().hangarSpace.getVehicleEntity()
    if entity and entity.isVehicleLoaded:
        return handler(*a, **k)
    onLoaded = lambda e: (handler(*a, **k), g_eventBus.removeListener(
        CameraRelatedEvents.VEHICLE_LOADING, onLoaded, EVENT_BUS_SCOPE.DEFAULT) if not e.ctx['started'] else None)
    g_eventBus.addListener(CameraRelatedEvents.VEHICLE_LOADING, onLoaded, EVENT_BUS_SCOPE.DEFAULT)


def getItemSeason(item):
    if item.itemTypeID != GUI_ITEM_TYPE.CAMOUFLAGE:
        return item.season
    name, key = (item.descriptor.userKey, 'custom') if item.priceGroup == 'custom' else (item.id, 'remap')
    seasons = g_config.camo_settings[key].get(name, {}).get('season', [])
    return item.season if not seasons else reduce(
        __import__('operator').ior, (SEASON_NAME_TO_TYPE[x] for x in seasons), SeasonType.UNDEFINED)


def _getVehicles(item):
    nationIDs = set()
    for filterNode in getattr(item.descriptor.filter, 'include', ()):
        for intCD in (filterNode.vehicles or []):
            nationIDs.add(getItemByCompactDescr(intCD).customizationNationID)
    return list(nationIDs)


def getInsigniaNation(item):
    for nation_idx, item_id in g_cache.customization20().defaultInsignias.iteritems():
        if item_id == item.id:
            return nation_idx


def getInsigniaUserName(item):
    if item.itemTypeID != GUI_ITEM_TYPE.INSIGNIA:
        return item.userName
    nationID = getInsigniaNation(item)
    if nationID is not None:
        title = nationName(nationID)
    else:
        texture_id = os.path.basename(item.getIconApplied(None)).partition('_')[2].rpartition('_')[0]
        title = insignia_names.get(texture_id, texture_id)
    return item.userName or title


def _getNations(item):
    nationIDs = set()
    if _getVehicles(item):
        return list(nationIDs)
    for filterNode in getattr(item.descriptor.filter, 'include', ()):
        for n in (filterNode.nations or []):
            nationIDs.add(n)
    if item.itemTypeID == GUI_ITEM_TYPE.INSIGNIA:
        nationID = getInsigniaNation(item)
        if nationID is not None:
            nationIDs.add(nationID)
    return list(nationIDs)


def firstWord(fromString, replace_with=''):
    return re.sub(r'( [^<>]*)(?![^ <>]*[> ])', replace_with, fromString)


def nationName(nationID):
    return text(R.strings.vehicle_customization.repaint.dyn(nations.NAMES[nationID] + '_base_color')())


def CSComparisonKey(isPurchase, item=None):
    if item is None:
        return partial(CSComparisonKey, isPurchase)
    tags, is3D, isVictim, clan, texName = item.tags, False, False, False, ''
    nat_count, vehicles = len(_getNations(item)), _getVehicles(item)
    if item.itemTypeID == GUI_ITEM_TYPE.STYLE:
        if item.modelsSet:
            is3D = True
        if any('Victim' in tag for tag in tags):
            isVictim = True
    if item.itemTypeID == GUI_ITEM_TYPE.CAMOUFLAGE:
        if 'victim' in item.descriptor.userKey:
            isVictim = True
        clan = g_config.isCamoGlobal(item.descriptor) and not vehicles
        if item.priceGroup == 'camouflages 50g notInShop':
            texName = getattr(item, 'texture', '').lower()
            if '/' in texName:
                texName = texName.rsplit('/', 1)[-1]
    order = TYPES_ORDER if isPurchase else (GUI_ITEM_TYPE.STYLE,) + tuple(i for i in TYPES_ORDER if i != GUI_ITEM_TYPE.STYLE)
    return (
        order.index(item.itemTypeID) if item.itemTypeID in order else -1, ItemTags.NATIONAL_EMBLEM not in tags,
        not is3D, isVictim, item.priceGroup == CUSTOM_GROUP_NAME, nat_count == 0,
        (not (clan or vehicles), not clan, not vehicles) if not nat_count else (clan, nat_count != 1),
        getGroupName(item, isPurchase), item.customizationDisplayType(), texName, item.isRare(),
        0 if not hasattr(item, 'formfactor') else ProjectionDecalFormTags.ALL.index(item.formfactor), item.id)


def getGroupName(item, isPurchase=False):
    group = item.groupUserName
    if isPurchase:
        return group
    if item.itemTypeID == GUI_ITEM_TYPE.STYLE:
        if item.modelsSet:
            group = text(R.strings.vehicle_customization.styles.unique_styles())
        if any('Victim' in tag for tag in item.tags):
            group = text(R.strings.vehicle_customization.victim_style.default())
    if item.itemTypeID == GUI_ITEM_TYPE.CAMOUFLAGE:
        if 'victim' in item.descriptor.userKey:
            group = text(R.strings.vehicle_customization.victim_style.default())
        if g_config.isCamoGlobal(item.descriptor):
            group = firstWord(text(R.strings.vehicle_customization.camouflage.Clan_camouflage_01.label()))
    nation = ''
    nationIDs = _getNations(item) if item.itemTypeID != GUI_ITEM_TYPE.INSIGNIA else ()
    if len(nationIDs) == 1:
        nation = nationName(nationIDs[0])
    elif nationIDs:
        nation = g_config.i18n['flashCol_group_multinational']
    vehicleNations = _getVehicles(item)
    if vehicleNations:
        group = text(R.strings.vehicle_customization.styles.unique_styles())
        nation = nationName(vehicleNations[0])
    if group and nation:  # HangarPainter support
        group = firstWord(nation) + g_config.i18n['flashCol_group_separator'] + group
    return group


@async
def createConfirmDialog(key):
    builder = WarningDialogBuilder().setFormattedMessage(
        g_config.i18n[key + '_message']).setFormattedTitle(g_config.i18n[key + '_title'])
    _setupButtonsBasedOnRes(builder, R.strings.dialogs.common.confirm)  # the most convenient
    subview = SL.appLoader.getDefLobbyApp().containerManager.getContainer(WindowLayer.SUB_VIEW).getView()
    result = yield await(dialogs.showSimple(builder.build(parent=subview)))
    raise AsyncReturn(result)


@async
def createDonationDialog():
    if hasattr(createDonationDialog, 'shown'):
        return
    createDonationDialog.shown = True
    builder = InfoDialogBuilder().setFormattedTitle(
        g_config.i18n['flashCol_freeVersion_title']).setFormattedMessage(g_config.i18n['flashCol_freeVersion_message'])
    for ID, key in (DButtons.PURCHASE, 'patreon'), (DButtons.RESEARCH, 'boosty'), (DButtons.CANCEL, 'close'):
        builder.addButton(ID, None, ID == DButtons.PURCHASE, rawLabel=g_config.i18n['flash_freeVersion_button_%s' % key])
    subview = SL.appLoader.getDefLobbyApp().containerManager.getContainer(WindowLayer.SUB_VIEW).getView()
    result = yield await(dialogs.show(builder.build(parent=subview)))
    if result.result == DButtons.PURCHASE:
        BigWorld.wg_openWebBrowser('https://www.patreon.com/polyacov_yury/')
    elif result.result == DButtons.RESEARCH:
        BigWorld.wg_openWebBrowser('https://boosty.to/polyacov_yury/')


def fixIconPath(icon):
    if '4278190335,4278255360,4294901760,' in icon:
        icon = '../../' + icon.split('"', 2)[1]
    return icon


def isStyleSeasoned(style):
    vehCD = g_currentVehicle.item.descriptor.makeCompactDescr()
    outfit = style.getOutfit(SeasonType.SUMMER, vehCD)
    return not (
            outfit.isEqual(style.getOutfit(SeasonType.WINTER, vehCD))
            and outfit.isEqual(style.getOutfit(SeasonType.DESERT, vehCD)))


def isSlotLocked(outfit, slotId):
    if slotId.slotType != GUI_ITEM_TYPE.PROJECTION_DECAL:
        return False
    limit = MAX_PROJECTION_DECALS_PER_AREA
    slot = outfit.getContainer(slotId.areaId).slotFor(slotId.slotType)
    regions = slot.getRegions()
    getShowOn = lambda _regionIdx: g_currentVehicle.item.getAnchorBySlotId(slotId.slotType, slotId.areaId, _regionIdx).showOn
    getAreaIds = lambda _showOn: set(areaId for _region, areaId in AREA_ID_BY_REGION.items() if _region & _showOn)
    filledRegions = {areaId: [] for areaId in Area.TANK_PARTS}
    for region, _, __ in slot.items():
        regionIdx = regions.index(region)
        for areaId in getAreaIds(getShowOn(regionIdx)):
            filledRegions[areaId].append(regionIdx)
    areaIds = getAreaIds(getShowOn(slotId.regionIdx))
    return any(
        len(_filledRegions) >= limit and slotId.regionIdx not in _filledRegions
        for areaId, _filledRegions in filledRegions.items() if areaId in areaIds)
