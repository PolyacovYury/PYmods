from PYmodsCore import overrideMethod
from gui.Scaleform.daapi.view.lobby.customization.main_view import MainView
from gui.Scaleform.daapi.view.lobby.customization.property_sheet_season_buttons_component import \
    PropertySheetSeasonButtonsComponent, SeasonButtonStates, SeasonIconFactory
from gui.Scaleform.daapi.view.lobby.customization.shared import SEASON_IDX_TO_TYPE, SEASON_TYPE_TO_IDX
from gui.Scaleform.genConsts.SEASON_BUTTON_ACTIONS import SEASON_BUTTON_ACTIONS
from gui.Scaleform.locale.RES_ICONS import RES_ICONS
from gui.Scaleform.locale.VEHICLE_CUSTOMIZATION import VEHICLE_CUSTOMIZATION
from gui.shared.formatters import getItemPricesVO
from gui.shared.gui_items.gui_item_economics import ITEM_PRICE_EMPTY


@overrideMethod(PropertySheetSeasonButtonsComponent, '_PropertySheetSeasonButtonsComponent__determineRendererState')
def __determineRendererState(base, self, renderer, seasonIDX, currentItem, activeItem, showGlow, *a, **kw):
    if isinstance(self._c11nView, MainView):
        return base(self, renderer, seasonIDX, currentItem, activeItem, showGlow, *a, **kw)
    self._activeSeason = self._c11nView.getCurrentSeason()
    wouldAddItem = False
    if currentItem is None and activeItem:
        wouldAddItem = self._c11nView.getItemInventoryCount(activeItem) == 0
    renderer.itemIntCD = currentItem.intCD if currentItem is not None else -1
    state = self.__getState(activeItem, currentItem, self.__isApplicableToActiveSeason(activeItem, seasonIDX),
                            wouldAddItem)
    action = self.__getAction(state)
    renderer.action = action[0]
    renderer.actionText = action[1]
    renderer.seasonIcon = self.__getSeasonIcon(SEASON_IDX_TO_TYPE[seasonIDX], state)
    renderer.applyItemIntCD = activeItem.intCD if activeItem is not None else -1
    smallSlotVO = {'itemIcon': currentItem.icon if currentItem is not None else '',
                   'itemIsWide': currentItem.isWide() if currentItem is not None else False}
    renderer.smallSlotVO = smallSlotVO
    renderer.wouldAddItem = wouldAddItem and action[0] is not SEASON_BUTTON_ACTIONS.LOCKED
    # itemForPurchase = currentItem if currentItem is not None else activeItem
    buyPrice = ITEM_PRICE_EMPTY
    renderer.buyPrice = getItemPricesVO(buyPrice)[0]
    renderer.currencyType = buyPrice.getCurrency() if buyPrice is not ITEM_PRICE_EMPTY else ''
    renderer.showBorder = (currentItem is not None and currentItem == activeItem and renderer.seasonIDX ==
                           SEASON_TYPE_TO_IDX[self._activeSeason])
    renderer.showPurchaseGlow = (showGlow and renderer.requiresPurchase and currentItem == activeItem and currentItem is
                                 not None)


@overrideMethod(PropertySheetSeasonButtonsComponent, '_PropertySheetSeasonButtonsComponent__getState')
def __getState(base, self, activeCustomizationItem, currentCustomizationItem, applicableToCurrentSeason, wouldAddItem, *a,
               **k):
    if isinstance(self._c11nView, MainView):
        return base(self, activeCustomizationItem, currentCustomizationItem, applicableToCurrentSeason, wouldAddItem, *a, **k)
    if activeCustomizationItem is None:
        state = SeasonButtonStates.EMPTY if currentCustomizationItem is None else SeasonButtonStates.FILLED
    elif currentCustomizationItem is None:
        if wouldAddItem:
            state = SeasonButtonStates.EMPTY_ADD if applicableToCurrentSeason else SeasonButtonStates.LOCKED_EMPTY
        else:
            state = SeasonButtonStates.EMPTY_APPLY if applicableToCurrentSeason else SeasonButtonStates.LOCKED_EMPTY
    elif activeCustomizationItem == currentCustomizationItem:
        state = SeasonButtonStates.GLOWING
    elif applicableToCurrentSeason:
        state = SeasonButtonStates.FILLED
    else:
        state = SeasonButtonStates.LOCKED_FILLED
    if state == SeasonButtonStates.EMPTY_ADD and activeCustomizationItem and activeCustomizationItem.isHidden:
        state = SeasonButtonStates.EMPTY_APPLY
    return state


@overrideMethod(PropertySheetSeasonButtonsComponent, '_PropertySheetSeasonButtonsComponent__getAction')
def __getAction(base, self, state, *a, **k):
    if isinstance(self._c11nView, MainView):
        base(self, state, *a, **k)
    action = SEASON_BUTTON_ACTIONS.NOTHING
    actionText = VEHICLE_CUSTOMIZATION.CUSTOMIZATION_PROPSHEET_POPOVER_EMPTY
    if state & SeasonButtonStates.EMPTY:
        action = SEASON_BUTTON_ACTIONS.NOTHING
        actionText = VEHICLE_CUSTOMIZATION.CUSTOMIZATION_PROPSHEET_POPOVER_EMPTY
    elif state & SeasonButtonStates.EMPTY_APPLY:
        action = SEASON_BUTTON_ACTIONS.APPLY
        actionText = VEHICLE_CUSTOMIZATION.CUSTOMIZATION_PROPSHEET_POPOVER_APPLYITEM
    elif state & SeasonButtonStates.EMPTY_ADD:
        action = SEASON_BUTTON_ACTIONS.APPLY
        actionText = VEHICLE_CUSTOMIZATION.CUSTOMIZATION_PROPSHEET_POPOVER_ADDITEM
    elif state & (SeasonButtonStates.FILLED | SeasonButtonStates.GLOWING | SeasonButtonStates.LOCKED_FILLED):
        action = SEASON_BUTTON_ACTIONS.REMOVE
        actionText = VEHICLE_CUSTOMIZATION.CUSTOMIZATION_PROPSHEET_POPOVER_REMOVE
    elif state & SeasonButtonStates.LOCKED_EMPTY:
        action = SEASON_BUTTON_ACTIONS.LOCKED
        actionText = VEHICLE_CUSTOMIZATION.CUSTOMIZATION_PROPSHEET_POPOVER_LOCKED
    return action, actionText


@overrideMethod(PropertySheetSeasonButtonsComponent, '_PropertySheetSeasonButtonsComponent__getSeasonIcon')
def __getSeasonIcon(base, self, seasonType, state, *a, **kw):
    if isinstance(self._c11nView, MainView):
        return base(self, seasonType, state, *a, **kw)
    if state & SeasonButtonStates.LOCKED_EMPTY:
        icon = RES_ICONS.MAPS_ICONS_CUSTOMIZATION_SEASON_LOCK_EMPTY
    elif state & SeasonButtonStates.LOCKED_FILLED:
        icon = RES_ICONS.MAPS_ICONS_CUSTOMIZATION_SEASON_LOCK_FILLED
    else:
        icon = SeasonIconFactory.getIcon(seasonType, state)
    return icon
