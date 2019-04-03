from CurrentVehicle import g_currentVehicle
from gui.Scaleform.daapi.view.lobby.customization.installed_items_popover import InstalledItemsPopoverDataProvider as \
    WGDataProvider, _ItemGroupDescription, _RegionId
from gui.Scaleform.daapi.view.lobby.customization.shared import TYPES_ORDER
from gui.Scaleform.locale.VEHICLE_CUSTOMIZATION import VEHICLE_CUSTOMIZATION
from gui.shared.formatters import text_styles
from helpers.i18n import makeString as _ms


class InstalledItemsPopoverDataProvider(WGDataProvider):
    def buildList(self, isNonHistoric):
        import bwpydevd
        bwpydevd.startPyDevD('pycharm', suspend=True)
        self.clear()
        hasCustomDefaultCamouflage = g_currentVehicle.item.descriptor.type.hasCustomDefaultCamouflage
        purchaseItems = [
            it for it in (self.__ctx.getPurchaseItems() if self.__ctx.isBuy else self.__ctx.getModdedPurchaseItems())
            if not it.isDismantling and it.group == self.__ctx.currentSeason]
        purchaseItemsGroups = {}
        for it in purchaseItems:
            if not isNonHistoric or not it.item.isHistorical():
                key = (it.item.intCD, it.isFromInventory)
                if key not in purchaseItemsGroups:
                    purchaseItemsGroups[key] = _ItemGroupDescription(it.item, 0, [], it.slot, it.isFromInventory)
                purchaseItemsGroups[key].numItems += 1
                purchaseItemsGroups[key].regionIdList.append(_RegionId(it.areaID, it.slot, it.regionID))

        notModifiedOutfit = self.__ctx.getNotModifiedItems(self.__ctx.currentSeason)
        notModifiedItemsGroups = {}
        for container in notModifiedOutfit.containers():
            for slot in container.slots():
                for idx in range(slot.capacity()):
                    item = slot.getItem(idx)
                    if item:
                        if self.__ctx.isBuy and item.isHiddenInUI() and hasCustomDefaultCamouflage:
                            continue
                        if not isNonHistoric or not item.isHistorical():
                            if item.intCD not in notModifiedItemsGroups:
                                notModifiedItemsGroups[item.intCD] = _ItemGroupDescription(item, 0, [], item.itemTypeID, True)
                            notModifiedItemsGroups[item.intCD].numItems += 1
                            notModifiedItemsGroups[item.intCD].regionIdList.append(
                                _RegionId(container.getAreaID(), item.itemTypeID, idx))

        if purchaseItemsGroups and notModifiedItemsGroups:
            self._list.append({
                'userName': text_styles.main(_ms(VEHICLE_CUSTOMIZATION.CUSTOMIZATION_NONHISTORIC_TABLEHEADERS_NEW)),
                'isTitle': True})
        purchaseItemsGroupsSorted = sorted(
            purchaseItemsGroups.values(), key=lambda v: (TYPES_ORDER.index(v.slotType), v.item.intCD, not v.isFromInventory))
        for group in purchaseItemsGroupsSorted:
            self._list.append(self._makeVO(group, False, group.isFromInventory))

        if purchaseItemsGroups and notModifiedItemsGroups:
            self._list.append({
                'userName': text_styles.main(_ms(VEHICLE_CUSTOMIZATION.CUSTOMIZATION_NONHISTORIC_TABLEHEADERS_PURCHASE)),
                'isTitle': True})
        notModifiedItemsGroupsSorted = sorted(
            notModifiedItemsGroups.values(), key=lambda v: (TYPES_ORDER.index(v.slotType), v.item.intCD))
        for group in notModifiedItemsGroupsSorted:
            self._list.append(self._makeVO(group, True))
