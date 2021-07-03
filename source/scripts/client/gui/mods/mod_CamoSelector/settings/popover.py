from CurrentVehicle import g_currentVehicle
from frameworks.wulf import WindowLayer
from gui import makeHtmlString
from gui.Scaleform.daapi.view.lobby.customization.popovers import C11nPopoverItemData, orderKey
from gui.Scaleform.daapi.view.lobby.customization.shared import (
    ITEM_TYPE_TO_SLOT_TYPE, fitOutfit, getCurrentVehicleAvailableRegionsMap, isStyleEditedForCurrentVehicle,
)
from gui.Scaleform.daapi.view.meta.CustomizationEditedKitPopoverMeta import CustomizationEditedKitPopoverMeta
from gui.Scaleform.framework import GroupedViewSettings, ScopeTemplates, g_entitiesFactories
from gui.customization.shared import C11nId, SEASONS_ORDER, SEASON_TYPE_TO_NAME
from gui.impl import backport
from gui.impl.gen import R
from gui.shared import EVENT_BUS_SCOPE, g_eventBus
from gui.shared.events import ViewEventType
from gui.shared.formatters import getItemPricesVO, icons, text_styles
from gui.shared.gui_items import GUI_ITEM_TYPE
from gui.shared.personality import ServicesLocator as SL
from helpers import dependency
from items.components.c11n_constants import SeasonType
from skeletons.gui.customization import ICustomizationService
from ..constants import VIEW_ALIAS


