import nations
import re
from gui.Scaleform.daapi.view.lobby.customization.shared import TYPES_ORDER
from gui.Scaleform.genConsts.SEASONS_CONSTANTS import SEASONS_CONSTANTS
from gui.shared.gui_items import GUI_ITEM_TYPE
from helpers import dependency
from helpers.i18n import makeString as _ms
from items.components.c11n_constants import SeasonType, ItemTags, ProjectionDecalFormTags
from skeletons.gui.customization import ICustomizationService
from .. import g_config
from ..constants import SEASON_NAME_TO_TYPE


class CSMode(object):
    PURCHASE, INSTALL = ALL = range(2)
    NAMES = ['buy', 'install']
    BUTTONS = [1, 0]
    FROM_BUTTONS = [INSTALL, PURCHASE]


def getItemSeason(item):
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
