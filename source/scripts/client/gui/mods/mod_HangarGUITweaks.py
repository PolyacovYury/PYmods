from CurrentVehicle import g_currentVehicle
from PYmodsCore import overrideMethod
from adisp import process
from debug_utils import LOG_ERROR
from goodies.goodie_constants import GOODIE_RESOURCE_TYPE
from gui import SystemMessages
from gui.Scaleform.daapi.view.lobby.customization.customization_cm_handlers import CustomizationItemCMHandler
from gui.Scaleform.daapi.view.lobby.customization.shared import removeItemsFromOutfit
from gui.Scaleform.daapi.view.lobby.storage import StorageCategoryPersonalReservesView
from gui.Scaleform.daapi.view.lobby.tank_setup import OptDeviceItemContextMenu
from gui.goodies.goodie_items import BOOSTERS_ORDERS
from gui.impl.backport import text
from gui.impl.gen import R
from gui.impl.lobby.customization.progressive_items_view.progressive_items_view import ProgressiveItemsView
from gui.shared.gui_items import GUI_ITEM_TYPE
from gui.shared.gui_items.items_actions import factory as ActionsFactory
from gui.shared.gui_items.processors.common import OutfitApplier
from gui.shared.tooltips.contexts import ModuleContext
from gui.shared.utils.decorators import process as process_waiting
from gui.shared.utils.requesters import REQ_CRITERIA
from items import vehicles
from items.components.c11n_constants import CUSTOM_STYLE_POOL_ID, CustomizationType, SeasonType

REMOVE_FROM_OTHER = 'removeFromOther'
misc_xp_tiers = (300, 200, 100, 50)
tank_xp_tiers = (100, 50, 25)
credits_tiers = (50, 25)
decal_order = ('battles', 'frags', 'BonusBattles', 'marksOfMastery', 'mainGun', 'BrothersInArms',)


@overrideMethod(ModuleContext, 'getStatsConfiguration')
def new_getStatsConfiguration(base, self, item):
    value = base(self, item)
    value.showCompatibles = True
    return value


@overrideMethod(CustomizationItemCMHandler, '_generateOptions')
def new_generateOptions(base, self, ctx=None):
    result = base(self, ctx)
    _ctx = self._CustomizationItemCMHandler__ctx
    if not getattr(_ctx, 'isPurchase', True) or self._item.isStyleOnly:
        return result
    appliedCount = 0  # mostly stolen from tooltips code
    vehicle = g_currentVehicle.item
    if self._item.itemTypeID != GUI_ITEM_TYPE.STYLE:
        appliedCount = _ctx.mode.getItemAppliedCount(self._item)
    elif vehicle is not None:
        currentStyleDesc = _ctx.mode.currentOutfit.style
        isApplied = currentStyleDesc is not None and self._item.id == currentStyleDesc.id
        appliedCount = int(isApplied)
    installedVehicles = {x: self.itemsCache.items.getItemByCD(x).shortUserName for x in self._item.getInstalledVehicles()}
    item_filter = self._item.descriptor.filter
    if (self._item.mayApply or appliedCount > 0 or not installedVehicles or vehicle.intCD in installedVehicles
            or item_filter is not None and not item_filter.match(vehicle.descriptor)):
        return result
    return result + [self._makeSeparator(), self._makeItem(
        REMOVE_FROM_OTHER, text(R.strings.vehicle_customization.propertySheet.actionBtn.clear()), optSubMenu=[
            self._makeItem(REMOVE_FROM_OTHER + '_' + str(vehicleCD), vehName)
            for vehicleCD, vehName in sorted(installedVehicles, key=lambda x: x[1])
        ])]


@overrideMethod(CustomizationItemCMHandler, 'onOptionSelect')
@process_waiting('customizationApply')
def new_onOptionSelect(base, self, optionId):
    if not optionId.startswith(REMOVE_FROM_OTHER):
        base(self, optionId)
        return
    vehicleCD = int(optionId.split('_')[1])
    item = self._item
    vehicle = self.itemsCache.items.getItemByCD(vehicleCD)
    if item.itemTypeID == GUI_ITEM_TYPE.STYLE:
        result = yield OutfitApplier(vehicle, ((self.service.getEmptyOutfit(), SeasonType.ALL),)).request()
        handleResult(result)
        return
    requestData = []
    for season in SeasonType.COMMON_SEASONS:
        originalOutfit = getCustomOutfit(self, vehicleCD, season)
        outfit = originalOutfit.copy()
        removeItemsFromOutfit(outfit, lambda i: i.intCD == item.intCD)
        if not outfit.isEqual(originalOutfit):
            requestData.append((outfit, season))
    if requestData:
        result = yield OutfitApplier(vehicle, requestData).request()
        handleResult(result)


