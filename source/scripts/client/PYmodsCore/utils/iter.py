import random

__all__ = ('pickRandomPart', 'remDups', 'objToDict',)


def remDups(seq):  # Dave Kirby, order preserving
    seen = set()
    return [x for x in seq if x not in seen and not seen.add(x)]


def objToDict(obj):
    if isinstance(obj, list):
        return [objToDict(o) for o in obj]
    elif hasattr(obj, 'toDict'):
        return {k: objToDict(v) for k, v in obj.toDict().iteritems()}
    elif isinstance(obj, dict):  # just in case
        return {k: objToDict(v) for k, v in obj.iteritems()}
    return obj


def pickRandomPart(variantList, lastID, isRandom=True):
    if not variantList:
        return ['', -1]
    elif len(variantList) == 1:
        return variantList[0], 0
    newID = lastID
    while isRandom and newID == lastID:
        newID = random.randrange(len(variantList))
    if not isRandom:
        newID = (newID + 1) % len(variantList)
    return variantList[newID], newID
