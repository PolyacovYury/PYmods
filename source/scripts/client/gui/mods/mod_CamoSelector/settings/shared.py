from gui.Scaleform.daapi.view.lobby.customization.shared import TABS_SLOT_TYPE_MAPPING
from gui.Scaleform.genConsts.SEASONS_CONSTANTS import SEASONS_CONSTANTS
from gui.shared.gui_items import GUI_ITEM_TYPE
from items.components.c11n_constants import SeasonType
from shared_utils import CONST_CONTAINER
from .. import g_config
from ..constants import SEASON_NAME_TO_TYPE


class CSMode(CONST_CONTAINER):
    BUY, INSTALL, SETUP = range(3)
    NAMES = {BUY: 'buy', INSTALL: 'install', SETUP: 'setup'}


class CSTabs(CONST_CONTAINER):
    STYLE, PAINT, CAMO_SHOP, CAMO_HIDDEN, CAMO_GLOBAL, CAMO_CUSTOM, EMBLEM, INSCRIPTION, PROJECTION_DECAL, EFFECT = ALL = \
        range(10)
    AVAILABLE_REGIONS = (PAINT, CAMO_SHOP, CAMO_HIDDEN, CAMO_GLOBAL, CAMO_CUSTOM, EMBLEM, INSCRIPTION, PROJECTION_DECAL)
    VISIBLE = ALL  # legacy, maybe not all tabs will be visible, idk
    CAMO = (CAMO_SHOP, CAMO_HIDDEN, CAMO_GLOBAL, CAMO_CUSTOM)
    REGIONS = CAMO + (STYLE, EFFECT, PAINT)


ITEM_TO_TABS = {GUI_ITEM_TYPE.STYLE: (CSTabs.STYLE,),
                GUI_ITEM_TYPE.PAINT: (CSTabs.PAINT,), GUI_ITEM_TYPE.CAMOUFLAGE: CSTabs.CAMO,
                GUI_ITEM_TYPE.EMBLEM: (CSTabs.EMBLEM,), GUI_ITEM_TYPE.INSCRIPTION: (CSTabs.INSCRIPTION,),
                GUI_ITEM_TYPE.PERSONAL_NUMBER: (CSTabs.INSCRIPTION,),
                GUI_ITEM_TYPE.PROJECTION_DECAL: (CSTabs.PROJECTION_DECAL,),
                GUI_ITEM_TYPE.MODIFICATION: (CSTabs.EFFECT,)}


def tabToItem(tabIndex, isBuy):
    if isBuy:
        return TABS_SLOT_TYPE_MAPPING.get(tabIndex)
    return next(itemType for itemType in ITEM_TO_TABS if tabIndex in ITEM_TO_TABS[itemType])


class ACTION_ALIASES:
    CHANGE_SUMMER = 8
    CHANGE_WINTER = 9
    CHANGE_DESERT = 10
    CHANGE_ALLY = 11
    CHANGE_ENEMY = 12


def getItemSeason(item):
    import operator
    itemName, itemKey = (item.descriptor.userKey, 'custom') if item.priceGroup == 'custom' else (item.id, 'remap')
    cfg = g_config.camouflages[itemKey].get(itemName, {})
    seasons = cfg.get('season', []) or [x for x in SEASONS_CONSTANTS.SEASONS if SEASON_NAME_TO_TYPE[x] & item.season]
    return reduce(operator.ior, (SEASON_NAME_TO_TYPE[x] for x in seasons), SeasonType.UNDEFINED)
