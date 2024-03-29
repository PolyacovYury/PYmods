import nations
from CurrentVehicle import g_currentVehicle
from OpenModsCore import SimpleConfigInterface, overrideMethod
from account_helpers.AccountSettings import CAROUSEL_FILTER_CLIENT_1, DEFAULT_VALUES, KEY_FILTERS
from adisp import adisp_process
from debug_utils import LOG_ERROR
from goodies.goodie_constants import GOODIE_RESOURCE_TYPE
from gui import GUI_NATIONS_ORDER_INDEX, SystemMessages
from gui.Scaleform import getButtonsAssetPath
from gui.Scaleform.daapi.view.common.filter_popover import TankCarouselFilterPopover, FILTER_SECTION
from gui.Scaleform.daapi.view.common.vehicle_carousel.carousel_data_provider import CarouselDataProvider
from gui.Scaleform.daapi.view.common.vehicle_carousel.carousel_filter import BasicCriteriesGroup
from gui.Scaleform.daapi.view.lobby.customization.customization_cm_handlers import CustomizationItemCMHandler
from gui.Scaleform.daapi.view.lobby.customization.shared import removeItemsFromOutfit
from gui.Scaleform.daapi.view.lobby.hangar.carousels.basic.carousel_data_provider import HangarCarouselDataProvider
from gui.Scaleform.daapi.view.lobby.storage import StorageCategoryPersonalReservesView
from gui.Scaleform.daapi.view.lobby.tank_setup import OptDeviceItemContextMenu
from gui.Scaleform.locale.RES_ICONS import RES_ICONS
from gui.goodies.goodie_items import BOOSTERS_ORDERS
from gui.impl import backport
from gui.impl.backport import text
from gui.impl.gen import R
from gui.impl.lobby.customization.progressive_items_view.progressive_items_view import ProgressiveItemsView
from gui.shared.formatters import icons, text_styles
from gui.shared.gui_items import GUI_ITEM_TYPE
from gui.shared.gui_items.Vehicle import VEHICLE_TYPES_ORDER_INDICES, Vehicle
from gui.shared.gui_items.items_actions import factory as ActionsFactory
from gui.shared.gui_items.processors.common import OutfitApplier
from gui.shared.items_parameters.params_cache import _ParamsCache, _getVehicleSuitablesByType
from gui.shared.tooltips.contexts import ModuleContext
from gui.shared.utils.decorators import adisp_process as process_waiting
from gui.shared.utils.functions import makeTooltip
from gui.shared.utils.requesters import REQ_CRITERIA
from gui.veh_post_progression.models.progression import PostProgressionCompletion
from items import vehicles
from items.components.c11n_constants import CUSTOM_STYLE_POOL_ID, CustomizationType, SeasonType

REMOVE_FROM_OTHER = 'removeFromOther'
misc_xp_tiers = (300, 200, 100, 50)
tank_xp_tiers = (100, 50, 25)
credits_tiers = (50, 25)
decal_order = ('battles', 'frags', 'BonusBattles', 'marksOfMastery', 'mainGun', 'BrothersInArms',)
DEFAULT_VALUES[KEY_FILTERS][CAROUSEL_FILTER_CLIENT_1]['normal'] = False
for _alliance in nations.ALLIANCES_TAGS_ORDER:
    DEFAULT_VALUES[KEY_FILTERS][CAROUSEL_FILTER_CLIENT_1][_alliance] = False


class ConfigInterface(SimpleConfigInterface):
    def init(self):
        self.ID = '%(mod_ID)s'
        self.version = '1.1.0 (%(file_compile_date)s)'
        self.author = 'by Polyacov_Yury'
        self.modsGroup = 'PYmods'
        self.modSettingsID = 'PYmodsGUI'
        self.data = {
            'enabled': True, 'showCompatibles': True,
            'removeFromOther_devices': True, 'removeFromOther_customization': True,
            'sort_progressionDecals': True, 'sort_personalReserves': True, 'sort_vehicleCarousel': False,
            'filter_vehicleCarousel_normal': True, 'filter_vehicleCarousel_alliance': True,
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
            'UI_setting_sort_progressionDecals_text': 'Change sorting of progression decals in Exterior view',
            'UI_setting_sort_progressionDecals_tooltip': (
                'This setting changes sorting order of progression decals to make easier ones appear first in the list.'),
            'UI_setting_sort_vehicleCarousel_text': 'Change sorting of vehicles in Hangar carousel',
            'UI_setting_sort_vehicleCarousel_tooltip': (
                'This setting changes sorting order of vehicles to make higher tiers appear first in the list.'),
            'UI_setting_filter_vehicleCarousel_normal_text': 'Add "Not researched" vehicle filter into Hangar carousel',
            'UI_setting_filter_vehicleCarousel_normal_tooltip': (
                'This setting adds a new filter button into vehicle filter popover that shows only non-elite vehicles.'),
            'UI_setting_filter_vehicleCarousel_alliance_text': 'Add per-Alliance vehicle filter into Hangar carousel',
            'UI_setting_filter_vehicleCarousel_alliance_tooltip': (
                'This setting adds new filter buttons into vehicle filter popover that show only vehicles that belong to '
                'a certain Alliance.'),
        }
        super(ConfigInterface, self).init()

    def createTemplate(self):
        return {
            'modDisplayName': self.i18n['name'], 'enabled': self.data['enabled'],
            'column1': [
                self.tb.createControl('showCompatibles'),
                self.tb.createControl('sort_personalReserves'),
                self.tb.createControl('sort_progressionDecals'),
                self.tb.createControl('sort_vehicleCarousel'),
            ],
            'column2': [
                self.tb.createControl('removeFromOther_devices'),
                self.tb.createControl('removeFromOther_customization'),
                self.tb.createControl('filter_vehicleCarousel_normal'),
                self.tb.createControl('filter_vehicleCarousel_alliance'),
            ]}


