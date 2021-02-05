import BigWorld
from CurrentVehicle import g_currentVehicle
from PYmodsCore import overrideMethod
from gui.Scaleform.daapi.view.lobby.customization.customization_bottom_panel import CustomizationBottomPanel as CBP
from gui.Scaleform.daapi.view.lobby.customization.shared import (
    CustomizationTabs, checkSlotsFilling, getItemTypesAvailableForVehicle, getEditableStylesExtraNotificationCounter)
from gui.Scaleform.locale.ITEM_TYPES import ITEM_TYPES
from gui.Scaleform.locale.RES_ICONS import RES_ICONS
from gui.Scaleform.locale.TOOLTIPS import TOOLTIPS
from gui.Scaleform.locale.VEHICLE_CUSTOMIZATION import VEHICLE_CUSTOMIZATION
from gui.customization.constants import CustomizationModes, CustomizationModeSource
from gui.shared.formatters import getItemPricesVO
from gui.shared.gui_items import GUI_ITEM_TYPE_NAMES, GUI_ITEM_TYPE
from gui.shared.gui_items.gui_item_economics import ITEM_PRICE_EMPTY
from gui.shared.utils.functions import makeTooltip
from helpers.i18n import makeString as _ms
from shared_utils import first
from .carousel import CSComparisonKey
from .shared import CSMode, getItemSeason
from .. import g_config


