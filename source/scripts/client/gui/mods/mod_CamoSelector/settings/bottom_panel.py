import BigWorld
from CurrentVehicle import g_currentVehicle
from PYmodsCore import overrideMethod
from frameworks.wulf import WindowLayer as WL
from gui import makeHtmlString
from gui.Scaleform.daapi.view.lobby.customization.customization_bottom_panel import CustomizationBottomPanel as CBP
from gui.Scaleform.daapi.view.lobby.customization.customization_item_vo import __getIcon as getIcon
from gui.Scaleform.daapi.view.lobby.customization.shared import (
    CustomizationTabs, checkSlotsFilling, getItemTypesAvailableForVehicle, getEditableStylesExtraNotificationCounter)
from gui.Scaleform.framework import g_entitiesFactories, ViewSettings, ScopeTemplates as ST
from gui.Scaleform.framework.entities.View import View
from gui.Scaleform.framework.managers.loaders import SFViewLoadParams
from gui.Scaleform.locale.ITEM_TYPES import ITEM_TYPES
from gui.Scaleform.locale.RES_ICONS import RES_ICONS
from gui.Scaleform.locale.TOOLTIPS import TOOLTIPS
from gui.Scaleform.locale.VEHICLE_CUSTOMIZATION import VEHICLE_CUSTOMIZATION
from gui.customization.constants import CustomizationModes, CustomizationModeSource
from gui.impl import backport
from gui.impl.gen import R
from gui.shared.formatters import getItemPricesVO
from gui.shared.gui_items import GUI_ITEM_TYPE_NAMES, GUI_ITEM_TYPE
from gui.shared.gui_items.gui_item_economics import ITEM_PRICE_EMPTY
from gui.shared.utils.functions import makeTooltip
from helpers.i18n import makeString as _ms
from shared_utils import first
from .shared import CSMode, CSComparisonKey
from .. import g_config


