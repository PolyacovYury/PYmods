from shared_utils import CONST_CONTAINER
from ..shared import RandMode, isCamoInternational


class C11nMode(CONST_CONTAINER):
    """ Customization mode.
    """
    INSTALL, SETUP = range(2)
    NAMES = {INSTALL: 'install', SETUP: 'setup'}


class C11nTabs(CONST_CONTAINER):
    """
    Enumeration of customization item browser tabs.
    The order of the ALL property corresponds to the order the tab names will appear in.
    """
    SHOP, HIDDEN, INTERNATIONAL, CUSTOM = range(4)
    AVAILABLE_REGIONS = (SHOP, HIDDEN, INTERNATIONAL, CUSTOM)
    ALL = (SHOP, HIDDEN, INTERNATIONAL, CUSTOM)
    VISIBLE = ALL


TAB_TO_RAND_MODE = {
    C11nTabs.SHOP: (RandMode.OFF, RandMode.RANDOM),
    C11nTabs.HIDDEN: (RandMode.OFF, RandMode.RANDOM),
    C11nTabs.INTERNATIONAL: (RandMode.OFF, RandMode.RANDOM, RandMode.TEAM),
    C11nTabs.CUSTOM: (RandMode.OFF, RandMode.RANDOM, RandMode.TEAM)}


def isItemSuitableForTab(item, tabIndex):
    if item is None:
        return False
    from .. import g_config
    ct = C11nTabs
    isInter = isCamoInternational(g_config, item.descriptor)
    return not ((tabIndex == ct.SHOP and (item.isHidden or item.priceGroup == 'modded'))
                or (tabIndex == ct.HIDDEN and (not item.isHidden or isInter or item.priceGroup == 'modded'))
                or (tabIndex == ct.INTERNATIONAL and not isInter)
                or (tabIndex == ct.CUSTOM and item.priceGroup != 'modded'))
