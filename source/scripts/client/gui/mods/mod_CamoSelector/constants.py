from gui.Scaleform.genConsts.SEASONS_CONSTANTS import SEASONS_CONSTANTS
from items.components.c11n_constants import SeasonType


class SelectionMode(object):
    ALL = OFF, TEAM, RANDOM = range(3)


SEASON_NAME_TO_TYPE = {SEASONS_CONSTANTS.SUMMER: SeasonType.SUMMER, SEASONS_CONSTANTS.WINTER: SeasonType.WINTER,
                       SEASONS_CONSTANTS.DESERT: SeasonType.DESERT}
