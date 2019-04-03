from CurrentVehicle import g_currentVehicle
from PYmodsCore import overrideMethod
from gui.Scaleform.daapi.settings.views import VIEW_ALIAS
from gui.Scaleform.daapi.view.lobby.customization.installed_items_popover import InstalledItemsPopoverDataProvider as \
    WGDataProvider, _ItemGroupDescription, _RegionId
from gui.Scaleform.daapi.view.lobby.customization.shared import TYPES_ORDER, C11nMode
from gui.Scaleform.locale.VEHICLE_CUSTOMIZATION import VEHICLE_CUSTOMIZATION
from gui.Scaleform.managers.PopoverManager import PopoverManager
from gui.shared.formatters import text_styles
from helpers import dependency
from helpers.i18n import makeString as _ms
from skeletons.gui.customization import ICustomizationService
from .. import g_config


class InstalledItemsPopoverDataProvider(WGDataProvider):
    def buildList(self, nonHistoric):
        self.clear()
        hasDefaultCamo = g_currentVehicle.item.descriptor.type.hasCustomDefaultCamouflage
        isBuy = self.__ctx.isBuy
        purchaseItems = [
            it for it in (self.__ctx.getPurchaseItems() if isBuy else self.__ctx.getModdedPurchaseItems())
            if not it.isDismantling and it.group == self.__ctx.currentSeason]
        purchaseGroups = {}
        for it in purchaseItems:
            if nonHistoric and it.item.isHistorical():
                continue
            key = (it.item.intCD, it.isFromInventory)
            if key not in purchaseGroups:
                purchaseGroups[key] = _ItemGroupDescription(it.item, 0, [], it.slot, it.isFromInventory)
            purchaseGroups[key].numItems += 1
            purchaseGroups[key].regionIdList.append(_RegionId(it.areaID, it.slot, it.regionID))

        notModifiedOutfit = self.__ctx.getNotModifiedItems(self.__ctx.currentSeason)
        notModifiedGroups = {}
        for container in notModifiedOutfit.containers():
            for slot in container.slots():
                for idx in range(slot.capacity()):
                    item = slot.getItem(idx)
                    if not item or isBuy and item.isHiddenInUI() and hasDefaultCamo or nonHistoric and item.isHistorical():
                        continue
                    if item.intCD not in notModifiedGroups:
                        notModifiedGroups[item.intCD] = _ItemGroupDescription(item, 0, [], item.itemTypeID, True)
                    notModifiedGroups[item.intCD].numItems += 1
                    notModifiedGroups[item.intCD].regionIdList.append(_RegionId(container.getAreaID(), item.itemTypeID, idx))

        if purchaseGroups and notModifiedGroups:
            self._list.append({
                'userName': text_styles.main(_ms(VEHICLE_CUSTOMIZATION.CUSTOMIZATION_NONHISTORIC_TABLEHEADERS_NEW)),
                'isTitle': True})
        purchaseItemsGroupsSorted = sorted(
            purchaseGroups.values(), key=lambda v: (TYPES_ORDER.index(v.slotType), v.item.intCD, not v.isFromInventory))
        for group in purchaseItemsGroupsSorted:
            self._list.append(self._makeVO(group, False, group.isFromInventory))

        if purchaseGroups and notModifiedGroups:
            self._list.append({
                'userName': text_styles.main(_ms(VEHICLE_CUSTOMIZATION.CUSTOMIZATION_NONHISTORIC_TABLEHEADERS_PURCHASE)),
                'isTitle': True})
        notModifiedItemsGroupsSorted = sorted(
            notModifiedGroups.values(), key=lambda v: (TYPES_ORDER.index(v.slotType), v.item.intCD))
        for group in notModifiedItemsGroupsSorted:
            self._list.append(self._makeVO(group, True))


@overrideMethod(WGDataProvider, '__new__')
def new(base, cls, *a, **kw):
    if not g_config.data['enabled']:
        return base(cls, *a, **kw)
    return base(InstalledItemsPopoverDataProvider, *a, **kw)


@overrideMethod(PopoverManager, 'requestShowPopover')
@dependency.replace_none_kwargs(srv=ICustomizationService)
def new_requestShowPopover(base, self, alias, data, srv=None):
    if g_config.data['enabled'] and alias == VIEW_ALIAS.CUSTOMIZATION_ITEMS_POPOVER and srv.getCtx().mode == C11nMode.STYLE:
        alias = VIEW_ALIAS.CUSTOMIZATION_KIT_POPOVER
    return base(self, alias, data)
