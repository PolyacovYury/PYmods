from gui.Scaleform.genConsts.SEASONS_CONSTANTS import SEASONS_CONSTANTS
from items.components.c11n_constants import SeasonType
from .. import g_config
from ..constants import SEASON_NAME_TO_TYPE


class CSMode(object):
    BUY, INSTALL = range(2)
    NAMES = {BUY: 'buy', INSTALL: 'install'}
    BUTTONS = {INSTALL: 1, BUY: 2}
    FROM_BUTTONS = {1: INSTALL, 2: BUY}


def getItemSeason(item):
    import operator
    name, key = (item.descriptor.userKey, 'custom') if item.priceGroup == 'custom' else (item.id, 'remap')
    cfg = g_config.camouflages[key].get(name, {})
    seasons = cfg.get('season', []) or [x for x in SEASONS_CONSTANTS.SEASONS if SEASON_NAME_TO_TYPE[x] & item.season]
    return reduce(operator.ior, (SEASON_NAME_TO_TYPE[x] for x in seasons), SeasonType.UNDEFINED)
