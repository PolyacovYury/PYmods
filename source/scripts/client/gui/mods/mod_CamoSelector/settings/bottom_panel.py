import traceback

from CurrentVehicle import g_currentVehicle
from gui import InputHandler
from gui.Scaleform.daapi.settings.views import VIEW_ALIAS
from gui.Scaleform.daapi.view.lobby.customization.customization_bottom_panel import CustomizationBottomPanel as CBP
from gui.Scaleform.daapi.view.lobby.customization.shared import getTotalPurchaseInfo
from gui.Scaleform.locale.ITEM_TYPES import ITEM_TYPES
from gui.Scaleform.locale.RES_ICONS import RES_ICONS
from gui.Scaleform.locale.TOOLTIPS import TOOLTIPS
from gui.Scaleform.locale.VEHICLE_CUSTOMIZATION import VEHICLE_CUSTOMIZATION
from gui.shared.formatters import getItemPricesVO, text_styles, getMoneyVO
from gui.shared.gui_items import GUI_ITEM_TYPE_NAMES, GUI_ITEM_TYPE
from gui.shared.gui_items.gui_item_economics import ITEM_PRICE_EMPTY
from gui.shared.money import Money
from gui.shared.utils.functions import makeTooltip
from gui.shared.utils.graphics import isRendererPipelineDeferred
from helpers.i18n import makeString as _ms
from .carousel import updateTabGroups
from .item_vo import buildCustomizationItemDataVO
from .shared import CSMode, tabToItem
from .. import g_config