class CustomizationBottomPanel(CBP):
    def _populate(self):
        CBP._populate(self)
        self.app.loadView(SFViewLoadParams('PY_CS_carousel_UI'))
        self.__ctx.events.onPurchaseModeChanged += self.__onPurchaseModeChanged

    def _dispose(self):
        self.__ctx.events.onPurchaseModeChanged -= self.__onPurchaseModeChanged
        CBP._dispose(self)

    def __onPurchaseModeChanged(self):
        self._carouselDP.invalidateItems()
        self.__onModeChanged(self.__ctx.modeId, self.__ctx.modeId)

    def returnToStyledMode(self):
        self.__changeMode(CSMode.PURCHASE)

    def switchMode(self, index):
        if index != 2:
            self.__changeMode(CSMode.FROM_BUTTONS[index])

    def __changeMode(self, modeId):
        self.__ctx.changePurchaseMode(modeId, source=CustomizationModeSource.BOTTOM_PANEL)
        self.__updatePopoverBtnIcon()

    def showGroupFromTab(self, tabIndex):
        if tabIndex == CustomizationTabs.STYLES and self.__ctx.modeId != CustomizationModes.STYLED:
            self.__ctx.changeMode(CustomizationModes.STYLED, tabIndex, source=CustomizationModeSource.BOTTOM_PANEL)
        elif tabIndex != CustomizationTabs.STYLES and self.__ctx.modeId == CustomizationModes.STYLED:
            self.__ctx.changeMode(CustomizationModes.CUSTOM, tabIndex, source=CustomizationModeSource.BOTTOM_PANEL)
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
        isPurchase = self.__ctx.isPurchase
        _filter = self.__ctx.mode.style.isItemInstallable if self.__ctx.modeId == CustomizationModes.EDITABLE_STYLE else None
        for tabId in visibleTabs:
            if not isPurchase:
                tabsCounters.append(0)
                continue
            itemTypes = CustomizationTabs.ITEM_TYPES[tabId]
            tabsCounters.append(vehicle.getC11nItemsNoveltyCounter(proxy, itemTypes, season, _filter))
        if self.__ctx.isPurchase:
            switchersCounter = 0
        else:
            switchersCounter = vehicle.getC11nItemsNoveltyCounter(proxy, getItemTypesAvailableForVehicle())
            styles = self._carouselDP.getItemsData(season, CustomizationModes.STYLED, CustomizationTabs.STYLES)
            switchersCounter += getEditableStylesExtraNotificationCounter(styles)
        self.as_setNotificationCountersS({'tabsCounters': tabsCounters, 'switchersCounter': switchersCounter})

    def __getSwitcherInitData(self):
        # noinspection PyUnresolvedReferences
        data = CBP._CustomizationBottomPanel__getSwitcherInitData(self)
        return dict(data, **{
            'leftLabel': g_config.i18n['flash_switcher_' + CSMode.NAMES[CSMode.INSTALL]],
            'rightLabel': g_config.i18n['flash_switcher_' + CSMode.NAMES[CSMode.PURCHASE]],
            'selectedIndex': CSMode.BUTTONS[self.__ctx.purchaseMode] + int(self.__ctx.isPurchase and data['isEditable']),
            'rightEnabled': True
        })

    def __setBottomPanelBillData(self, *_):
        # noinspection PyUnresolvedReferences
        CBP._CustomizationBottomPanel__setBottomPanelBillData(self, *_)
        outfitsModified = self.__ctx.isOutfitsModified()
        BigWorld.callback(0, self.__showBill if outfitsModified else self.__hideBill)

    def _carouseItemWrapper(self, itemCD):
        VO = CBP._carouseItemWrapper(self, itemCD)
        if self.__ctx.isPurchase:
            return VO
        item = self.service.getItemByCD(itemCD)
        VO['locked'] = False
        VO['isAlreadyUsed'] = False  # actually marks item.isUsedUp
        VO['isDarked'] = False
        VO['buyPrice'] = getItemPricesVO(ITEM_PRICE_EMPTY)[0]
        VO['rentalInfoText'] = ''
        VO['showEditBtnHint'] = False
        VO['showEditableHint'] = False
        VO['editableIcon'] = ''
        VO['editBtnEnabled'] = False
        VO['tooltip'] = ''
        if item.isProgressive:
            VO['progressionLevel'] = progressionLevel = 0
            VO['icon'] = getIcon(item, progressionLevel)
        VO['noveltyCounter'] = 0
        if '4278190335,4278255360,4294901760,4278190080' in VO['icon']:
            VO['icon'] = '../../' + VO['icon'].split('"', 2)[1]
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

    def __scrollToNewItem(self):
        if self.__ctx.isPurchase:
            itemTypes = CustomizationTabs.ITEM_TYPES[self.__ctx.mode.tabId]
            newItems = sorted(g_currentVehicle.item.getNewC11nItems(g_currentVehicle.itemsCache.items), key=CSComparisonKey)
            for item in newItems:
                if item.itemTypeID in itemTypes and item.season & self.__ctx.season:
                    self.__scrollToItem(item.intCD)
                    return
        intCD = first(self.carouselItems)
        if intCD is not None:
            self.__scrollToItem(intCD, immediately=True)

    def __onEditableStylesHintsShown(self):
        if not self.__ctx.isPurchase:
            return self.__onEditableStylesHintsHidden(record=False)
        # noinspection PyUnresolvedReferences
        return CBP._CustomizationBottomPanel__onEditableStylesHintsShown(self)

    def __processBillDataPurchaseItems(self, purchaseItems):
        with self.__ctx.overridePurchaseMode():
            # noinspection PyUnresolvedReferences
            return CBP._CustomizationBottomPanel__processBillDataPurchaseItems(self, purchaseItems)


class CamoSelector_carousel(View):
    def _populate(self):
        View._populate(self)
        BigWorld.callback(0, self.destroy)
        BigWorld.callback(0, self.app.containerManager.getContainer(WL.SUB_VIEW).getView()._MainView__bottomPanel.resetFilter)

    @staticmethod
    def py_log(*args):
        for arg in args:
            print arg
            # print dir(arg)
            if hasattr(arg, 'toDict'):
                print arg.toDict()


# noinspection PyArgumentList
g_entitiesFactories.addSettings(ViewSettings(
    'PY_CS_carousel_UI', CamoSelector_carousel, 'CamoSelector_carousel.swf', WL.WINDOW, None, ST.GLOBAL_SCOPE))


@overrideMethod(CBP, '__new__')
def new(base, cls, *a, **kw):
    if not g_config.data['enabled']:
        return base(cls, *a, **kw)
    return base(CustomizationBottomPanel, *a, **kw)
