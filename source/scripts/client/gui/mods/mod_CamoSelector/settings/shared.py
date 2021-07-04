import BigWorld
import nations
import re
from BWUtil import AsyncReturn
from async import async, await
from frameworks.wulf import WindowLayer
from functools import partial
from gui import makeHtmlString
from gui.Scaleform.genConsts.SEASONS_CONSTANTS import SEASONS_CONSTANTS
from gui.hangar_cameras.hangar_camera_common import CameraRelatedEvents
from gui.impl.dialogs import dialogs
from gui.impl.dialogs.builders import WarningDialogBuilder, _setupButtonsBasedOnRes
from gui.impl.gen import R
from gui.shared import EVENT_BUS_SCOPE, g_eventBus
from gui.shared.gui_items import GUI_ITEM_TYPE
from gui.shared.personality import ServicesLocator as SL
from helpers import dependency
from helpers.i18n import makeString as _ms
from items.components.c11n_constants import ItemTags, ProjectionDecalFormTags, SeasonType
from items.vehicles import g_cache, getItemByCompactDescr
from skeletons.gui.customization import ICustomizationService
from .. import g_config
from ..constants import SEASON_NAME_TO_TYPE, TYPES_ORDER


def onVehicleLoadedOnce(handler):
    entity = BigWorld.player().hangarSpace.getVehicleEntity()
    if entity and entity.isVehicleLoaded:
        return handler()
    onLoaded = lambda e: (handler(), g_eventBus.removeListener(
        CameraRelatedEvents.VEHICLE_LOADING, onLoaded, EVENT_BUS_SCOPE.DEFAULT) if not e.ctx['started'] else None)
    g_eventBus.addListener(CameraRelatedEvents.VEHICLE_LOADING, onLoaded, EVENT_BUS_SCOPE.DEFAULT)


def getItemSeason(item):
    if item.itemTypeID != GUI_ITEM_TYPE.CAMOUFLAGE:
        return item.season
    import operator
    name, key = (item.descriptor.userKey, 'custom') if item.priceGroup == 'custom' else (item.id, 'remap')
    cfg = g_config.camouflages[key].get(name, {})
    seasons = cfg.get('season', []) or [x for x in SEASONS_CONSTANTS.SEASONS if SEASON_NAME_TO_TYPE[x] & item.season]
    return reduce(operator.ior, (SEASON_NAME_TO_TYPE[x] for x in seasons), SeasonType.UNDEFINED)


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
    return _ms('#vehicle_customization:repaint/%s_base_color' % nations.NAMES[nationID])


@dependency.replace_none_kwargs(service=ICustomizationService)
def CSComparisonKey(isPurchase, item=None, service=None):
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
        not is3D, isVictim, item.priceGroup == 'custom', nat_count == 0,
        (not (clan or vehicles), not clan, not vehicles) if not nat_count else (clan, nat_count != 1),
        getGroupName(item, service.getCtx().isPurchase), not item.isHistorical(), texName, item.isRare(),
        0 if not hasattr(item, 'formfactor') else ProjectionDecalFormTags.ALL.index(item.formfactor), item.id)


def getGroupName(item, isPurchase=False):
    group = item.groupUserName
    if isPurchase:
        return group
    if item.itemTypeID == GUI_ITEM_TYPE.STYLE:
        if item.modelsSet:
            group = _ms('#vehicle_customization:styles/unique_styles')
        if any('Victim' in tag for tag in item.tags):
            group = _ms('#vehicle_customization:victim_style/default')
    if item.itemTypeID == GUI_ITEM_TYPE.CAMOUFLAGE:
        if 'victim' in item.descriptor.userKey:
            group = _ms('#vehicle_customization:victim_style/default')
        if g_config.isCamoGlobal(item.descriptor):
            group = firstWord(_ms('#vehicle_customization:camouflage/Clan_camouflage_01/label'))
    nation = ''
    nationIDs = _getNations(item) if item.itemTypeID != GUI_ITEM_TYPE.INSIGNIA else ()
    if len(nationIDs) == 1:
        nation = nationName(nationIDs[0])
    elif nationIDs:
        nation = g_config.i18n['flashCol_group_multinational']
    vehicleNations = _getVehicles(item)
    if vehicleNations:
        group = _ms('#vehicle_customization:styles/unique_styles')
        nation = nationName(vehicleNations[0])
    if group and nation:  # HangarPainter support
        group = firstWord(nation) + g_config.i18n['flashCol_group_separator'] + group
    return group


@async
def createConfirmDialog(key):
    message = makeHtmlString('html_templates:lobby/customization/dialog', 'decal', {
        'value': g_config.i18n[key + '_message']})
    builder = WarningDialogBuilder().setFormattedMessage(message).setFormattedTitle(g_config.i18n[key + '_title'])
    _setupButtonsBasedOnRes(builder, R.strings.dialogs.common.confirm)  # the most convenient
    subview = SL.appLoader.getDefLobbyApp().containerManager.getContainer(WindowLayer.SUB_VIEW).getView()
    result = yield await(dialogs.showSimple(builder.build(parent=subview)))
    raise AsyncReturn(result)
