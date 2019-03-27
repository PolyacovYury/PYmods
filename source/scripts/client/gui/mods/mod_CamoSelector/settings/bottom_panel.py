from CurrentVehicle import g_currentVehicle
from PYmodsCore import overrideMethod
from gui.Scaleform.daapi.settings.views import VIEW_ALIAS
from gui.Scaleform.daapi.view.lobby.customization.customization_bottom_panel import CustomizationBottomPanel as CBP
from gui.Scaleform.daapi.view.lobby.customization.customization_carousel import comparisonKey
from gui.Scaleform.daapi.view.lobby.customization.shared import getTotalPurchaseInfo, TABS_ITEM_TYPE_MAPPING, C11nTabs, \
    TABS_SLOT_TYPE_MAPPING
from gui.Scaleform.locale.ITEM_TYPES import ITEM_TYPES
from gui.Scaleform.locale.RES_ICONS import RES_ICONS
from gui.Scaleform.locale.TOOLTIPS import TOOLTIPS
from gui.Scaleform.locale.VEHICLE_CUSTOMIZATION import VEHICLE_CUSTOMIZATION
from gui.customization.shared import C11nId
from gui.shared.formatters import getItemPricesVO, text_styles, getMoneyVO
from gui.shared.gui_items import GUI_ITEM_TYPE_NAMES, GUI_ITEM_TYPE
from gui.shared.gui_items.gui_item_economics import ITEM_PRICE_EMPTY
from gui.shared.money import Money
from gui.shared.utils.functions import makeTooltip
from gui.shared.utils.graphics import isRendererPipelineDeferred
from helpers.i18n import makeString as _ms
from .carousel import CSComparisonKey
from .item_vo import buildCustomizationItemDataVO
from .shared import CSMode, getItemSeason
from .. import g_config


class CustomizationBottomPanel(CBP):
    def __onSlotSelected(self, areaId, slotType, regionIdx):
        item = self.__ctx.getItemFromRegion(C11nId(areaId, slotType, regionIdx))
        itemIdx = -1
        if item is not None and item.intCD in self._carouselDP.collection:
            itemIdx = self._carouselDP.collection.index(item.intCD)
        self._carouselDP.selectItemIdx(itemIdx)

    def __setNotificationCounters(self):
        vehicle = g_currentVehicle.item
        proxy = g_currentVehicle.itemsCache.items
        tabsCounters = []
        for tabIdx in self.__ctx.visibleTabs:
            tabsCounters.append(vehicle.getC11nItemsNoveltyCounter(
                proxy, itemTypes=TABS_ITEM_TYPE_MAPPING[tabIdx], season=self.__ctx.currentSeason))
        self.as_setNotificationCountersS({
            'tabsCounters': tabsCounters,
            'switchersCounter': vehicle.getC11nItemsNoveltyCounter(proxy, itemTypes=GUI_ITEM_TYPE.CUSTOMIZATIONS)})

    def __setFooterInitData(self):
        self.as_setBottomPanelInitDataS({
            'tabsAvailableRegions': C11nTabs.AVAILABLE_REGIONS,
            'defaultStyleLabel': g_config.i18n['flash_switcher_tabsInvisible'],
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

    def __updateSetSwitcherData(self):
        self.as_setSwitchersDataS(self.__getSwitcherInitData(int(not self.__ctx.isBuy)))

    # noinspection PyMethodOverriding
    @staticmethod
    def __getSwitcherInitData(mode):
        return {'leftLabel': g_config.i18n['flash_switcher_' + CSMode.NAMES[mode]],
                'rightLabel': g_config.i18n['flash_switcher_' + CSMode.NAMES[(mode + 1) % len(CSMode.NAMES)]],
                'leftEvent': 'installStyle',
                'rightEvent': 'installStyle',
                'isLeft': mode == CSMode.BUY,
                'rightEnabled': True}

    def __setBottomPanelBillData(self, *_):  # TODO: process installed items correctly
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
                       'isEnoughStatuses': getMoneyVO(Money(True, True, True)),
                       'pricePanel': totalPriceVO[0]}})
        self.as_setItemsPopoverBtnEnabledS(self.__ctx.currentOutfit.isEmpty())

    def _carouseItemWrapper(self, itemCD):
        isBuy = self.__ctx.isBuy
        item = self.service.getItemByCD(itemCD)
        itemInventoryCount = self.__ctx.getItemInventoryCount(item)
        purchaseLimit = self.__ctx.getPurchaseLimit(item)
        showUnsupportedAlert = item.itemTypeID == GUI_ITEM_TYPE.MODIFICATION and not isRendererPipelineDeferred()
        isCurrentlyApplied = itemCD in self._carouselDP.getCurrentlyApplied()
        noPrice = isBuy and item.buyCount <= 0
        isDarked = isBuy and purchaseLimit == 0 and itemInventoryCount == 0
        isAlreadyUsed = isDarked and not isCurrentlyApplied
        autoRentEnabled = self.__ctx.autoRentEnabled()
        return buildCustomizationItemDataVO(
            isBuy, item, itemInventoryCount, showUnsupportedAlert=showUnsupportedAlert, isCurrentlyApplied=isCurrentlyApplied,
            isAlreadyUsed=isAlreadyUsed, forceLocked=isAlreadyUsed, isDarked=isDarked, noPrice=noPrice,
            autoRentEnabled=autoRentEnabled, vehicle=g_currentVehicle.item)

    def __getItemTabsData(self):
        data = []
        pluses = []
        for tabIdx in self.__ctx.visibleTabs:
            itemTypeID = TABS_SLOT_TYPE_MAPPING[tabIdx]
            typeName = GUI_ITEM_TYPE_NAMES[itemTypeID]
            slotsCount, filledSlotsCount = self.__ctx.checkSlotsFilling(itemTypeID, self.__ctx.currentSeason)
            showPlus = filledSlotsCount < slotsCount
            data.append({'label': _ms(ITEM_TYPES.customizationPlural(typeName)),
                         'icon': RES_ICONS.getCustomizationIcon(typeName) if itemTypeID != GUI_ITEM_TYPE.STYLE else
                         RES_ICONS.MAPS_ICONS_CUSTOMIZATION_PROPERTY_SHEET_IDLE_ICON_FULL_TANK,
                         'tooltip': makeTooltip(
                             ITEM_TYPES.customizationPlural(typeName),
                             TOOLTIPS.customizationItemTab(typeName) if itemTypeID != GUI_ITEM_TYPE.STYLE else
                             g_config.i18n['flashCol_tabs_0_tooltip']),
                         'id': tabIdx})
            pluses.append(showPlus)
        return data, pluses

    def __scrollToNewItem(self):
        currentTypes = TABS_ITEM_TYPE_MAPPING[self.__ctx.currentTab]
        newItems = sorted(g_currentVehicle.item.getNewC11nItems(g_currentVehicle.itemsCache.items),
                          key=comparisonKey if self.__ctx.isBuy else CSComparisonKey)
        for item in newItems:
            if item.itemTypeID in currentTypes and (
                    item.season if self.__ctx.isBuy else getItemSeason(item)) & self.__ctx.currentSeason:
                self.as_scrollToSlotS(item.intCD)


@overrideMethod(CBP, '__new__')
def new(base, cls, *a, **kw):
    if not g_config.data['enabled']:
        return base(cls, *a, **kw)
    return base(CustomizationBottomPanel, *a, **kw)
