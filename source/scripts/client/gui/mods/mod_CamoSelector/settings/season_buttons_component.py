from PYmodsCore import overrideMethod
from gui.Scaleform.daapi.view.lobby.customization.main_view import MainView
from gui.Scaleform.daapi.view.lobby.customization.property_sheet_season_buttons_component import \
    PropertySheetSeasonButtonsComponent
from gui.Scaleform.daapi.view.lobby.customization.shared import SEASON_IDX_TO_TYPE, SEASON_TYPE_TO_IDX
from gui.shared.formatters import getItemPricesVO
from gui.shared.gui_items.gui_item_economics import ITEM_PRICE_EMPTY
from .shared import C11nMode


@overrideMethod(PropertySheetSeasonButtonsComponent, '_PropertySheetSeasonButtonsComponent__determineRendererState')
def __determineRendererState(base, self, renderer, seasonIDX, currentItem, activeItem, showGlow, *a, **kw):
    if isinstance(self._c11nView, MainView) or self._c11nView.getMode() == C11nMode.INSTALL:
        return base(self, renderer, seasonIDX, currentItem, activeItem, showGlow, *a, **kw)
    self._activeSeason = self._c11nView.getCurrentSeason()
    seasonType = SEASON_IDX_TO_TYPE[seasonIDX]
    activeItem = self._c11nView.getCurrentOutfit().getContainer(self._areaId).slotFor(self._slotId).getItem(self._regionId)
    currentItem = None if not self._c11nView.getSettingSeason() & seasonType else activeItem
    renderer.itemIntCD = currentItem.intCD if currentItem is not None else -1
    state = self._PropertySheetSeasonButtonsComponent__getState(
        activeItem, currentItem, bool(self._c11nView.getCurrentTab()) or
        self._PropertySheetSeasonButtonsComponent__isApplicableToActiveSeason(activeItem, seasonIDX), False)
    action = self._PropertySheetSeasonButtonsComponent__getAction(state)
    renderer.action = action[0]
    renderer.actionText = action[1]
    renderer.seasonIcon = self._PropertySheetSeasonButtonsComponent__getSeasonIcon(seasonType, state)
    renderer.applyItemIntCD = activeItem.intCD if activeItem is not None else -1
    smallSlotVO = {'itemIcon': currentItem.icon if currentItem is not None else '',
                   'itemIsWide': currentItem.isWide() if currentItem is not None else False}
    renderer.smallSlotVO = smallSlotVO
    renderer.wouldAddItem = False
    buyPrice = ITEM_PRICE_EMPTY
    renderer.buyPrice = getItemPricesVO(buyPrice)[0]
    renderer.currencyType = buyPrice.getCurrency() if buyPrice is not ITEM_PRICE_EMPTY else ''
    renderer.showBorder = renderer.seasonIDX == SEASON_TYPE_TO_IDX[self._activeSeason]
    renderer.showPurchaseGlow = (showGlow and renderer.requiresPurchase and currentItem == activeItem and currentItem is
                                 not None)