g_config = ConfigInterface()


@overrideMethod(ModuleContext, 'getStatsConfiguration')
def new_getStatsConfiguration(base, self, item, *args, **kwargs):
    value = base(self, item, *args, **kwargs)
    if g_config.data['enabled'] and g_config.data['showCompatibles']:
        value.showCompatibles = True
    return value


@overrideMethod(_ParamsCache, 'getComponentVehiclesNames')
def getComponentVehiclesNames(base, self, typeCompactDescr, *args, **kwargs):
    if not (g_config.data['enabled'] and g_config.data['showCompatibles']):
        return base(self, typeCompactDescr, *args, **kwargs)
    itemTypeIdx, nationIdx, _ = vehicles.parseIntCompactDescr(typeCompactDescr)
    getter = vehicles.g_cache.vehicle
    result = []
    for itemID in vehicles.g_list.getList(nationIdx).iterkeys():
        vehicleType = getter(nationIdx, itemID)
        components = _getVehicleSuitablesByType(vehicleType, itemTypeIdx)
        filtered = [item for item in components if item.compactDescr == typeCompactDescr]
        if filtered:
            vehicleName = vehicleType.userString
            if components[0] == filtered[0]:
                vehicleName = text_styles.discountText(vehicleName)
            result.append(vehicleName)
    return result


@overrideMethod(CustomizationItemCMHandler, '_generateOptions')
def new_generateOptions(base, self, ctx=None, *args, **kwargs):
    result = base(self, ctx, *args, **kwargs)
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
def new_onOptionSelect(base, self, optionId, *args, **kwargs):
    if not optionId.startswith(REMOVE_FROM_OTHER):
        base(self, optionId, *args, **kwargs)
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
@adisp_process
def new_onOptionSelect(base, self, optionId, *a, **k):
    if not optionId.startswith(REMOVE_FROM_OTHER):
        base(self, optionId, *a, **k)
        return
    vehicleCD, slotID = map(int, optionId.split('_')[1:])
    yield ActionsFactory.asyncDoAction(ActionsFactory.getAction(
        ActionsFactory.REMOVE_OPT_DEVICE, self._itemsCache.items.getItemByCD(vehicleCD), self._getItem(), slotID, False))


def booster_tier(item):
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
    return int(a.count <= 1) or cmp(booster_tier(a), booster_tier(b)) or cmp(
        BOOSTERS_ORDERS[a.boosterType], BOOSTERS_ORDERS[b.boosterType]) or cmp(b.effectTime, a.effectTime)


@overrideMethod(ProgressiveItemsView, '_getPossibleItemsForVehicle')
def new_getPossibleItemsForVehicle(_, self, *_args, **_kwargs):
    if not g_config.data['enabled'] or not g_config.data['sort_progressionDecals']:
        return
    customizationCache = vehicles.g_cache.customization20()
    vehicleType = self._vehicle.descriptor.type
    return [_item.compactDescr for _item in sorted(
        (item for item in customizationCache.customizationWithProgression.itervalues()
         if item.itemType == CustomizationType.PROJECTION_DECAL
         and (item.filter is None or item.filter.matchVehicleType(vehicleType))),
        key=(lambda i: (
            next((j for j, tag in enumerate(decal_order) if tag in i.progression.levels[1]['conditions'][0]['path'][1]), 100),
            i.id
        )))]


@overrideMethod(CarouselDataProvider, '_vehicleComparisonKey')
def _vehicleComparisonKey(base, cls, vehicle, *args, **kwargs):
    if not (
            g_config.data['enabled'] and g_config.data['sort_vehicleCarousel']
            and issubclass(cls, HangarCarouselDataProvider)):
        if getattr(base, '__func__', None) is None:  # idiot-proof
            return base(vehicle, *args, **kwargs)
        return base.__func__(cls, vehicle, *args, **kwargs)
    return (
        not vehicle.isInInventory,
        vehicle.isOnlyForClanWarsBattles,
        not vehicle.isEvent,
        not vehicle.isOnlyForBattleRoyaleBattles,
        -vehicle.level,
        vehicle.isPremium,
        not vehicle.isFavorite,
        GUI_NATIONS_ORDER_INDEX[vehicle.nationName],
        VEHICLE_TYPES_ORDER_INDICES[vehicle.type],
        tuple(vehicle.buyPrices.itemPrice.price.iterallitems(byWeight=True)),
        vehicle.userName)