class CustomizationBottomPanel(CBP):
    def _populate(self):
        self.__isShiftDown = False
        super(CustomizationBottomPanel, self)._populate()
        InputHandler.g_instance.onKeyDown += self.__handleKeyEvent
        InputHandler.g_instance.onKeyUp += self.__handleKeyEvent

    def _dispose(self):
        InputHandler.g_instance.onKeyDown -= self.__handleKeyEvent
        InputHandler.g_instance.onKeyUp -= self.__handleKeyEvent
        super(CustomizationBottomPanel, self)._dispose()

    def __handleKeyEvent(self, event):
        import Keys
        if event.key in [Keys.KEY_LSHIFT, Keys.KEY_RSHIFT]:
            if self.__isShiftDown != event.isKeyDown():
                self.__isShiftDown = event.isKeyDown()
                self.__setFooterInitData()

    def _carouseItemWrapper(self, itemCD):
        item = self.service.getItemByCD(itemCD)
        itemInventoryCount = self.__ctx.getItemInventoryCount(item)
        purchaseLimit = self.__ctx.getPurchaseLimit(item)
        showUnsupportedAlert = item.itemTypeID == GUI_ITEM_TYPE.MODIFICATION and not isRendererPipelineDeferred()
        isCurrentlyApplied = itemCD in self._carouselDP.getCurrentlyApplied()
        noPrice = item.buyCount <= 0
        isDarked = purchaseLimit == 0 and itemInventoryCount == 0
        isAlreadyUsed = isDarked and not isCurrentlyApplied
        autoRentEnabled = self.__ctx.autoRentEnabled()
        return buildCustomizationItemDataVO(
            item, itemInventoryCount, plainView=not self.__ctx.isBuy, showUnsupportedAlert=showUnsupportedAlert,
            isCurrentlyApplied=isCurrentlyApplied, isAlreadyUsed=isAlreadyUsed, forceLocked=isAlreadyUsed,
            isDarked=isDarked, noPrice=noPrice, autoRentEnabled=autoRentEnabled, vehicle=g_currentVehicle.item)

    def __setNotificationCounters(self):
        vehicle = g_currentVehicle.item
        proxy = g_currentVehicle.itemsCache.items
        tabsCounters = []
        for tabIdx in self.__ctx.visibleTabs:
            tabsCounters.append(vehicle.getC11nItemsNoveltyCounter(
                proxy, itemTypes=(tabToItem(tabIdx, self.__ctx.isBuy),), season=self.__ctx.currentSeason))
        self.as_setNotificationCountersS({'tabsCounters': tabsCounters,
                                          'switchersCounter': vehicle.getC11nItemsNoveltyCounter(proxy,
                                                                                                 itemTypes=GUI_ITEM_TYPE.CUSTOMIZATIONS)})

    def __setFooterInitData(self):
        self.__ctx.isSwitcherIgnored = True
        self.as_setBottomPanelInitDataS({
            'tabsAvailableRegions': self.__ctx.tabsData.AVAILABLE_REGIONS,
            'defaultStyleLabel': g_config.i18n['UI_flash_switcher_tabsInvisible'],
            'carouselInitData': self.__getCarouselInitData(),
            'filtersVO': {'popoverAlias': VIEW_ALIAS.CUSTOMIZATION_FILTER_POPOVER,
                          'mainBtn': {'value': RES_ICONS.MAPS_ICONS_BUTTONS_FILTER,
                                      'tooltip': VEHICLE_CUSTOMIZATION.CAROUSEL_FILTER_MAINBTN},
                          'hotFilters': [{'value': RES_ICONS.MAPS_ICONS_CUSTOMIZATION_STORAGE_ICON,
                                          'tooltip': VEHICLE_CUSTOMIZATION.CAROUSEL_FILTER_STORAGEBTN,
                                          'selected': self._carouselDP.getOwnedFilter()},
                                         {'value': RES_ICONS.MAPS_ICONS_BUTTONS_EQUIPPED_ICON,
                                          'tooltip': VEHICLE_CUSTOMIZATION.CAROUSEL_FILTER_EQUIPPEDBTN,
                                          'selected': self._carouselDP.getAppliedFilter()}]}})
        self.__updateSetSwitcherData()
        self.__setNotificationCounters()

    def __getSwitcherInitData(self, mode, rightEnabled):
        isShift = self.__isShiftDown
        leftMode = mode if not isShift else (mode - 1) % len(CSMode.NAMES)
        rightMode = (leftMode + 1) % len(CSMode.NAMES)
        return {'leftLabel': g_config.i18n['UI_flash_switcher_' + CSMode.NAMES[leftMode]],
                'rightLabel': g_config.i18n['UI_flash_switcher_' + CSMode.NAMES[rightMode]],
                'leftEvent': 'installStyle',
                'rightEvent': 'installStyles',
                'isLeft': not isShift,
                'rightEnabled': rightEnabled or True}

    def __setBottomPanelBillData(self, *_):
        purchaseItems = self.__ctx.getPurchaseItems()
        cartInfo = getTotalPurchaseInfo(purchaseItems)
        totalPriceVO = getItemPricesVO(cartInfo.totalPrice)
        if cartInfo.totalPrice != ITEM_PRICE_EMPTY:
            label = _ms(VEHICLE_CUSTOMIZATION.COMMIT_BUY)
        else:
            label = _ms(VEHICLE_CUSTOMIZATION.COMMIT_APPLY)
        tooltip = VEHICLE_CUSTOMIZATION.CUSTOMIZATION_BUYDISABLED_BODY
        fromStorageCount = 0
        toByeCount = 0
        for item in purchaseItems:
            if item.isFromInventory:
                fromStorageCount += 1
            if not item.isDismantling:
                toByeCount += 1

        if fromStorageCount > 0 or toByeCount > 0:
            self.__showBill()
        else:
            self.__hideBill()
            tooltip = VEHICLE_CUSTOMIZATION.CUSTOMIZATION_NOTSELECTEDITEMS
        fromStorageCount = text_styles.stats('({})'.format(fromStorageCount))
        toByeCount = text_styles.stats('({})'.format(toByeCount))
        outfitsModified = self.__ctx.isOutfitsModified()
        self.as_setBottomPanelPriceStateS({
            'buyBtnEnabled': outfitsModified,
            'buyBtnLabel': label,
            'buyBtnTooltip': tooltip,
            'isHistoric': self.__ctx.currentOutfit.isHistorical(),
            'billVO': {'title': text_styles.highlightText(_ms(VEHICLE_CUSTOMIZATION.BUYPOPOVER_RESULT)),
                       'priceLbl': text_styles.main('{} {}'.format(_ms(VEHICLE_CUSTOMIZATION.BUYPOPOVER_PRICE), toByeCount)),
                       'fromStorageLbl': text_styles.main(
                           '{} {}'.format(_ms(VEHICLE_CUSTOMIZATION.BUYPOPOVER_FROMSTORAGE), fromStorageCount)),
                       'isEnoughStatuses': getMoneyVO(Money(outfitsModified, outfitsModified, outfitsModified)),
                       'pricePanel': totalPriceVO[0]}})

    def __getItemTabsData(self):
        data = []
        pluses = []
        for tabIdx in self.__ctx.visibleTabs:
            itemTypeID = tabToItem(tabIdx, self.__ctx.isBuy)
            typeName = GUI_ITEM_TYPE_NAMES[itemTypeID]
            showPlus = not self.__ctx.checkSlotsFilling(itemTypeID, self.__ctx.currentSeason)
            tabData = {'id': tabIdx,
                       'icon': RES_ICONS.getCustomizationIcon(typeName) if itemTypeID != GUI_ITEM_TYPE.STYLE else
                       RES_ICONS.MAPS_ICONS_CUSTOMIZATION_PROPERTY_SHEET_IDLE_ICON_FULL_TANK_HOVER}
            if self.__ctx.isBuy:
                tabData.update({'label': _ms(ITEM_TYPES.customizationPlural(typeName)),
                                'tooltip': makeTooltip(
                                    ITEM_TYPES.customizationPlural(typeName),
                                    TOOLTIPS.customizationItemTab(typeName) if itemTypeID != GUI_ITEM_TYPE.STYLE else
                                    g_config.i18n['UI_flashCol_tabs_0_tooltip'])})
            else:
                tabData.update({'label': g_config.i18n['UI_flash_tabs_%s_label' % tabIdx],
                                'tooltip': makeTooltip(g_config.i18n['UI_flashCol_tabs_%s_text' % tabIdx],
                                                       g_config.i18n['UI_flashCol_tabs_%s_tooltip' % tabIdx])})
            data.append(tabData)
            pluses.append(showPlus)
        return data, pluses

    def __onModeChanged(self, mode):
        self.__setFooterInitData()
        updateTabGroups(self._carouselDP)
        self.__refreshCarousel(force=True)
        self.__updateTabs(self.__ctx.currentTab)
        self._carouselDP.selectItem(self.__ctx.modifiedStyle if self.__ctx.currentTab == self.__ctx.tabsData.STYLE else None)
        self.__setBottomPanelBillData()