class EditableStylePopover(CustomizationEditedKitPopoverMeta):
    __service = dependency.descriptor(ICustomizationService)

    def __init__(self, ctx=None):
        super(EditableStylePopover, self).__init__(ctx)
        self.__ctx = None
        self.__styles = None

    def onWindowClose(self):
        self.destroy()

    def remove(self, intCD, slotIds, season):
        self.__ctx.mode.removeFromSlots(slotIds, season)

    def setToDefault(self):
        self.__ctx.mode.clearStyle()

    def removeAll(self):
        if self.__style is not None:
            self.__ctx.mode.removeStyle(self.__style.intCD)

    def _populate(self):
        super(EditableStylePopover, self)._populate()
        self.__ctx = self.__service.getCtx()
        self.__ctx.events.onCacheResync += self.__update
        self.__ctx.events.onSeasonChanged += self.__update
        self.__ctx.events.onItemInstalled += self.__update
        self.__ctx.events.onItemsRemoved += self.__update
        self.__ctx.events.onChangesCanceled += self.__update
        self.__update()

    def _dispose(self):
        if self.__ctx.events is not None:
            self.__ctx.events.onChangesCanceled -= self.__update
            self.__ctx.events.onItemsRemoved -= self.__update
            self.__ctx.events.onItemInstalled -= self.__update
            self.__ctx.events.onSeasonChanged -= self.__update
            self.__ctx.events.onCacheResync -= self.__update
        self.__styles = None
        self.__ctx = None
        super(EditableStylePopover, self)._dispose()

    def __setHeader(self):
        self.as_setHeaderS(text_styles.highTitle(backport.text(
            R.strings.vehicle_customization.customization.kitPopover.title.items())))
        self.as_setHelpMessageS(
            icons.makeImageTag(backport.image(R.images.gui.maps.icons.customization.edited_small()))
            + text_styles.main(backport.text(R.strings.vehicle_customization.popover.editableStyle.editedItems())))

    def __setClearMessage(self):
        self.as_showClearMessageS('' if not self.__ctx.mode.isOutfitsEmpty() else text_styles.main(backport.text(
            R.strings.vehicle_customization.customization.itemsPopover.clear.message())))

    def __update(self, *_):
        self.__styles = self.__ctx.mode.getModifiedStyles()
        self.as_setItemsS({'items': self.__buildList()})
        self.__setHeader()
        self.__setClearMessage()
        self.__updateClearStyleButton()

    def __updateClearStyleButton(self):
        self.as_setDefaultButtonEnabledS(
            self.__style is not None and isStyleEditedForCurrentVehicle(self.__ctx.mode.getModifiedOutfits(), self.__style))

    def __buildList(self):
        data = []
        if self.__style is None:
            return data
        vDesc = g_currentVehicle.item.descriptor
        purchaseItems = self.__ctx.mode.getActualPurchaseItems()
        seasonPurchaseItems = {
            season: [pItem for pItem in purchaseItems if pItem.group == season] for season in SeasonType.COMMON_SEASONS}
        availableRegionsMap = getCurrentVehicleAvailableRegionsMap()
        for season in SEASONS_ORDER:
            data.append(self.__getSeasonGroupVO(season))
            data.extend(self.__getSeasonItemsData(season, seasonPurchaseItems[season], availableRegionsMap, vDesc))
        return data

    @staticmethod
    def __getSeasonGroupVO(season):
        return {'isTitle': True, 'titleLabel': (makeHtmlString(
            'html_templates:lobby/customization/StylePopoverSeasonName', SEASON_TYPE_TO_NAME[season],
            ctx={'align': 'CENTER'}))}

    def __getSeasonItemsData(self, season, purchaseItems, availableRegionsMap, vehicleDescriptor):
        itemData = {}
        for pItem in purchaseItems:
            item = pItem.item
            if item.intCD not in itemData:
                itemData[item.intCD] = C11nPopoverItemData(item=item, season=season, isRemovable=True, isFromInventory=True)
            slotId = C11nId(pItem.areaID, pItem.slotType, pItem.regionIdx)
            itemData[item.intCD].slotsIds.append(slotId._asdict())

        baseOutfit = self.__style.getOutfit(season, vehicleCD=vehicleDescriptor.makeCompactDescr())
        fitOutfit(baseOutfit, availableRegionsMap)
        nationalEmblemItem = self.__service.getItemByID(GUI_ITEM_TYPE.EMBLEM, vehicleDescriptor.type.defaultPlayerEmblemID)
        showStyle = True
        nationalEmblemDetected = False
        otherDetected = False
        for intCD, _, regionIdx, container, _ in baseOutfit.itemsFull():
            item = self.__service.getItemByCD(intCD)
            if item.isHiddenInUI():
                continue
            else:
                showStyle = False
            if not nationalEmblemDetected and intCD == nationalEmblemItem.intCD:
                nationalEmblemDetected = True
            elif not otherDetected and intCD != nationalEmblemItem.intCD:
                otherDetected = True
            key = (intCD, True)
            if key not in itemData:
                itemData[key] = C11nPopoverItemData(
                    item=item, season=season, isBase=True, isRemoved=True, isFromInventory=True)
            if itemData[key].isRemoved:
                areaId = container.getAreaID()
                slotType = ITEM_TYPE_TO_SLOT_TYPE[item.itemTypeID]
                slotId = C11nId(areaId, slotType, regionIdx)
                itemData[key].slotsIds.append(slotId._asdict())

        if nationalEmblemDetected and not otherDetected:
            showStyle = True
            key = (nationalEmblemItem.intCD, True)
            itemData.pop(key)
        if showStyle:
            key = (self.__style.intCD, True)
            itemData[key] = C11nPopoverItemData(item=self.__style, season=season, isBase=True, isFromInventory=True)
        data = [self.__makeItemDataVO(itemData) for itemData in sorted(itemData.values(), key=orderKey)]
        return data

    def __makeItemDataVO(self, itemData):
        item = itemData.item
        icon = item.icon
        name = text_styles.main(item.userName)
        if itemData.isRemoved or not itemData.isRemovable:
            countLabel = ''
            price = None
        elif itemData.isFromInventory:
            countLabel = text_styles.main('{} '.format(len(itemData.slotsIds)))
            price = None
        else:
            countLabel = text_styles.main('{} x '.format(len(itemData.slotsIds)))
            price = getItemPricesVO(item.buyPrices.itemPrice)[0]
        disabledLabel = backport.text(R.strings.vehicle_customization.popover.style.removed())
        disabledLabel = text_styles.bonusPreviewText(disabledLabel)
        isApplied = itemData.isBase
        progressionLevel = 0 if item.itemTypeID != GUI_ITEM_TYPE.STYLE else self.__ctx.mode.currentOutfit.progressionLevel
        return {
            'id': item.intCD, 'icon': icon, 'userName': name, 'numItems': countLabel, 'isHistoric': item.isHistorical(),
            'price': price, 'isApplied': isApplied, 'isWide': item.isWide(), 'itemsList': itemData.slotsIds,
            'isDim': item.isDim(), 'isEdited': not itemData.isBase, 'isDisabled': itemData.isRemoved,
            'disabledLabel': disabledLabel, 'isRemovable': itemData.isRemovable, 'seasonType': itemData.season,
            'progressionLevel': progressionLevel}


popoverAlias = VIEW_ALIAS.CAMO_SELECTOR_KIT_POPOVER
g_entitiesFactories.addSettings(GroupedViewSettings(
    popoverAlias, EditableStylePopover, 'customizationEditedKitPopover.swf', WindowLayer.WINDOW, popoverAlias, popoverAlias,
    ScopeTemplates.DEFAULT_SCOPE))
g_eventBus.addListener(ViewEventType.LOAD_VIEW, lambda event: SL.appLoader.getApp().loadView(
    event.loadParams, event.ctx) if event.alias == popoverAlias else None, EVENT_BUS_SCOPE.LOBBY)