@overrideMethod(TankCarouselFilterPopover, '_generateMapping')
def new_generateMapping(base, _, *a, **k):
    mapping = base(*a, **k)
    if not g_config.data['enabled']:
        return mapping
    if g_config.data['filter_vehicleCarousel_normal']:
        mapping[FILTER_SECTION.SPECIALS].insert(2, 'normal')
    if g_config.data['filter_vehicleCarousel_alliance']:
        mapping[FILTER_SECTION.NATIONS] += nations.ALLIANCES_TAGS_ORDER
    return mapping


@overrideMethod(TankCarouselFilterPopover, '_update')
def new_update(base, self, isInitial=False, *a, **k):
    base(self, isInitial, *a, **k)
    if (g_config.data['enabled']
            and (g_config.data['filter_vehicleCarousel_normal'] or g_config.data['filter_vehicleCarousel_alliance'])
            and not isInitial):
        filters = self._carousel.filter.getFilters(self._VehiclesFilterPopover__usedFilters)
        xpRateMultiplier = self.itemsCache.items.shop.dailyXPFactor
        self._withRoles = self._carousel.hasRoles()
        self.as_setInitDataS(self._getInitialVO(filters, xpRateMultiplier))


@overrideMethod(TankCarouselFilterPopover, '_getInitialVO')
def new_getInitialVO(base, self, filters, *a, **k):
    dataVO = base(self, filters, *a, **k)
    if not g_config.data['enabled']:
        return dataVO
    if g_config.data['filter_vehicleCarousel_normal']:
        dataVO['specials'][2] = {
            'value': getButtonsAssetPath('XpIcon'),
            'tooltip': makeTooltip(backport.text(R.strings.menu.shop.menu.module.extra.locked.name())),
            'selected': not filters['elite'] and not filters['premium'] and filters.get('normal', False),
            'enabled': not filters['elite'] and not filters['premium']}
    if g_config.data['filter_vehicleCarousel_alliance']:
        for idx, alliance_orig in enumerate(reversed(nations.ALLIANCES_TAGS_ORDER)):
            alliance = alliance_orig.replace('-', '_')
            dataVO['nations'][-(idx + 1)] = {
                'value': RES_ICONS.getAlliance17x19Icon(alliance_orig),
                'tooltip': makeTooltip(
                    backport.text(
                        R.strings.tooltips.blueprints.conversionView.title()).replace(
                        '%(allianceIcon)', icons.makeImageTag(
                            backport.image(R.images.gui.maps.icons.blueprints.fragment.conversion.dyn(alliance)()))).replace(
                        '%(allianceName)', text_styles.stats(
                            backport.text(R.strings.tooltips.blueprints.conversionView.alliance.title.name.dyn(alliance)()))),
                    backport.text(
                        R.strings.tooltips.blueprints.conversionView.subTitle()).replace(
                        '%(allianceNations)', text_styles.stats(
                            backport.text(R.strings.tooltips.blueprints.conversionView.alliance.nations.dyn(alliance)())))
                ),
                'selected': not any(filters[nation] for nation in nations.NAMES) and filters.get(alliance_orig, False),
                'enabled': not any(filters[nation] for nation in nations.NAMES)}
    return dataVO


@overrideMethod(BasicCriteriesGroup, 'update')
def new_update(base, self, filters, *a, **k):
    base(self, filters, *a, **k)
    if not g_config.data['enabled']:
        return
    if g_config.data['filter_vehicleCarousel_normal']:
        if not filters['elite'] and not filters['premium'] and filters.get('normal', False):
            self._criteria |= ~REQ_CRITERIA.VEHICLE.ELITE
    if g_config.data['filter_vehicleCarousel_alliance']:
        if not any(filters[nation] for nation in nations.NAMES):
            selectedNationsIds = []
            for alliance, allianceId in nations.ALLIANCE_IDS.iteritems():
                if filters.get(alliance, False):
                    selectedNationsIds.extend(nations.ALLIANCE_IDS_MAP[allianceId])
            if selectedNationsIds:
                self._criteria |= REQ_CRITERIA.NATIONS(selectedNationsIds)


@overrideMethod(Vehicle, 'isFullyElite')
def new_isFullyElite(base, self, *args, **kwargs):
    return (base(self, *args, **kwargs)
            and (not self.postProgressionAvailability(True).result
                 or self.postProgression.getCompletion() == PostProgressionCompletion.FULL))
