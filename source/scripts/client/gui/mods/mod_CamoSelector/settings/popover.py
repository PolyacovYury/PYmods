from functools import partial

import BigWorld
from CurrentVehicle import g_currentVehicle
from frameworks.wulf import WindowLayer
from gui import makeHtmlString
from gui.Scaleform.daapi.view.lobby.customization.popovers import C11nPopoverItemData
from gui.Scaleform.daapi.view.lobby.customization.shared import (
    ITEM_TYPE_TO_SLOT_TYPE, fitOutfit, getCurrentVehicleAvailableRegionsMap,
)
from gui.Scaleform.daapi.view.meta.CustomizationEditedKitPopoverMeta import CustomizationEditedKitPopoverMeta
from gui.Scaleform.framework import GroupedViewSettings, ScopeTemplates, g_entitiesFactories
from gui.customization.shared import AdditionalPurchaseGroups, C11nId, SEASONS_ORDER, SEASON_TYPE_TO_NAME
from gui.impl import backport
from gui.impl.gen import R
from gui.shared import EVENT_BUS_SCOPE, g_eventBus
from gui.shared.events import ViewEventType
from gui.shared.formatters import icons, text_styles
from gui.shared.gui_items import GUI_ITEM_TYPE
from gui.shared.personality import ServicesLocator as SL
from helpers import dependency
from skeletons.gui.customization import ICustomizationService
from .shared import addDefaultInsignia, fixIconPath, getDefaultItemCDs, getInsigniaUserName
from ..constants import TYPES_ORDER, VIEW_ALIAS


