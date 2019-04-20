from CurrentVehicle import g_currentVehicle
from PYmodsCore import overrideMethod
from gui.Scaleform.daapi.view.lobby.customization.customization_bottom_panel import CustomizationBottomPanel as CBP
from gui.Scaleform.daapi.view.lobby.customization.shared import getTotalPurchaseInfo, TABS_ITEM_TYPE_MAPPING, \
    TABS_SLOT_TYPE_MAPPING, C11nMode
from gui.Scaleform.locale.ITEM_TYPES import ITEM_TYPES
from gui.Scaleform.locale.RES_ICONS import RES_ICONS
from gui.Scaleform.locale.TOOLTIPS import TOOLTIPS
from gui.Scaleform.locale.VEHICLE_CUSTOMIZATION import VEHICLE_CUSTOMIZATION as CUSTOMIZATION
from gui.customization.shared import C11nId
from gui.shared.formatters import getItemPricesVO, text_styles, getMoneyVO
from gui.shared.gui_items import GUI_ITEM_TYPE_NAMES, GUI_ITEM_TYPE
from gui.shared.gui_items.gui_item_economics import ITEM_PRICE_EMPTY
from gui.shared.money import Money
from gui.shared.utils.functions import makeTooltip
from gui.shared.utils.graphics import isRendererPipelineDeferred
from helpers.i18n import makeString as _ms
from .item_vo import buildCustomizationItemDataVO
from .shared import CSMode, getItemSeason
from .. import g_config


class CustomizationBottomPanel(CBP):
    def _populate(self):
        super(CustomizationBottomPanel, self)._populate()
        self.__ctx.onActualModeChanged += self.__onActualModeChanged

    def _dispose(self):
        self.__ctx.onActualModeChanged -= self.__onActualModeChanged
        super(CustomizationBottomPanel, self)._dispose()

    def __onActualModeChanged(self):
        self._carouselDP.updateTabGroups()
        self.__updatePopoverBtnIcon()

    def __onSlotSelected(self, areaId, slotType, regionIdx):
        item = self.__ctx.getItemFromRegion(C11nId(areaId, slotType, regionIdx))
        itemIdx = -1
        if item is not None and item.intCD in self._carouselDP.collection:
            itemIdx = self._carouselDP.collection.index(item.intCD)
        self._carouselDP.selectItemIdx(itemIdx)

    def __setNotificationCounters(self):
        item = g_currentVehicle.item
        proxy = g_currentVehicle.itemsCache.items
        isBuy = self.__ctx.isBuy
        self.as_setNotificationCountersS({
            'tabsCounters': [0 if not isBuy else item.getC11nItemsNoveltyCounter(
                proxy, TABS_ITEM_TYPE_MAPPING[tabIdx], self.__ctx.currentSeason) for tabIdx in self.__ctx.visibleTabs],
            'switchersCounter': 0 if isBuy else item.getC11nItemsNoveltyCounter(proxy, GUI_ITEM_TYPE.CUSTOMIZATIONS)})

    def __updateSetSwitcherData(self):
        self.as_setSwitchersDataS(self.__getSwitcherInitData(self.__ctx.actualMode))

    # noinspection PyMethodOverriding
    @staticmethod
    def __getSwitcherInitData(mode):
        return {'leftLabel': g_config.i18n['flash_switcher_' + CSMode.NAMES[mode]],
                'rightLabel': g_config.i18n['flash_switcher_' + CSMode.NAMES[(mode + 1) % len(CSMode.NAMES)]],
                'leftEvent': 'installStyle',
                'rightEvent': 'installStyle',
                'isLeft': True,
                'rightEnabled': True}

    def __setBottomPanelBillData(self, *_):
        purchaseItems = self.__ctx.getPurchaseItems()
        cartInfo = getTotalPurchaseInfo(purchaseItems)
        totalPriceVO = getItemPricesVO(cartInfo.totalPrice)
        label = _ms(CUSTOMIZATION.COMMIT_BUY if cartInfo.totalPrice != ITEM_PRICE_EMPTY else CUSTOMIZATION.COMMIT_APPLY)
        tooltip = CUSTOMIZATION.CUSTOMIZATION_BUYDISABLED_BODY
        fromStorageCount = 0
        toBuyCount = 0
        for item in purchaseItems:
            if item.isFromInventory:
                fromStorageCount += 1
            if not item.isDismantling:
                toBuyCount += 1

        outfitsModified = self.__ctx.isOutfitsModified()
        if outfitsModified:
            self.__showBill()
        else:
            self.__hideBill()
            tooltip = CUSTOMIZATION.CUSTOMIZATION_NOTSELECTEDITEMS
        fromStorageCount = text_styles.stats('({})'.format(fromStorageCount))
        toBuyCount = text_styles.stats('({})'.format(toBuyCount))
        self.as_setBottomPanelPriceStateS({
            'buyBtnEnabled': outfitsModified,
            'buyBtnLabel': label,
            'buyBtnTooltip': tooltip,
            'isHistoric': self.__ctx.currentOutfit.isHistorical(),
            'billVO': {'title': text_styles.highlightText(_ms(CUSTOMIZATION.BUYPOPOVER_RESULT)),
                       'priceLbl': text_styles.main('{} {}'.format(_ms(CUSTOMIZATION.BUYPOPOVER_PRICE), toBuyCount)),
                       'fromStorageLbl': text_styles.main(
                           '{} {}'.format(_ms(CUSTOMIZATION.BUYPOPOVER_FROMSTORAGE), fromStorageCount)),
                       'isEnoughStatuses': getMoneyVO(Money(True, True, True)),
                       'pricePanel': totalPriceVO[0]}})
        self.as_setItemsPopoverBtnEnabledS(not self.__ctx.currentOutfit.isEmpty())

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
                             CUSTOMIZATION.DEFAULTSTYLE_LABEL),
                         'id': tabIdx})
            pluses.append(showPlus)
        return data, pluses

    def __onModeChanged(self, mode):
        self._carouselDP.selectItem(self.__ctx.modifiedStyle if mode == C11nMode.STYLE else None)
        self.__setBottomPanelBillData()
        self.__setFooterInitData()
        self.__scrollToNewItem()
        self.__updatePopoverBtnIcon()

    def __scrollToNewItem(self):
        currentTypes = TABS_ITEM_TYPE_MAPPING[self.__ctx.currentTab]
        newItems = sorted(g_currentVehicle.item.getNewC11nItems(self.itemsCache.items), key=self._carouselDP.CSComparisonKey)
        for item in newItems:
            if item.itemTypeID in currentTypes and (
                    item.season if self.__ctx.isBuy else getItemSeason(item)) & self.__ctx.currentSeason:
                self.as_scrollToSlotS(item.intCD)


@overrideMethod(CBP, '__new__')
def new(base, cls, *a, **kw):
    if not g_config.data['enabled']:
        return base(cls, *a, **kw)
    return base(CustomizationBottomPanel, *a, **kw)