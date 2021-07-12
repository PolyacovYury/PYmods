from goodies.goodie_constants import GOODIE_RESOURCE_TYPE
from gui.Scaleform.daapi.view.lobby.storage import StorageCategoryPersonalReservesView
from gui.goodies.goodie_items import BOOSTERS_ORDERS

misc_xp_tiers = (300, 200, 100, 50)
tank_xp_tiers = (100, 50, 25)
credits_tiers = (50, 25)


def item_tier(item):
    bType = item.boosterType
    tiers = (
        misc_xp_tiers if bType in (GOODIE_RESOURCE_TYPE.CREW_XP, GOODIE_RESOURCE_TYPE.FREE_XP) else
        tank_xp_tiers if bType in (GOODIE_RESOURCE_TYPE.XP,) else
        credits_tiers if bType in (GOODIE_RESOURCE_TYPE.CREDITS,) else
        ())
    try:
        return tiers.index(item.effectValue)
    except ValueError:
        return -1


def new_sort(_, a, b):
    return cmp(item_tier(a), item_tier(b)) or cmp(BOOSTERS_ORDERS[a.boosterType], BOOSTERS_ORDERS[b.boosterType]) or cmp(
        b.effectTime, a.effectTime)


StorageCategoryPersonalReservesView._StorageCategoryPersonalReservesView__sort = new_sort
print 'ReorderPersonalReserves v.1.0.0 by Polyacov_Yury: initialised.'
