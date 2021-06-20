import nations
import re
from gui.Scaleform.daapi.view.lobby.customization import customization_properties_sheet, customization_carousel, popovers
from gui.Scaleform.daapi.view.lobby.customization import vehicle_anchor_states, shared as lobby_shared
from gui.Scaleform.daapi.view.lobby.customization.context import custom_mode, editable_style_mode
from gui.Scaleform.daapi.view.lobby.customization.shared import (
    TYPES_ORDER, CustomizationTabs, ITEM_TYPE_TO_TAB, ITEM_TYPE_TO_SLOT_TYPE)
from gui.Scaleform.genConsts.SEASONS_CONSTANTS import SEASONS_CONSTANTS
from gui.customization import shared as gui_shared
from gui.customization.constants import CustomizationModes
from gui.shared.gui_items import GUI_ITEM_TYPE
from helpers import dependency
from helpers.i18n import makeString as _ms
from items.components.c11n_constants import SeasonType, ItemTags, ProjectionDecalFormTags, CustomizationType
from skeletons.gui.customization import ICustomizationService
from vehicle_outfit.outfit import Area
from .. import g_config
from ..constants import SEASON_NAME_TO_TYPE


class CSMode(object):
    PURCHASE, INSTALL = ALL = range(2)
    NAMES = ['buy', 'install']
    BUTTONS = [1, 0]
    FROM_BUTTONS = [INSTALL, PURCHASE]


CustomizationTabs.INSIGNIA = 8
CustomizationTabs.ALL += (CustomizationTabs.INSIGNIA,)
CustomizationTabs.MODES[CustomizationModes.CUSTOM] += (CustomizationTabs.INSIGNIA,)
CustomizationTabs.SLOT_TYPES[CustomizationTabs.INSIGNIA] = GUI_ITEM_TYPE.INSIGNIA
CustomizationTabs.ITEM_TYPES[CustomizationTabs.INSIGNIA] = (GUI_ITEM_TYPE.INSIGNIA,)
ITEM_TYPE_TO_TAB[GUI_ITEM_TYPE.INSIGNIA] = CustomizationTabs.INSIGNIA
ITEM_TYPE_TO_SLOT_TYPE[GUI_ITEM_TYPE.INSIGNIA] = GUI_ITEM_TYPE.INSIGNIA
vehicle_anchor_states.REGIONS_SLOTS += (GUI_ITEM_TYPE.INSIGNIA,)
gui_shared.C11N_ITEM_TYPE_MAP[GUI_ITEM_TYPE.INSIGNIA] = CustomizationType.INSIGNIA
TYPES_ORDER = (GUI_ITEM_TYPE.INSIGNIA,) + TYPES_ORDER
customization_carousel.TYPES_ORDER = popovers.TYPES_ORDER = TYPES_ORDER


def getItemSeason(item):
    if item.itemTypeID != GUI_ITEM_TYPE.CAMOUFLAGE:
        return item.season
    import operator
    name, key = (item.descriptor.userKey, 'custom') if item.priceGroup == 'custom' else (item.id, 'remap')
    cfg = g_config.camouflages[key].get(name, {})
    seasons = cfg.get('season', []) or [x for x in SEASONS_CONSTANTS.SEASONS if SEASON_NAME_TO_TYPE[x] & item.season]
    return reduce(operator.ior, (SEASON_NAME_TO_TYPE[x] for x in seasons), SeasonType.UNDEFINED)


@dependency.replace_none_kwargs(service=ICustomizationService)
def CSComparisonKey(item, service=None):
    nationIDs = [n for filterNode in getattr(item.descriptor.filter, 'include', ()) for n in filterNode.nations or []]
    is3D, isVictim, isGlobal, texName = False, False, False, ''
    if item.itemTypeID == GUI_ITEM_TYPE.STYLE:
        if item.modelsSet:
            is3D = True
        if any('Victim' in tag for tag in item.tags):
            isVictim = True
    if item.itemTypeID == GUI_ITEM_TYPE.CAMOUFLAGE:
        if 'victim' in item.descriptor.userKey:
            isVictim = True
        isGlobal = g_config.isCamoGlobal(item.descriptor)
        if item.priceGroup == 'camouflages 50g notInShop':
            texName = getattr(item, 'texture', '').lower()
            if '/' in texName:
                texName = texName.rsplit('/', 1)[-1]
    return (TYPES_ORDER.index(item.itemTypeID) if item.itemTypeID in TYPES_ORDER else 0, not is3D,
            ItemTags.NATIONAL_EMBLEM not in item.tags, item.priceGroup == 'custom', item.isHidden, isVictim, not isGlobal,
            len(nationIDs) != 1, getGroupName(item, service.getCtx().isPurchase), item.isRare(),
            0 if not hasattr(item, 'formfactor') else ProjectionDecalFormTags.ALL.index(item.formfactor), texName, item.id)


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
    nationIDs = [n for filterNode in getattr(item.descriptor.filter, 'include', ()) for n in filterNode.nations or []]
    nation = ''
    if len(nationIDs) == 1:
        nation = _ms('#vehicle_customization:repaint/%s_base_color' % nations.NAMES[nationIDs[0]])
    elif len(nationIDs) > 1:
        nation = g_config.i18n['flashCol_group_multinational']
    if group and nation:  # HangarPainter support
        group = re.sub(r'( [^ <>]+)(?![^ <>]*>)', '', nation) + g_config.i18n['flashCol_group_separator'] + group
    return group


def getAvailableRegions(areaId, slotType, vehicleDescr=None):
    if slotType == GUI_ITEM_TYPE.INSIGNIA:
        if areaId != Area.GUN:
            return ()
        return old_getAvailableRegions(areaId, GUI_ITEM_TYPE.PAINT, vehicleDescr)[:1]
    return old_getAvailableRegions(areaId, slotType, vehicleDescr)


old_getAvailableRegions = gui_shared.getAvailableRegions
for obj in (gui_shared, lobby_shared, custom_mode, customization_properties_sheet, editable_style_mode):
    setattr(obj, 'getAvailableRegions', getAvailableRegions)
