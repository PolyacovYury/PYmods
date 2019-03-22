from gui.Scaleform.genConsts.SEASONS_CONSTANTS import SEASONS_CONSTANTS
from items.components.c11n_constants import SeasonType
from shared_utils import CONST_CONTAINER


class RandMode(CONST_CONTAINER):
    OFF, TEAM, RANDOM = range(3)
    NAMES = {OFF: 'off', RANDOM: 'random', TEAM: 'team'}
    INDICES = {v: k for k, v in NAMES.iteritems()}


SEASON_NAME_TO_TYPE = {SEASONS_CONSTANTS.SUMMER: SeasonType.SUMMER, SEASONS_CONSTANTS.WINTER: SeasonType.WINTER,
                       SEASONS_CONSTANTS.DESERT: SeasonType.DESERT}
