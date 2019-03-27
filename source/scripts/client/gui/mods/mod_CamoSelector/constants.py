from gui.Scaleform.genConsts.SEASONS_CONSTANTS import SEASONS_CONSTANTS
from items.components.c11n_constants import SeasonType


class SelectionMode(object):
    ALL = OFF, TEAM, RANDOM = range(3)
    NAMES = {OFF: 'off', TEAM: 'team', RANDOM: 'random'}
    INDICES = {v: k for k, v in NAMES.iteritems()}


SEASON_NAME_TO_TYPE = {SEASONS_CONSTANTS.SUMMER: SeasonType.SUMMER, SEASONS_CONSTANTS.WINTER: SeasonType.WINTER,
                       SEASONS_CONSTANTS.DESERT: SeasonType.DESERT}
