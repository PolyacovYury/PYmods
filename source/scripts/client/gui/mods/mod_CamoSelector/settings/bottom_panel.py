from CurrentVehicle import g_currentVehicle
from OpenModsCore import BigWorld_callback, overrideMethod
from frameworks.wulf import WindowLayer as WL
from gui.Scaleform.daapi.view.lobby.customization.customization_bottom_panel import CustomizationBottomPanel as CBP
from gui.Scaleform.daapi.view.lobby.customization.customization_item_vo import __getIcon as getIcon
from gui.Scaleform.daapi.view.lobby.customization.shared import (
    CustomizationTabs, checkSlotsFilling, getEditableStylesExtraNotificationCounter, getItemTypesAvailableForVehicle,
)
from gui.Scaleform.framework import ScopeTemplates as ST, ViewSettings, g_entitiesFactories
from gui.Scaleform.framework.entities.View import View
from gui.Scaleform.framework.managers.loaders import SFViewLoadParams
from gui.Scaleform.locale.RES_ICONS import RES_ICONS
from gui.Scaleform.locale.TOOLTIPS import TOOLTIPS
from gui.Scaleform.locale.VEHICLE_CUSTOMIZATION import VEHICLE_CUSTOMIZATION
from gui.customization.constants import CustomizationModes
from gui.impl.backport import text
from gui.impl.gen import R
from gui.shared.formatters import getItemPricesVO
from gui.shared.gui_items import GUI_ITEM_TYPE, GUI_ITEM_TYPE_NAMES
from gui.shared.gui_items.gui_item_economics import ITEM_PRICE_EMPTY
from gui.shared.utils.functions import makeTooltip
from shared_utils import first
from .shared import CSComparisonKey, getCriteria
from .. import g_config
from ..constants import VIEW_ALIAS


