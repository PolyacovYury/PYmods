from CurrentVehicle import g_currentVehicle
from PYmodsCore import PYmodsConfigInterface, overrideMethod
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


class ConfigInterface(PYmodsConfigInterface):
    def init(self):
        self.ID = '%(mod_ID)s'
        self.version = '1.0.0 (%(file_compile_date)s)'
        self.data = {
            'enabled': True, 'showCompatibles': True,
            'removeFromOther_devices': True, 'removeFromOther_customization': True,
            'sort_progressionDecals': True, 'sort_personalReserves': True,
        }
        self.i18n = {
            'name': 'Hangar GUI Tweaks',
            'UI_setting_showCompatibles_text': 'Show compatible vehicles for modules in tech tree',
            'UI_setting_showCompatibles_tooltip': (
                'This setting adds the list of compatible vehicles into tooltips of vehicle modules, '
                'removing the need to open the info window to see it.'),
            'UI_setting_removeFromOther_customization_text': 'Add option to remove a customization from other vehicle',
            'UI_setting_removeFromOther_customization_tooltip': (
                'This setting adds a context menu option to take off the customization item from another vehicle.\n'
                'The option is only added for items that can\'t be installed on current vehicle without removing it '
                'from another one.'),
            'UI_setting_removeFromOther_devices_text': 'Add option to remove an optional device from other vehicle',
            'UI_setting_removeFromOther_devices_tooltip': (
                'This setting adds a context menu option to take off the optional device from another vehicle.\n'
                'The option is only added for items that can\'t be installed on current vehicle without removing it '
                'from another one.'),
            'UI_setting_sort_personalReserves_text': 'Change sorting of personal reserves in Storage view',
            'UI_setting_sort_personalReserves_tooltip': (
                'This setting changes sorting priority of personal reserves from type-tier-time to tier-type-time.\n'
                'In other words, all the best personal reserves are displayed first.'),
            'UI_setting_sort_progressionDecals_text': 'Change sorting of progression decals in Customization view',
            'UI_setting_sort_progressionDecals_tooltip': (
                'This setting changes sorting order of progression decals to make easier ones appear first in the list.'),
        }
        super(ConfigInterface, self).init()

    def createTemplate(self):
        return {
            'modDisplayName': self.i18n['name'], 'enabled': self.data['enabled'],
            'column1': [
                self.tb.createControl('removeFromOther_devices'),
                self.tb.createControl('sort_personalReserves'),
                self.tb.createControl('showCompatibles'),
            ],
            'column2': [
                self.tb.createControl('removeFromOther_customization'),
                self.tb.createControl('sort_progressionDecals'),
            ]}


g_config = ConfigInterface()


@overrideMethod(ModuleContext, 'getStatsConfiguration')
def new_getStatsConfiguration(base, self, item):
    value = base(self, item)
    if g_config.data['enabled'] and g_config.data['showCompatibles']:
        value.showCompatibles = True
    return value


@overrideMethod(CustomizationItemCMHandler, '_generateOptions')
def new_generateOptions(base, self, ctx=None):
    result = base(self, ctx)
    _ctx = self._CustomizationItemCMHandler__ctx
    if not (g_config.data['enabled'] and g_config.data['removeFromOther_customization']):
        return result
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
    if not (g_config.data['enabled'] and g_config.data['removeFromOther_devices']):
        return result
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
def new_sort(base, self, a, b, *_a, **k):
    if not (g_config.data['enabled'] and g_config.data['sort_personalReserves']):
        return base(self, a, b, *_a, **k)
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
        key=(lambda i: (
            next((j for j, tag in enumerate(decal_order) if tag in i.progression.levels[1]['conditions'][0]['path'][1]), 100),
            i.id
        ) if g_config.data['enabled'] and g_config.data['sort_progressionDecals'] else i.id))]
