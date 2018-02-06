from CurrentVehicle import g_currentVehicle
from collections import Counter
from gui.Scaleform.daapi.view.lobby.customization.shared import Cart, PurchaseItem
from gui.customization.shared import HighlightingMode
from gui.shared.gui_items.gui_item_economics import ITEM_PRICE_EMPTY
from shared_utils import CONST_CONTAINER
from ..shared import isCamoInternational


class C11N_MODE(CONST_CONTAINER):
    """ Customization mode.
    """
    INSTALL, SETUP = range(2)
    NAMES = {INSTALL: 'install', SETUP: 'setup'}


class CUSTOMIZATION_TABS(CONST_CONTAINER):
    """
    Enumeration of customization item browser tabs.
    The order of the ALL property corresponds to the order the tab names will appear in.
    """
    SHOP, HIDDEN, INTERNATIONAL, CUSTOM = range(4)
    AVAILABLE_REGIONS = (SHOP, HIDDEN, INTERNATIONAL, CUSTOM)
    ALL = (SHOP, HIDDEN, INTERNATIONAL, CUSTOM)
    VISIBLE = ALL


def chooseMode(settingMode, vehicle):
    """ Choose mode for the highlighter from the given item type and vehicle.
    """
    # if settingMode == C11N_MODE.INSTALL:
    if vehicle.turret.isGunCarriage:
        return HighlightingMode.CAMO_REGIONS_SKIP_TURRET
    return HighlightingMode.CAMO_REGIONS
    # return HighlightingMode.WHOLE_VEHICLE


def getCustomPurchaseItems(outfitsInfo):
    """ Builds and returns a list of PurchaseItems.  This list will only contain items that would be newly purchased.
    This takes into account current inventory and what items are already available.
    :return: list of PurchaseItem entries containing items that would require a new purchase.
    """
    purchaseItems = []
    inventoryCount = Counter()
    for season, outfitCompare in outfitsInfo.iteritems():
        inventoryCount.update({i.intCD: 0 for i in outfitCompare.modified.items()})

    for season, outfitCompare in outfitsInfo.iteritems():
        backward = outfitCompare.modified.diff(outfitCompare.original)
        for container in backward.containers():
            for slot in container.slots():
                for idx in range(slot.capacity()):
                    item = slot.getItem(idx)
                    if item:
                        # noinspection PyArgumentEqualDefault
                        purchaseItems.append(PurchaseItem(
                            item, price=item.getBuyPrice(), areaID=container.getAreaID(), slot=slot.getType(),
                            regionID=idx, selected=True, group=season, isFromInventory=True, isDismantling=False))
                        inventoryCount[item.intCD] += 1

    for season, outfitCompare in outfitsInfo.iteritems():
        forward = outfitCompare.original.diff(outfitCompare.modified)
        for container in forward.containers():
            for slot in container.slots():
                for idx in range(slot.capacity()):
                    item = slot.getItem(idx)
                    if item:
                        # noinspection PyArgumentEqualDefault
                        purchaseItems.append(PurchaseItem(
                            item, price=item.getBuyPrice(), areaID=container.getAreaID(), slot=slot.getType(),
                            regionID=idx, selected=True, group=season, isFromInventory=True, isDismantling=False))
                        inventoryCount[item.intCD] -= 1

    return purchaseItems


def getTotalPurchaseInfo(purchaseItems):
    """ Get purchase info (total price that needs to be paid,
    number of actually selected items and total number of items.
    """
    totalPrice = ITEM_PRICE_EMPTY
    numSelectedItems = 0
    numApplyingItems = 0
    for purchaseItem in purchaseItems:
        if not purchaseItem.isDismantling:
            numApplyingItems += 1
        if purchaseItem.selected and not purchaseItem.isDismantling:
            numSelectedItems += 1
            if not purchaseItem.isFromInventory:
                totalPrice += purchaseItem.price

    return Cart(totalPrice, numSelectedItems, numApplyingItems, len(purchaseItems))


def getItemInventoryCount(item, outfitsInfo=None):
    """ Gets the actual available inventory count of an item.
    (including the items that had been put off but haven't been committed yet)
    """
    inventoryCount = item.fullInventoryCount(g_currentVehicle.item)
    if not outfitsInfo:
        return inventoryCount
    intCD = item.intCD
    for season, outfitCompare in outfitsInfo.iteritems():
        old = Counter((i.intCD for i in outfitCompare.original.items()))
        new = Counter((i.intCD for i in outfitCompare.modified.items()))
        inventoryCount += old[intCD] - new[intCD]

    return max(0, inventoryCount)


def isItemSuitableForTab(item, tabIndex):
    from .. import g_config
    ct = CUSTOMIZATION_TABS
    isInter = isCamoInternational(g_config, item.descriptor)
    return not ((tabIndex == ct.SHOP and (item.isHidden or item.priceGroup == 'modded'))
                or (tabIndex == ct.HIDDEN and (not item.isHidden or isInter or item.priceGroup == 'modded'))
                or (tabIndex == ct.INTERNATIONAL and not isInter)
                or (tabIndex == ct.CUSTOM and item.priceGroup != 'modded'))
