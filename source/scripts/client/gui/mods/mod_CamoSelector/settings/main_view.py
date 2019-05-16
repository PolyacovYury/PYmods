from CurrentVehicle import g_currentVehicle
from PYmodsCore import overrideMethod
from gui.Scaleform.daapi.view.lobby.customization.main_view import MainView as WGMainView
from gui.Scaleform.daapi.view.lobby.customization.shared import SEASONS_ORDER
from gui.shared.gui_items import GUI_ITEM_TYPE
from .. import g_config


class MainView(WGMainView):
    def __setNotificationCounters(self):
        currentSeason = self.__ctx.currentSeason
        seasonCounters = {season: 0 for season in SEASONS_ORDER}
        itemTypes = GUI_ITEM_TYPE.CUSTOMIZATIONS if self.__ctx.isBuy else ()
        for season in SEASONS_ORDER:
            seasonCounters[season] = (
                0 if not itemTypes or currentSeason == season else g_currentVehicle.item.getC11nItemsNoveltyCounter(
                    g_currentVehicle.itemsCache.items, itemTypes, season))

        self.as_setNotificationCountersS([seasonCounters[season] for season in SEASONS_ORDER])


@overrideMethod(WGMainView, '__new__')
def new(base, cls, *a, **kw):
    if not g_config.data['enabled']:
        return base(cls, *a, **kw)
    return base(MainView, *a, **kw)
