from shared_utils import CONST_CONTAINER


class RandMode(CONST_CONTAINER):
    OFF, TEAM, RANDOM = range(3)
    NAMES = {OFF: 'off', RANDOM: 'random', TEAM: 'team'}
    INDICES = {v: k for k, v in NAMES.iteritems()}


class TeamMode(CONST_CONTAINER):
    ALLY, ENEMY, BOTH = range(1, 4)
    NAMES = {ALLY: 'ally', ENEMY: 'enemy', BOTH: 'both'}
    INDICES = {v: k for k, v in NAMES.iteritems()}