class CustomizationBottomPanel(CBP):
    def _populate(self):
        super(CustomizationBottomPanel, self)._populate()
        self.__ctx.events.onActualModeChanged += self.__onActualModeChanged

    def _dispose(self):
        self.__ctx.events.onActualModeChanged -= self.__onActualModeChanged
        super(CustomizationBottomPanel, self)._dispose()

    def __onActualModeChanged(self):
        self._carouselDP.invalidateItems()
        self.__onModeChanged(self.__ctx.modeId, self.__ctx.modeId)

    def __changeMode(self, modeId):
        self.__ctx.changeActualMode(CSMode.FROM_BUTTONS[modeId], source=CustomizationModeSource.BOTTOM_PANEL)
        self.__updatePopoverBtnIcon()

    def showGroupFromTab(self, tabIndex):
        if tabIndex == CustomizationTabs.STYLES and self.__ctx.modeId != CustomizationModes.STYLED:
            self.__ctx.changeMode(CustomizationModes.STYLED, tabIndex, source=CustomizationModeSource.BOTTOM_PANEL)
        else:
            self.__ctx.mode.changeTab(tabIndex)
        self.__updatePopoverBtnIcon()

    def __updateTabs(self):
        tabsData, pluses = self.__getItemTabsData()
        if self.__ctx.modeId == CustomizationModes.STYLED:
            selectedTab = CustomizationTabs.STYLES
        else:
            selectedTab = self.__ctx.mode.tabId
        self.as_setBottomPanelTabsDataS({'tabsDP': tabsData, 'selectedTab': selectedTab})
        self.as_setBottomPanelTabsPlusesS(pluses)

    def __setNotificationCounters(self):
        vehicle = g_currentVehicle.item
        proxy = g_currentVehicle.itemsCache.items
        tabsCounters = []
        visibleTabs = self.getVisibleTabs()
        season = self.__ctx.season
        isBuy = self.__ctx.isBuy
        itemFilter = self.__ctx.mode.style.isItemInstallable if self.__ctx.modeId == CustomizationModes.EDITABLE_STYLE else None
        for tabId in visibleTabs:
            if not isBuy:
                tabsCounters.append(0)
                continue
            itemTypes = CustomizationTabs.ITEM_TYPES[tabId]
            tabsCounters.append(vehicle.getC11nItemsNoveltyCounter(proxy, itemTypes, season, itemFilter))
        if self.__ctx.isBuy:
            switchersCounter = 0
        else:
            switchersCounter = vehicle.getC11nItemsNoveltyCounter(proxy, getItemTypesAvailableForVehicle())
            styles = self._carouselDP.getItemsData(season, CustomizationModes.STYLED, CustomizationTabs.STYLES)
            switchersCounter += getEditableStylesExtraNotificationCounter(styles)
        self.as_setNotificationCountersS({'tabsCounters': tabsCounters, 'switchersCounter': switchersCounter})

    def __getSwitcherInitData(self):
        # noinspection PyUnresolvedReferences
        data = super(CustomizationBottomPanel, self)._CustomizationBottomPanel__getSwitcherInitData()
        return dict(data, **{
            'leftLabel': g_config.i18n['flash_switcher_' + CSMode.NAMES[CSMode.INSTALL]],
            'rightLabel': g_config.i18n['flash_switcher_' + CSMode.NAMES[CSMode.BUY]],
            'selectedIndex': CSMode.BUTTONS[self.__ctx.actualMode],
            'rightEnabled': True
        })

    def __setBottomPanelBillData(self, *_):
        # noinspection PyUnresolvedReferences
        super(CustomizationBottomPanel, self)._CustomizationBottomPanel__setBottomPanelBillData(*_)
        outfitsModified = self.__ctx.isOutfitsModified()
        BigWorld.callback(0, self.__showBill if outfitsModified else self.__hideBill)

    def _carouseItemWrapper(self, itemCD):
        VO = super(CustomizationBottomPanel, self)._carouseItemWrapper(itemCD)
        if not self.__ctx.isBuy:
            VO['locked'] = False
            VO['isDarked'] = False
            VO['buyPrice'] = getItemPricesVO(ITEM_PRICE_EMPTY)[0]
            VO['rentalInfoText'] = ''
            VO.pop('quantity', None)
        return VO

    def __getItemTabsData(self):
        tabsData = []
        pluses = []
        visibleTabs = self.getVisibleTabs()
        outfit = self.__ctx.mode.currentOutfit
        for tabId in visibleTabs:
            slotType = CustomizationTabs.SLOT_TYPES[tabId]
            itemTypeName = GUI_ITEM_TYPE_NAMES[slotType]
            slotsCount, filledSlotsCount = checkSlotsFilling(outfit, slotType)
            showPlus = filledSlotsCount < slotsCount
            tabsData.append({
                'label': _ms(ITEM_TYPES.customizationPlural(itemTypeName)),
                'icon': RES_ICONS.getCustomizationIcon(itemTypeName)
                if slotType != GUI_ITEM_TYPE.STYLE else
                RES_ICONS.MAPS_ICONS_CUSTOMIZATION_PROPERTY_SHEET_IDLE_ICON_FULL_TANK,
                'tooltip': makeTooltip(
                    ITEM_TYPES.customizationPlural(itemTypeName),
                    TOOLTIPS.customizationItemTab(itemTypeName)
                    if slotType != GUI_ITEM_TYPE.STYLE else
                    VEHICLE_CUSTOMIZATION.DEFAULTSTYLE_LABEL),
                'id': tabId})
            pluses.append(showPlus)
        return tabsData, pluses

    def __onModeChanged(self, *_):
        # noinspection PyUnresolvedReferences
        super(CustomizationBottomPanel, self)._CustomizationBottomPanel__onModeChanged(*_)
        self.__scrollToNewItem()
        self.__updatePopoverBtnIcon()

    def __scrollToNewItem(self):
        currentTypes = CustomizationTabs.ITEM_TYPES[self.__ctx.mode.tabId]
        newItems = sorted(g_currentVehicle.item.getNewC11nItems(g_currentVehicle.itemsCache.items), key=CSComparisonKey)
        for item in newItems:
            if item.itemTypeID in currentTypes and (
                    item.season if self.__ctx.isBuy else getItemSeason(item)) & self.__ctx.currentSeason:
                self.__scrollToItem(item.intCD)
                break
        else:
            intCD = first(self.carouselItems)
            if intCD is not None:
                self.__scrollToItem(intCD, immediately=True)


@overrideMethod(CBP, '__new__')
def new(base, cls, *a, **kw):
    if not g_config.data['enabled']:
        return base(cls, *a, **kw)
    return base(CustomizationBottomPanel, *a, **kw)
