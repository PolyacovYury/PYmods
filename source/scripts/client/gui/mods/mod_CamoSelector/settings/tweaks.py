from PYmodsCore import overrideMethod
from gui.Scaleform.daapi.view.lobby.customization import (
    customization_style_info as si)
from gui.Scaleform.daapi.view.lobby.customization.popovers import C11nPopoverItemData, orderKey
from gui.Scaleform.daapi.view.lobby.customization.popovers.custom_popover import CustomPopoverDataProvider
from gui.Scaleform.daapi.view.lobby.customization.shared import getSlotDataFromSlot, ITEM_TYPE_TO_SLOT_TYPE
from gui.customization.shared import getPurchaseMoneyState, isTransactionValid, C11nId
from gui.impl import backport
from gui.impl.gen import R
from helpers import dependency
from items.components import c11n_components as c11c
from itertools import ifilter
from shared_utils import first
from skeletons.gui.customization import ICustomizationService
from .. import g_config


@overrideMethod(c11c, 'isPersonalNumberAllowed')
@dependency.replace_none_kwargs(service=ICustomizationService)
def isPersonalNumberAllowed(base, number, service=None):
    return (g_config.data['enabled'] and not service.getCtx().isPurchase) or base(number)


@overrideMethod(si.CustomizationStyleInfo, '__makeButtonVO')
def new_makeButtonVO(base, self, style):
    if not g_config.data['enabled']:
        return base(self, style)
    ctx = self._CustomizationStyleInfo__ctx
    if not ctx.isOutfitsModified():
        return None
    label = backport.text(R.strings.vehicle_customization.commit.apply())
    enabled = True
    if ctx.isPurchase:
        stylePrice = style.getBuyPrice().price
        moneyState = getPurchaseMoneyState(stylePrice)
        purchaseItem = first(ctx.mode.getPurchaseItems())
        if purchaseItem is not None and not purchaseItem.isFromInventory:
            label = backport.text(R.strings.vehicle_customization.commit.buy())
            enabled = isTransactionValid(moneyState, stylePrice)
    return si.ButtonVO(enabled=enabled, label=label, disabledTooltip=backport.text(
        R.strings.vehicle_customization.customization.buyDisabled.body()), visible=True)._asdict()


@overrideMethod(CustomPopoverDataProvider, '__getModifiedItemsData')
def __getModifiedItemsData(base, self):
    if not g_config.data['enabled']:
        return base(self)
    itemData = {}
    ctx = self._CustomPopoverDataProvider__ctx
    if ctx.isPurchase:
        purchaseItems = ctx.mode.getPurchaseItems()
    else:
        purchaseItems = ctx.mode.getModdedPurchaseItems()
    purchaseItems = ifilter(lambda i: i.group == ctx.season, purchaseItems)
    modifiedOutfit = ctx.mode.getModifiedOutfit()
    originalOutfit = ctx.mode.getOriginalOutfit()
    for pItem in purchaseItems:
        if self._CustomPopoverDataProvider__isNonHistoric and pItem.item.isHistorical():
            continue
        slotId = C11nId(pItem.areaID, pItem.slotType, pItem.regionIdx)
        modifiedSlotData = getSlotDataFromSlot(modifiedOutfit, slotId)
        originalSlotData = getSlotDataFromSlot(originalOutfit, slotId)
        if modifiedSlotData is None or originalSlotData is None or modifiedSlotData.isEqual(originalSlotData):
            continue
        key = (pItem.item.intCD, pItem.isFromInventory)
        if key not in itemData:
            itemData[key] = C11nPopoverItemData(item=pItem.item, isFromInventory=pItem.isFromInventory)
        itemData[key].slotsIds.append(slotId._asdict())
    return sorted(itemData.values(), key=orderKey)


@overrideMethod(CustomPopoverDataProvider, '__getOriginalItemsData')
def __getOriginalItemsData(base, self):
    if not g_config.data['enabled']:
        return base(self)
    itemData = {}
    ctx = self._CustomPopoverDataProvider__ctx
    notModifiedOutfit = ctx.mode.getNotModifiedItems()
    for intCD, _, regionIdx, container, _ in notModifiedOutfit.itemsFull():
        item = self._CustomPopoverDataProvider__service.getItemByCD(intCD)
        if ctx.isPurchase and item.isHiddenInUI():
            continue
        if self._CustomPopoverDataProvider__isNonHistoric and item.isHistorical():
            continue
        areaId = container.getAreaID()
        slotType = ITEM_TYPE_TO_SLOT_TYPE[item.itemTypeID]
        slotId = C11nId(areaId, slotType, regionIdx)
        if intCD not in itemData:
            itemData[intCD] = C11nPopoverItemData(item=item, isFromInventory=True)
        itemData[intCD].slotsIds.append(slotId._asdict())
    return sorted(itemData.values(), key=orderKey)


@overrideMethod(CustomPopoverDataProvider, '__makeItemDataVO')
def __makeItemDataVO(base, itemData, isModified):
    data = base(itemData, isModified)
    if '4278190335,4278255360,4294901760,4278190080' in data['icon']:
        data['icon'] = '../../' + data['icon'].split('"', 2)[1]
    return data
