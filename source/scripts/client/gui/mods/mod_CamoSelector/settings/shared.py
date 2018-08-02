from gui.Scaleform.daapi.view.lobby.customization.shared import TABS_ITEM_MAPPING
from gui.shared.gui_items import GUI_ITEM_TYPE
from shared_utils import CONST_CONTAINER


class CSMode(CONST_CONTAINER):
    BUY, INSTALL, SETUP = range(3)
    NAMES = {BUY: 'buy', INSTALL: 'install', SETUP: 'setup'}


class CSTabs(CONST_CONTAINER):
    STYLE, PAINT, CAMO_SHOP, CAMO_HIDDEN, CAMO_GLOBAL, CAMO_CUSTOM, EMBLEM, INSCRIPTION, EFFECT = ALL = range(9)
    AVAILABLE_REGIONS = (PAINT, CAMO_SHOP, CAMO_HIDDEN, CAMO_GLOBAL, CAMO_CUSTOM, EMBLEM, INSCRIPTION)
    VISIBLE = ALL  # legacy, maybe not all tabs will be visible, idk
    CAMO = (CAMO_SHOP, CAMO_HIDDEN, CAMO_GLOBAL, CAMO_CUSTOM)
    REGIONS = CAMO + (STYLE, EFFECT, PAINT)


ITEM_TO_TABS = {GUI_ITEM_TYPE.PAINT: (CSTabs.PAINT,), GUI_ITEM_TYPE.CAMOUFLAGE: CSTabs.CAMO,
                GUI_ITEM_TYPE.EMBLEM: (CSTabs.EMBLEM,), GUI_ITEM_TYPE.INSCRIPTION: (CSTabs.INSCRIPTION,),
                GUI_ITEM_TYPE.MODIFICATION: (CSTabs.EFFECT,), GUI_ITEM_TYPE.STYLE: (CSTabs.STYLE,)}


def tabToItem(tabIndex, mode):
    if mode == CSMode.BUY:
        return TABS_ITEM_MAPPING.get(tabIndex)
    return next(itemType for itemType in ITEM_TO_TABS if tabIndex in ITEM_TO_TABS[itemType])


class ACTION_ALIASES:
    CHANGE_ALLY = 11
    CHANGE_ENEMY = 12
