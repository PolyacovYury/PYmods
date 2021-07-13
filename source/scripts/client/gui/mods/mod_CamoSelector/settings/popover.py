from collections import namedtuple

from PYmodsCore import BigWorld_callback
from frameworks.wulf import WindowLayer
from gui import makeHtmlString
from gui.Scaleform.daapi.view.lobby.customization.popovers import C11nPopoverItemData
from gui.Scaleform.daapi.view.lobby.customization.shared import ITEM_TYPE_TO_SLOT_TYPE
from gui.Scaleform.daapi.view.meta.CustomizationEditedKitPopoverMeta import CustomizationEditedKitPopoverMeta
from gui.Scaleform.framework import GroupedViewSettings, ScopeTemplates, g_entitiesFactories
from gui.customization.shared import AdditionalPurchaseGroups, C11nId, SEASONS_ORDER, SEASON_TYPE_TO_NAME
from gui.impl.backport import image, text
from gui.impl.gen import R
from gui.shared import EVENT_BUS_SCOPE, g_eventBus
from gui.shared.events import ViewEventType
from gui.shared.formatters import icons, text_styles
from gui.shared.gui_items import GUI_ITEM_TYPE
from gui.shared.personality import ServicesLocator as SL
from helpers import dependency
from skeletons.gui.customization import ICustomizationService
from .shared import fixIconPath, getInsigniaUserName
from .. import g_config
from ..constants import TYPES_ORDER, VIEW_ALIAS
from ..processors import getDefaultItemCDs, getOutfitFromStyle

PurchaseItemPlaceholder = namedtuple('NotPItem', 'item progressionLevel')