class CustomizationBottomPanel(CBP):
    criteria = None

    def _populate(self):
        CBP._populate(self)
        self.app.loadView(SFViewLoadParams('PY_CS_carousel_UI'))

    def switchMode(self, index):
        if index != 2:
            modeId = self.__ctx.purchaseModeId
            if modeId == CustomizationModes.EDITABLE_STYLE:
                modeId = CustomizationModes.STYLED
            modeId = (CustomizationModes.CAMO_SELECTOR, modeId)[index]
            tabId = self.__ctx.getMode(modeId).tabId
            self.__changeMode(modeId)
            self.showGroupFromTab(tabId)

    def showGroupFromTab(self, tabIndex):
        if tabIndex == CustomizationTabs.STYLES and self.__ctx.isPurchase and self.__ctx.modeId != CustomizationModes.STYLED:
            self.__changeMode(CustomizationModes.STYLED)
        elif tabIndex != CustomizationTabs.STYLES and self.__ctx.modeId == CustomizationModes.STYLED:
            self.__changeMode(CustomizationModes.CUSTOM)
        CBP.showGroupFromTab(self, tabIndex)

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
        season = self.__ctx.season
        isPurchase = self.__ctx.isPurchase
        _filter = self.__ctx.mode.style.isItemInstallable if self.__ctx.modeId == CustomizationModes.EDITABLE_STYLE else None
        styles = self._carouselDP.getItemsData(season, CustomizationModes.STYLED, CustomizationTabs.STYLES)
        self.as_setNotificationCountersS({'tabsCounters': [
            0 if not isPurchase else (
                    vehicle.getC11nItemsNoveltyCounter(proxy, CustomizationTabs.ITEM_TYPES[tabId], season, _filter)
                    + (0 if tabId != CustomizationTabs.STYLES else getEditableStylesExtraNotificationCounter(styles)))
            for tabId in self.getVisibleTabs()], 'switchersCounter': (
            0 if isPurchase else vehicle.getC11nItemsNoveltyCounter(
                proxy, getItemTypesAvailableForVehicle()) + getEditableStylesExtraNotificationCounter(styles))})

    def __getSwitcherInitData(self):
        # noinspection PyUnresolvedReferences
        data = CBP._CustomizationBottomPanel__getSwitcherInitData(self)
        return dict(data, **{
            'leftLabel': g_config.i18n['flash_switcher_install'],
            'rightLabel': g_config.i18n['flash_switcher_buy'],
            'selectedIndex': int(self.__ctx.isPurchase) + int(self.__ctx.isPurchase and data['isEditable']),
            'popoverAlias': data['popoverAlias'] if self.__ctx.isPurchase else VIEW_ALIAS.CAMO_SELECTOR_KIT_POPOVER,
            'rightEnabled': bool(self._carouselDP.getVisibleTabsForPurchase())
        })

    def __setBottomPanelBillData(self, *a, **k):
        # noinspection PyUnresolvedReferences
        CBP._CustomizationBottomPanel__setBottomPanelBillData(self, *a, **k)
        BigWorld_callback(0, self.__showBill if self.__ctx.isOutfitsModified() else self.__hideBill)
        BigWorld_callback(0, self.as_setItemsPopoverBtnEnabledS, not self.__ctx.mode.isOutfitsEmpty())

    def as_setBottomPanelPriceStateS(self, data):
        self.criteria = getCriteria(self.__ctx)
        data['buyBtnEnabled'] &= all(
            self.criteria(self.service.getItemByCD(itemCD))
            for itemCD in self.__ctx.getMode(CustomizationModes.CAMO_SELECTOR).getAppliedItems(False))
        if not data['buyBtnEnabled'] and self.__ctx.isOutfitsModified():
            data['buyBtnTooltip'] = g_config.i18n['flashCol_freeVersion_tooltip']
        return super(CustomizationBottomPanel, self).as_setBottomPanelPriceStateS(data)

    def _carouseItemWrapper(self, itemCD):
        VO = CBP._carouseItemWrapper(self, itemCD)
        if '4278190335,4278255360,4294901760,4278190080' in VO['icon']:
            VO['icon'] = '../../' + VO['icon'].split('"', 2)[1]
            VO['imageCached'] = False
        if self.__ctx.isPurchase:
            VO['isDarked'] = VO['isAlreadyUsed']
            return VO
        if not self.criteria:
            self.criteria = getCriteria(self.__ctx)
        item = self.service.getItemByCD(itemCD)
        VO['locked'] = VO['isDarked'] = False
        VO['isAlreadyUsed'] = not self.criteria(item)
        VO['showEditBtnHint'] = True
        VO['showEditableHint'] = VO['editBtnEnabled'] = False
        VO['rentalInfoText'] = VO['editableIcon'] = VO['tooltip'] = ''
        VO['buyPrice'] = getItemPricesVO(ITEM_PRICE_EMPTY)[0]
        if item.isProgressive:
            VO['progressionLevel'] = progressionLevel = 0
            VO['icon'] = getIcon(item, progressionLevel)
        VO['noveltyCounter'] = 0
        VO.pop('quantity', None)
        return VO

    def __getItemTabsData(self):
        tabsData = []
        pluses = []
        outfit = self.__ctx.mode.currentOutfit
        for tabId in self.getVisibleTabs():
            slotType = CustomizationTabs.SLOT_TYPES[tabId]
            slotsCount, filledSlotsCount = checkSlotsFilling(outfit, slotType)
            pluses.append(filledSlotsCount < slotsCount)
            itemTypeName = GUI_ITEM_TYPE_NAMES[slotType]
            pluralText = text(
                R.strings.item_types.customization.plural.dyn(itemTypeName)()) if slotType != GUI_ITEM_TYPE.INSIGNIA else ''
            tabsData.append(
                {
                    'label': text(R.strings.achievements.marksOnGun0()), 'id': tabId,
                    'icon': RES_ICONS.MAPS_ICONS_CUSTOMIZATION_PROPERTY_SHEET_IDLE_ICON_EDIT,
                    'tooltip': makeTooltip(text(R.strings.achievements.marksOnGun0()))
                } if slotType == GUI_ITEM_TYPE.INSIGNIA else {
                    'label': pluralText, 'id': tabId,
                    'icon': RES_ICONS.MAPS_ICONS_CUSTOMIZATION_PROPERTY_SHEET_IDLE_ICON_FULL_TANK,
                    'tooltip': makeTooltip(pluralText, VEHICLE_CUSTOMIZATION.DEFAULTSTYLE_LABEL)
                } if slotType == GUI_ITEM_TYPE.STYLE else {
                    'label': pluralText, 'id': tabId,
                    'icon': RES_ICONS.getCustomizationIcon(itemTypeName),
                    'tooltip': makeTooltip(pluralText, TOOLTIPS.customizationItemTab(itemTypeName))
                })
        return tabsData, pluses

    def __scrollToNewItem(self):
        if self.__ctx.isPurchase:
            itemTypes = CustomizationTabs.ITEM_TYPES[self.__ctx.mode.tabId]
            newItems = sorted(g_currentVehicle.item.getNewC11nItems(self.itemsCache.items), key=CSComparisonKey(True, None))
            for item in newItems:
                if item.itemTypeID in itemTypes and item.season & self.__ctx.season:
                    return self.__scrollToItem(item.intCD, immediately=True)
        items = self.carouselItems
        for intCD in self.__ctx.mode.getAppliedItems(isOriginal=False):
            if intCD in items:
                return self.__scrollToItem(intCD, immediately=True)
        intCD = first(items)
        if intCD is not None:
            self.__scrollToItem(intCD, immediately=True)

    def __onEditableStylesHintsShown(self):
        if not self.__ctx.isPurchase:
            # noinspection PyArgumentEqualDefault
            return self.__onEditableStylesHintsHidden(record=False)
        # noinspection PyUnresolvedReferences
        return CBP._CustomizationBottomPanel__onEditableStylesHintsShown(self)

    def __updateStageSwitcherVisibility(self):
        newVisibility = False
        if self.__ctx.mode.tabId == CustomizationTabs.STYLES:
            styleItem = self.__ctx.mode.currentOutfit.style
            if styleItem:
                newVisibility = styleItem.isProgression
        if self.__stageSwitcherVisibility != newVisibility:
            self.__stageSwitcherVisibility = newVisibility
            self.as_setStageSwitcherVisibilityS(self.__stageSwitcherVisibility)


class CamoSelector_carousel(View):
    def _populate(self):
        View._populate(self)
        BigWorld_callback(0, self.destroy)
        BigWorld_callback(0, self.app.containerManager.getContainer(WL.SUB_VIEW).getView()._MainView__bottomPanel.resetFilter)

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