def getCustomOutfit(self, vehicleCD, season):  # from service
    outfitsPool = self.itemsCache.items.inventory.getC11nOutfitsFromPool(vehicleCD)
    if not outfitsPool:
        return self.service.getEmptyOutfit()
    styleId, outfits = outfitsPool[0]
    if styleId != CUSTOM_STYLE_POOL_ID:
        return self.service.getEmptyOutfit()
    return self.service.itemsFactory.createOutfit(
        strCompactDescr=outfits.get(season, ''),
        vehicleCD=self._itemsCache.items.inventory.getItemData(vehicleCD).compDescr)


def handleResult(result):
    if result.userMsg:
        SystemMessages.pushI18nMessage(result.userMsg, type=result.sysMsgType)
    if result.success:
        return SystemMessages.pushMessage(text(
            R.strings.messenger.serviceChannelMessages.sysMsg.customization.remove()), SystemMessages.SM_TYPE.Information)
    LOG_ERROR('failed to purchase customization outfits.')


@overrideMethod(OptDeviceItemContextMenu, '_generateOptions')
def new_generateOptions(base, self, ctx, *a, **k):
    result = base(self, ctx, *a, **k)
    if not self._isDisabled:  # mostly stolen from tooltips code
        return result
    item = self._getItem()
    inventoryVehicles = self._itemsCache.items.getVehicles(REQ_CRITERIA.INVENTORY).itervalues()
    installedVehicles = {x: x.shortUserName for x in item.getInstalledVehicles(inventoryVehicles)}
    if self._getVehicle().intCD in installedVehicles:
        return result
    return result + [self._makeSeparator(), self._makeItem(
        REMOVE_FROM_OTHER, text(R.strings.vehicle_customization.propertySheet.actionBtn.clear()), optSubMenu=[
            self._makeItem(REMOVE_FROM_OTHER + '_%s_%s' % (vehicle.intCD, vehicle.optDevices.installed.index(item)), vehName)
            for vehicle, vehName in sorted(installedVehicles, key=lambda x: x[1])
        ])]


@overrideMethod(OptDeviceItemContextMenu, 'onOptionSelect')
@process
def new_onOptionSelect(base, self, optionId, *a, **k):
    if not optionId.startswith(REMOVE_FROM_OTHER):
        base(self, optionId, *a, **k)
    vehicleCD, slotID = map(int, optionId.split('_')[1:])
    yield ActionsFactory.asyncDoAction(ActionsFactory.getAction(
        ActionsFactory.REMOVE_OPT_DEVICE, self._itemsCache.items.getItemByCD(vehicleCD), self._getItem(), slotID, False))


def item_tier(item):
    bType = item.boosterType
    tiers = (
        misc_xp_tiers if bType in (GOODIE_RESOURCE_TYPE.CREW_XP, GOODIE_RESOURCE_TYPE.FREE_XP) else
        tank_xp_tiers if bType in (GOODIE_RESOURCE_TYPE.XP,) else
        credits_tiers if bType in (GOODIE_RESOURCE_TYPE.CREDITS,) else
        ())
    try:
        return tiers.index(item.effectValue)
    except ValueError:
        return -1


@overrideMethod(StorageCategoryPersonalReservesView, '__sort')
def new_sort(_, __, a, b):
    return cmp(item_tier(a), item_tier(b)) or cmp(BOOSTERS_ORDERS[a.boosterType], BOOSTERS_ORDERS[b.boosterType]) or cmp(
        b.effectTime, a.effectTime)


@overrideMethod(ProgressiveItemsView, '_getPossibleItemsForVehicle')
def new_getPossibleItemsForVehicle(_, self):
    customizationCache = vehicles.g_cache.customization20()
    vehicleType = self._vehicle.descriptor.type
    return [_item.compactDescr for _item in sorted(
        [item for item in customizationCache.customizationWithProgression.itervalues()
         if item.itemType == CustomizationType.PROJECTION_DECAL
         and (item.filter is None or item.filter.matchVehicleType(vehicleType))],
        key=lambda i: (
            next((j for j, tag in enumerate(decal_order) if tag in i.progression.levels[1]['conditions'][0]['path'][1]), 100),
            i.id
        ))]
