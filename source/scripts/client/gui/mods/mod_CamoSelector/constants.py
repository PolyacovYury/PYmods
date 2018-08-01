from shared_utils import CONST_CONTAINER


class RandMode(CONST_CONTAINER):
    OFF, TEAM, RANDOM = range(3)
    NAMES = {OFF: 'off', RANDOM: 'random', TEAM: 'team'}
    INDICES = {v: k for k, v in NAMES.iteritems()}
