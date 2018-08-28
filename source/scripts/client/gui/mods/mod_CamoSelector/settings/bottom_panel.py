from gui.Scaleform.daapi.settings.views import VIEW_ALIAS
from gui.Scaleform.daapi.view.lobby.customization.customization_bottom_panel import CustomizationBottomPanel as CBP
from gui.Scaleform.daapi.view.lobby.customization.shared import getTotalPurchaseInfo
from gui.Scaleform.daapi.view.lobby.store.browser.ingameshop_helpers import isIngameShopEnabled
from gui.Scaleform.framework import g_entitiesFactories
from gui.Scaleform.locale.ITEM_TYPES import ITEM_TYPES
from gui.Scaleform.locale.RES_ICONS import RES_ICONS
from gui.Scaleform.locale.TOOLTIPS import TOOLTIPS
from gui.Scaleform.locale.VEHICLE_CUSTOMIZATION import VEHICLE_CUSTOMIZATION
from gui.shared.formatters import getItemPricesVO, text_styles
from gui.shared.gui_items import GUI_ITEM_TYPE_NAMES, GUI_ITEM_TYPE
from gui.shared.gui_items.gui_item_economics import ITEM_PRICE_EMPTY, ItemPrice
from gui.shared.money import Currency
from gui.shared.utils.functions import makeTooltip
from helpers.i18n import makeString as _ms
from .shared import CSMode, tabToItem
from .. import g_config


class CustomizationBottomPanel(CBP):
    def __setFooterInitData(self):
        self.as_setBottomPanelInitDataS({
            'tabsAvailableRegions': self.__ctx.tabsData.AVAILABLE_REGIONS,
            'defaultStyleLabel': VEHICLE_CUSTOMIZATION.DEFAULTSTYLE_LABEL,
            'carouselInitData': self.__getCarouselInitData(),
            'switcherInitData': self.__getSwitcherInitData(self.__ctx.mode),
            'filtersVO': {'popoverAlias': VIEW_ALIAS.CUSTOMIZATION_FILTER_POPOVER,
                          'mainBtn': {'value': RES_ICONS.MAPS_ICONS_BUTTONS_FILTER,
                                      'tooltip': VEHICLE_CUSTOMIZATION.CAROUSEL_FILTER_MAINBTN},
                          'hotFilters': [{'value': RES_ICONS.MAPS_ICONS_CUSTOMIZATION_STORAGE_ICON,
                                          'tooltip': VEHICLE_CUSTOMIZATION.CAROUSEL_FILTER_STORAGEBTN,
                                          'selected': self._carouselDP.getOwnedFilter()},
                                         {'value': RES_ICONS.MAPS_ICONS_BUTTONS_EQUIPPED_ICON,
                                          'tooltip': VEHICLE_CUSTOMIZATION.CAROUSEL_FILTER_EQUIPPEDBTN,
                                          'selected': self._carouselDP.getAppliedFilter()}]}})

    @staticmethod
    def __getSwitcherInitData(mode):
        return {'leftLabel': g_config.i18n['UI_flash_switcher_' + CSMode.NAMES[mode]],
                'rightLabel': g_config.i18n['UI_flash_switcher_' + CSMode.NAMES[(mode + 1) % len(CSMode.NAMES)]],
                'leftEvent': 'installStyle',
                'rightEvent': 'installStyles',
                'isLeft': True}

    def __setBottomPanelBillData(self, *_):
        purchaseItems = self.__ctx.getPurchaseItems()
        cartInfo = getTotalPurchaseInfo(purchaseItems)
        totalPriceVO = getItemPricesVO(cartInfo.totalPrice)
        if cartInfo.totalPrice != ITEM_PRICE_EMPTY:
            label = _ms(VEHICLE_CUSTOMIZATION.COMMIT_BUY)
        else:
            label = _ms(VEHICLE_CUSTOMIZATION.COMMIT_APPLY)
        money = self.itemsCache.items.stats.money
        exchangeRate = self.itemsCache.items.shop.exchangeRate
        moneyExchanged = money.exchange(Currency.GOLD, Currency.CREDITS, exchangeRate, default=0)
        minPriceItemAvailable = cartInfo.minPriceItem.isDefined() and (
                    cartInfo.minPriceItem <= money or cartInfo.minPriceItem <= moneyExchanged)
        canBuy = minPriceItemAvailable or not cartInfo.minPriceItem.isDefined()
        isApplyEnabled = self.__ctx.isOutfitsModified() and (canBuy or isIngameShopEnabled())
        shortage = money.getShortage(cartInfo.totalPrice.price)
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
        self.as_setBottomPanelPriceStateS({
            'buyBtnEnabled': isApplyEnabled,
            'buyBtnLabel': label,
            'buyBtnTooltip': tooltip,
            'isHistoric': self.__ctx.currentOutfit.isHistorical(),
            'billVO': {'title': text_styles.highlightText(_ms(VEHICLE_CUSTOMIZATION.BUYPOPOVER_RESULT)),
                       'priceLbl': text_styles.main('{} {}'.format(_ms(VEHICLE_CUSTOMIZATION.BUYPOPOVER_PRICE), toByeCount)),
                       'fromStorageLbl': text_styles.main(
                           '{} {}'.format(_ms(VEHICLE_CUSTOMIZATION.BUYPOPOVER_FROMSTORAGE), fromStorageCount)),
                       'enoughMoney': getItemPricesVO(ItemPrice(shortage, shortage))[0],
                       'pricePanel': totalPriceVO[0]}})

    def __getItemTabsData(self):
        data = []
        pluses = []
        for tabIdx in self.__ctx.visibleTabs:
            itemTypeID = tabToItem(tabIdx, self.__ctx.mode)
            typeName = GUI_ITEM_TYPE_NAMES[itemTypeID]
            showPlus = not self.__ctx.checkSlotsFilling(itemTypeID, self.__ctx.currentSeason)
            data.append({'label': _ms(ITEM_TYPES.customizationPlural(typeName)),
                         'tooltip': makeTooltip(ITEM_TYPES.customizationPlural(typeName), TOOLTIPS.customizationItemTab(
                             typeName) if itemTypeID != GUI_ITEM_TYPE.STYLE else ''),
                         'id': tabIdx} if self.__ctx.mode == CSMode.BUY else
                        {'label': g_config.i18n['UI_flash_tabs_%s_label' % tabIdx],
                         'tooltip': makeTooltip(g_config.i18n['UI_flashCol_tabs_%s_text' % tabIdx],
                                                g_config.i18n['UI_flashCol_tabs_%s_tooltip' % tabIdx]),
                         'id': tabIdx})
            pluses.append(showPlus)
        return data, pluses

    def __onModeChanged(self, mode):
        self.__setFooterInitData()
        self.__updateTabs(self.__ctx.currentTab)
        self._carouselDP.selectItem(self.__ctx.modifiedStyle if self.__ctx.currentTab == self.__ctx.tabsData.STYLE else None)
        self.__setBottomPanelBillData()