class EditableStylePopover(CustomizationEditedKitPopoverMeta):
    __service = dependency.descriptor(ICustomizationService)

    def __init__(self, ctx=None):
        super(EditableStylePopover, self).__init__(ctx)
        self.__ctx = None

    def onWindowClose(self):
        self.destroy()

    def remove(self, intCD, slotIds, season):
        if season != AdditionalPurchaseGroups.UNASSIGNED_GROUP_ID:
            return self.__ctx.mode.removeFromSlots([C11nId(**slotId.toDict()) for slotId in slotIds], season)
        self.__ctx.mode.rollbackSettings(self.__service.getItemByCD(intCD))
        self.__ctx.events.onCacheResync()

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
        self.as_setHeaderS(text_styles.highTitle(text(
            R.strings.vehicle_customization.customization.kitPopover.title.items())))
        self.as_setHelpMessageS(
            icons.makeImageTag(image(R.images.gui.maps.icons.customization.edited_small()))
            + text_styles.main(text(R.strings.vehicle_customization.popover.editableStyle.editedItems())))

    def __setClearMessage(self):
        self.as_showClearMessageS('' if not self.__ctx.mode.isOutfitsEmpty() else text_styles.main(text(
            R.strings.vehicle_customization.customization.itemsPopover.clear.message())))

    def __update(self, *_):
        self.as_setItemsS({'items': self.__buildList()})
        self.__setHeader()
        self.__setClearMessage()
        self.__updateClearStyleButton()

    def __updateClearStyleButton(self):
        mode = self.__ctx.mode
        style = mode.modifiedStyle
        BigWorld_callback(0, self.as_setClearButtonEnabledS, style is not None)  # must run after flash invalidate()
        self.as_setDefaultButtonEnabledS(bool(style) and (
                mode.modifiedStyleSeason != mode.season
                or not mode.currentOutfit.isEqual(getOutfitFromStyle(style, mode.season, mode.getStyleProgressionLevel()))))

    def __buildList(self):
        return [] if self.__ctx.mode.isOutfitsEmpty() else sum((self.__getSeasonItemsData(
            self.__ctx.mode.getActualPurchaseItems(season), season)
            for season in (self.__ctx.season,) + tuple(s for s in SEASONS_ORDER if s != self.__ctx.season)),
            self.__getSettingsItemsData())

    @staticmethod
    def __getSeasonGroupVO(s):
        return {'isTitle': True, 'titleLabel': makeHtmlString(
            'html_templates:lobby/customization/StylePopoverSeasonName', SEASON_TYPE_TO_NAME[s], ctx={'align': 'CENTER'})}

    def __getSeasonItemsData(self, purchaseItems, season):
        defCDs = getDefaultItemCDs()
        items = {}
        for pItem in purchaseItems:
            item = pItem.item
            if pItem.group == AdditionalPurchaseGroups.STYLES_GROUP_ID or item.itemTypeID not in ITEM_TYPE_TO_SLOT_TYPE:
                continue
            if item.intCD not in items:
                items[item.intCD] = C11nPopoverItemData(
                    item=pItem, season=season, isBase=not pItem.isEdited, isRemovable=True)
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
        baseOutfit = getOutfitFromStyle(
            style, self.__ctx.mode.getModifiedStyleSeason(season), purchaseItems[0].progressionLevel)
        for intCD, _, regionIdx, container, _ in baseOutfit.itemsFull():
            item = self.__service.getItemByCD(intCD)
            if item.itemTypeID not in ITEM_TYPE_TO_SLOT_TYPE:
                continue
            if intCD not in items:
                items[intCD] = C11nPopoverItemData(
                    item=PurchaseItemPlaceholder(item, -1), season=season, isBase=True, isRemovable=True, isRemoved=True)
            if items[intCD].isRemoved:
                areaId = container.getAreaID()
                slotType = ITEM_TYPE_TO_SLOT_TYPE[item.itemTypeID]
                slotId = C11nId(areaId, slotType, regionIdx)
                items[intCD].slotsIds.append(slotId._asdict())
        items = {intCD: itemData for intCD, itemData in items.items()
                 if itemData.isRemoved or not itemData.isBase and intCD not in defCDs}
        items[style.intCD] = C11nPopoverItemData(item=purchaseItems[0], season=season, isBase=True, isRemovable=True)
        items[style.intCD].slotsIds.append(self.__ctx.mode.STYLE_SLOT._asdict())
        return [self.__getSeasonGroupVO(season)] + [
            self.__makeItemDataVO(itemData) for itemData in sorted(items.values(), key=self.orderKey)]

    @staticmethod
    def __makeItemDataVO(itemData):
        pItem = itemData.item
        item = pItem.item
        item_name = getInsigniaUserName(item)
        if item.itemTypeID == GUI_ITEM_TYPE.STYLE and pItem.component != itemData.season:
            item_name += (' ' + text(
                R.strings.vehicle_customization.customization.camouflage.dyn(SEASON_TYPE_TO_NAME[pItem.component])()))
        return {
            'id': item.intCD, 'icon': fixIconPath(item.icon), 'userName': text_styles.main(item_name),
            'numItems':
                '' if itemData.isRemoved or not itemData.isRemovable or item.itemTypeID == GUI_ITEM_TYPE.STYLE else
                text_styles.main('{} '.format(len(itemData.slotsIds))), 'isHistoric': item.isHistorical(), 'price': None,
            'isApplied': itemData.isBase, 'isWide': item.isWide(), 'itemsList': itemData.slotsIds,
            'isDim': item.isDim(), 'isEdited': not itemData.isBase, 'isDisabled': itemData.isRemoved,
            'disabledLabel': text_styles.bonusPreviewText(text(
                R.strings.vehicle_customization.popover.style.removed())), 'isRemovable': itemData.isRemovable,
            'seasonType': itemData.season, 'progressionLevel': pItem.progressionLevel}

    @staticmethod
    def orderKey(itemData):
        item = itemData.item.item
        order = (GUI_ITEM_TYPE.STYLE,) + tuple(i for i in TYPES_ORDER if i != GUI_ITEM_TYPE.STYLE)
        return order.index(item.itemTypeID), not itemData.isBase, itemData.isRemovable, item.intCD

    def __getSettingsItemsData(self):
        result = []
        for intCD, num in sorted(self.__ctx.mode.getChangedItemData().items()):
            data = C11nPopoverItemData(
                item=PurchaseItemPlaceholder(self.__service.getItemByCD(intCD), -1),
                season=AdditionalPurchaseGroups.UNASSIGNED_GROUP_ID, isBase=True, isRemovable=True)
            data.slotsIds = [{}] * num
            result.append(self.__makeItemDataVO(data))
        if not result:
            return result
        group_title = g_config.color_compat(text(R.strings.settings.colorSettings.tab.customSettings()))
        # noinspection SpellCheckingInspection
        return [{
            'isTitle': True,
            'titleLabel': (
                    '<textformat indent="0" leftmargin="0" rightmargin="0" leading="1">'
                    '<p align="center"><font face="$fieldfont" size="14" color="#e9e2bf" kerning="0">'
                    '<img src="img://gui/maps/icons/buttons/settings.png"'
                    ' width="16" height="16" vspace="-3" align="baseline"> '
                    '%s</font></p></textformat>' % group_title)
        }] + result


popoverAlias = VIEW_ALIAS.CAMO_SELECTOR_KIT_POPOVER
g_entitiesFactories.addSettings(GroupedViewSettings(
    popoverAlias, EditableStylePopover, 'customizationEditedKitPopover.swf', WindowLayer.WINDOW, popoverAlias, popoverAlias,
    ScopeTemplates.DEFAULT_SCOPE))
g_eventBus.addListener(ViewEventType.LOAD_VIEW, lambda event: SL.appLoader.getApp().loadView(
    event.loadParams, event.ctx) if event.alias == popoverAlias else None, EVENT_BUS_SCOPE.LOBBY)
