from gui.Scaleform.daapi.view.lobby.customization.property_sheet_season_buttons_component import \
    PropertySheetButtonRenderer, \
    PropertySheetSeasonButtonRenderers, SeasonButtonStates, SeasonIconFactory
from gui.Scaleform.daapi.view.lobby.customization.shared import SEASONS_ORDER, SEASON_IDX_TO_TYPE, SEASON_TYPE_TO_IDX
from gui.Scaleform.daapi.view.meta.PropertySheetSeasonButtonsComponentMeta import PropertySheetSeasonButtonsComponentMeta
from gui.Scaleform.framework import ViewTypes
from gui.Scaleform.genConsts.SEASON_BUTTON_ACTIONS import SEASON_BUTTON_ACTIONS
from gui.Scaleform.locale.RES_ICONS import RES_ICONS
from gui.Scaleform.locale.VEHICLE_CUSTOMIZATION import VEHICLE_CUSTOMIZATION
from gui.shared.formatters import getItemPricesVO
from gui.shared.gui_items.gui_item_economics import ITEM_PRICE_EMPTY
from helpers import dependency
from items.components.c11n_constants import SeasonType
from skeletons.gui.customization import ICustomizationService


# noinspection PyMethodMayBeStatic
class PropertySheetSeasonButtonsComponent(PropertySheetSeasonButtonsComponentMeta):
    service = dependency.descriptor(ICustomizationService)

    def __init__(self):
        super(PropertySheetSeasonButtonsComponent, self).__init__()
        self._activeSeason = SeasonType.SUMMER
        self._areaId = -1
        self._slotId = -1
        self._regionId = -1
        self._renderers = None
        self._c11nView = None
        return

    def show(self):
        self.__registerHandlers()

    def refresh(self):
        self.__refreshRenderers()

    def hide(self):
        self.__unregisterHandlers()
        if self._renderers is not None:
            self._renderers.clear()
        self._renderers = None
        self._areaId = -1
        self._slotId = -1
        self._regionId = -1
        return

    def refreshSeasonButtons(self):
        if self.__isComponentValid():
            self.__refreshRenderers()
            renderers = []
            for seasonIDX, rend in self._renderers.iteritems():
                renderers.append(rend.asdict())

            self.as_setRendererDataS(PropertySheetSeasonButtonRenderers(renderers)._asdict())

    def _populate(self):
        super(PropertySheetSeasonButtonsComponent, self)._populate()
        self._c11nView = self.app.containerManager.getContainer(ViewTypes.LOBBY_SUB).getView()

    def _dispose(self):
        if self._renderers is not None:
            self._renderers.clear()
        self._renderers = None
        self.__unregisterHandlers()
        super(PropertySheetSeasonButtonsComponent, self)._dispose()
        return

    def __registerHandlers(self):
        self.service.onPropertySheetShow += self.__onVehicleOutfitChanged

    def __unregisterHandlers(self):
        self.service.onPropertySheetShow -= self.__onVehicleOutfitChanged

    def __createRenderers(self):
        if self._renderers is None:
            self._renderers = {}
            outfit = self._c11nView.getModifiedOutfit(self._activeSeason)
            activeItem = outfit.getContainer(self._areaId).slotFor(self._slotId).getItem(self._regionId)
            for idx, season in enumerate(SEASONS_ORDER):
                outfit = self._c11nView.getModifiedOutfit(season)
                item = outfit.getContainer(self._areaId).slotFor(self._slotId).getItem(self._regionId)
                newRenderer = PropertySheetButtonRenderer()
                newRenderer.seasonIDX = idx
                self.__determineRendererState(newRenderer, idx, item, activeItem, False)
                self._renderers[idx] = newRenderer

        return

    def __determineRendererState(self, renderer, seasonIDX, currentItem, activeItem, showGlow):
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
        return

    def __getState(self, activeCustomizationItem, currentCustomizationItem, applicableToCurrentSeason, wouldAddItem):
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

    def __getAction(self, state):
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

    def __getSeasonIcon(self, seasonType, state):
        if state & SeasonButtonStates.LOCKED_EMPTY:
            icon = RES_ICONS.MAPS_ICONS_CUSTOMIZATION_SEASON_LOCK_EMPTY
        elif state & SeasonButtonStates.LOCKED_FILLED:
            icon = RES_ICONS.MAPS_ICONS_CUSTOMIZATION_SEASON_LOCK_FILLED
        else:
            icon = SeasonIconFactory.getIcon(seasonType, state)
        return icon

    def __isApplicableToActiveSeason(self, activeSeasonSlot, seasonIDX):
        return False if activeSeasonSlot is None else activeSeasonSlot.season & SEASON_IDX_TO_TYPE[seasonIDX]

    def __onVehicleOutfitChanged(self, areaId, slotId, regionId):
        if self._renderers is None:
            self._areaId = areaId
            self._slotId = slotId
            self._regionId = regionId
            self.__createRenderers()
        return

    def __refreshRenderers(self):
        outfit = self._c11nView.getModifiedOutfit(self._activeSeason)
        activeItem = outfit.getContainer(self._areaId).slotFor(self._slotId).getItem(self._regionId)
        for idx, renderer in self._renderers.iteritems():
            outfit = self._c11nView.getModifiedOutfit(SEASON_IDX_TO_TYPE[idx])
            item = outfit.getContainer(self._areaId).slotFor(self._slotId).getItem(self._regionId)
            showGlow = renderer.itemIntCD == -1 or item and item.intCD is not renderer.itemIntCD
            self.__determineRendererState(renderer, renderer.seasonIDX, item, activeItem, showGlow)

    def __isComponentValid(self):
        return self._renderers is not None