class EditableStylePopover(CustomizationEditedKitPopoverMeta):
    __service = dependency.descriptor(ICustomizationService)

    def __init__(self, ctx=None):
        super(EditableStylePopover, self).__init__(ctx)
        self.__ctx = None

    def onWindowClose(self):
        self.destroy()

    def remove(self, intCD, slotIds, season):
        self.__ctx.mode.removeFromSlots([C11nId(**slotId.toDict()) for slotId in slotIds], season)

    def setToDefault(self):
        self.__ctx.mode.clearStyle()

    def removeAll(self):
        style = self.__ctx.mode.modifiedStyle
        if style:
            self.__ctx.mode.removeStyle(style.intCD)

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
        self.__ctx = None
        super(EditableStylePopover, self)._dispose()

    def as_setClearButtonEnabledS(self, value):
        if self._isDAAPIInited():
            self.flashObject.clearBtn.enabled = value

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
        self.as_setItemsS({'items': self.__buildList()})
        self.__setHeader()
        self.__setClearMessage()
        self.__updateClearStyleButton()

    def __updateClearStyleButton(self):
        mode = self.__ctx.mode
        style = mode.modifiedStyle
        BigWorld.callback(0, partial(self.as_setClearButtonEnabledS, style is not None))  # must run after flash invalidate()
        if not style:
            return self.as_setDefaultButtonEnabledS(False)
        if mode.modifiedStyleSeason != mode.season:
            return self.as_setDefaultButtonEnabledS(True)
        level = mode.getStyleProgressionLevel()
        vDesc = g_currentVehicle.item.descriptor
        vehicleCD = vDesc.makeCompactDescr()
        baseOutfit = style.getOutfit(mode.season, vehicleCD)
        if level != -1:
            addOutfit = style.getAdditionalOutfit(level, mode.season, vehicleCD)
            if addOutfit is not None:
                baseOutfit = baseOutfit.patch(addOutfit)
        fitOutfit(baseOutfit, getCurrentVehicleAvailableRegionsMap())
        addDefaultInsignia(baseOutfit)
        self.as_setDefaultButtonEnabledS(not mode.currentOutfit.isEqual(baseOutfit))

    def __buildList(self):
        data = []
        if self.__ctx.mode.isOutfitsEmpty():
            return data
        vDesc = g_currentVehicle.item.descriptor
        availableRegionsMap = getCurrentVehicleAvailableRegionsMap()
        for season in (self.__ctx.season,) + tuple(s for s in SEASONS_ORDER if s != self.__ctx.season):
            purchaseItems = self.__ctx.mode.getActualPurchaseItems(season)
            data.extend(self.__getSeasonItemsData(purchaseItems, season, availableRegionsMap, vDesc))
        return data

    @staticmethod
    def __getSeasonGroupVO(s):
        return {'isTitle': True, 'titleLabel': makeHtmlString(
            'html_templates:lobby/customization/StylePopoverSeasonName', SEASON_TYPE_TO_NAME[s], ctx={'align': 'CENTER'})}

    def __getSeasonItemsData(self, purchaseItems, season, availableRegionsMap, vDesc):
        defCDs = getDefaultItemCDs(vDesc)
        items = {}
        for pItem in purchaseItems:
            item = pItem.item
            if pItem.group == AdditionalPurchaseGroups.STYLES_GROUP_ID:
                continue
            if item.intCD not in items:
                items[item.intCD] = C11nPopoverItemData(item=item, season=season, isBase=not pItem.isEdited, isRemovable=True)
            slotId = C11nId(pItem.areaID, pItem.slotType, pItem.regionIdx)
            items[item.intCD].slotsIds.append(slotId._asdict())

        style = self.__ctx.mode.getModifiedStyle(season)
        if not style:
            for defCD in defCDs:
                items.pop(defCD, None)
            if items:
                return [self.__getSeasonGroupVO(season)] + [
                    self.__makeItemDataVO(itemData) for itemData in sorted(items.values(), key=self.orderKey)]
            return []
        styleSeason = self.__ctx.mode.getModifiedStyleSeason(season)
        baseOutfit = style.getOutfit(styleSeason, vehicleCD=vDesc.makeCompactDescr())
        fitOutfit(baseOutfit, availableRegionsMap)
        addDefaultInsignia(baseOutfit)
        for intCD, _, regionIdx, container, _ in baseOutfit.itemsFull():
            item = self.__service.getItemByCD(intCD)
            if intCD not in items:
                items[intCD] = C11nPopoverItemData(item=item, season=season, isBase=True, isRemovable=True, isRemoved=True)
            if items[intCD].isRemoved:
                areaId = container.getAreaID()
                slotType = ITEM_TYPE_TO_SLOT_TYPE[item.itemTypeID]
                slotId = C11nId(areaId, slotType, regionIdx)
                items[intCD].slotsIds.append(slotId._asdict())
        items = {intCD: itemData for intCD, itemData in items.items()
                 if itemData.isRemoved or not itemData.isBase and intCD not in defCDs}
        items[style.intCD] = C11nPopoverItemData(
            item=style, season=season, isBase=True, isRemovable=True, isFromInventory=purchaseItems[0].progressionLevel)
        items[style.intCD].slotsIds.append(self.__ctx.mode.STYLE_SLOT._asdict())
        return [self.__getSeasonGroupVO(season)] + [
            self.__makeItemDataVO(itemData) for itemData in sorted(items.values(), key=self.orderKey)]

    @staticmethod
    def __makeItemDataVO(itemData):
        item = itemData.item
        return {
            'id': item.intCD, 'icon': fixIconPath(item.icon), 'userName': text_styles.main(getInsigniaUserName(item)),
            'numItems':
                '' if itemData.isRemoved or not itemData.isRemovable or item.itemTypeID == GUI_ITEM_TYPE.STYLE else
                text_styles.main('{} '.format(len(itemData.slotsIds))), 'isHistoric': item.isHistorical(), 'price': None,
            'isApplied': itemData.isBase, 'isWide': item.isWide(), 'itemsList': itemData.slotsIds,
            'isDim': item.isDim(), 'isEdited': not itemData.isBase, 'isDisabled': itemData.isRemoved,
            'disabledLabel': text_styles.bonusPreviewText(backport.text(
                R.strings.vehicle_customization.popover.style.removed())), 'isRemovable': itemData.isRemovable,
            'seasonType': itemData.season, 'progressionLevel': int(itemData.isFromInventory)}

    @staticmethod
    def orderKey(itemData):
        item = itemData.item
        order = (GUI_ITEM_TYPE.STYLE,) + tuple(i for i in TYPES_ORDER if i != GUI_ITEM_TYPE.STYLE)
        return not itemData.isBase, itemData.isRemovable, order.index(item.itemTypeID), item.intCD


popoverAlias = VIEW_ALIAS.CAMO_SELECTOR_KIT_POPOVER
g_entitiesFactories.addSettings(GroupedViewSettings(
    popoverAlias, EditableStylePopover, 'customizationEditedKitPopover.swf', WindowLayer.WINDOW, popoverAlias, popoverAlias,
    ScopeTemplates.DEFAULT_SCOPE))
g_eventBus.addListener(ViewEventType.LOAD_VIEW, lambda event: SL.appLoader.getApp().loadView(
    event.loadParams, event.ctx) if event.alias == popoverAlias else None, EVENT_BUS_SCOPE.LOBBY)
