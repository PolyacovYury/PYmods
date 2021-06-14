from CurrentVehicle import g_currentVehicle
from PYmodsCore import overrideMethod
from gui.Scaleform.daapi.view.lobby.customization import shared as sh
from gui.Scaleform.daapi.view.lobby.customization.main_view import MainView as WGMainView, _logger
from gui.customization.constants import CustomizationModes
from gui.customization.shared import SEASONS_ORDER
from gui.impl import backport
from gui.impl.gen import R
from gui.shared.formatters import icons, text_styles
from gui.shared.gui_items import GUI_ITEM_TYPE
from gui.shared.utils.requesters import REQ_CRITERIA
from items.components.c11n_constants import EDITABLE_STYLE_STORAGE_DEPTH
from .. import g_config


class MainView(WGMainView):
    def __setNotificationCounters(self):
        itemTypes = sh.getItemTypesAvailableForVehicle() if self.__ctx.isPurchase else ()
        if not itemTypes:
            return self.as_setNotificationCountersS([0 for _ in SEASONS_ORDER])
        seasonCounters = {season: 0 for season in SEASONS_ORDER}
        itemsFilter = ~REQ_CRITERIA.CUSTOMIZATION.ALL_SEASON
        if self.__ctx.modeId == sh.CustomizationModes.EDITABLE_STYLE:
            itemsFilter |= REQ_CRITERIA.CUSTOM(lambda item: self.__ctx.mode.style.isItemInstallable(item))
        for season in SEASONS_ORDER:
            if season != self.__ctx.season:
                seasonCounters[season] = g_currentVehicle.item.getC11nItemsNoveltyCounter(
                    g_currentVehicle.itemsCache.items, itemTypes, season, itemsFilter)
        self.as_setNotificationCountersS([seasonCounters[season] for season in SEASONS_ORDER])

    def onPressClearBtn(self):
        super(MainView, self).onPressClearBtn()
        self.__ctx.cancelChanges()

    # noinspection DuplicatedCode
    def as_setHeaderDataS(self, data):
        if self.__ctx.isPurchase and self.__ctx.mode.modeId == CustomizationModes.STYLED:
            showSpecialLabel = False
            counter = 0
            for intCD in self.__bottomPanel._carouselDP.collection:
                item = self.service.getItemByCD(intCD)
                if item.itemTypeID != GUI_ITEM_TYPE.STYLE:
                    break
                if item.canBeEditedForVehicle(g_currentVehicle.item.intCD):
                    counter += 1
                if counter > EDITABLE_STYLE_STORAGE_DEPTH:
                    showSpecialLabel = True
                    break
            if showSpecialLabel:
                storedStylesCount = len(self.service.getStoredStyleDiffs())
                img = icons.makeImageTag(backport.image(R.images.gui.maps.icons.customization.edited_big()))
                label = text_styles.vehicleStatusSimpleText(backport.text(
                    R.strings.vehicle_customization.savedStyles.label(), img=img, current=storedStylesCount,
                    max=EDITABLE_STYLE_STORAGE_DEPTH))
                data['tankInfo'] = label
        return super(MainView, self).as_setHeaderDataS(data)

    def __selectFirstVisibleTab(self):
        visibleTabs = self.__bottomPanel.getVisibleTabs()
        if visibleTabs:
            if self.__ctx.mode.tabId not in visibleTabs:
                self.__ctx.mode.changeTab(visibleTabs[0])
        else:
            _logger.error('There is no visible customization tabs for current vehicle: %s', g_currentVehicle.item)


@overrideMethod(WGMainView, '__new__')
def new(base, cls, *a, **kw):
    if not g_config.data['enabled']:
        return base(cls, *a, **kw)
    return base(MainView, *a, **kw)
