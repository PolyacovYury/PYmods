from CurrentVehicle import g_currentVehicle
from PYmodsCore import overrideMethod
from gui.Scaleform.daapi.view.lobby.customization.customization_cm_handlers import CustomizationItemCMHandler as WGCMHandler
from gui.Scaleform.genConsts.SEASONS_CONSTANTS import SEASONS_CONSTANTS
from gui.impl.backport import text
from gui.impl.gen import R
from gui.shared.gui_items import GUI_ITEM_TYPE
from .. import g_config


class Options(object):
    MODE_GROUP = 'selectionMode_group'
    MODE_OFF = 'selectionMode_off'
    MODE_RANDOM = 'selectionMode_random'
    MODE_TEAM = 'selectionMode_team'
    MODE_CHANGE = 'selectionMode_change'
    SEASON_GROUP = 'season_group'
    SEASON_SUMMER = 'season_summer'
    SEASON_WINTER = 'season_winter'
    SEASON_DESERT = 'season_desert'
    TEAM_GROUP = 'team_group'
    TEAM_ALLY = 'team_ally'
    TEAM_ENEMY = 'team_enemy'
    REMOVE_FROM_OTHER = 'removeFromOther'
    MODE = (MODE_OFF, MODE_RANDOM, MODE_TEAM)
    SEASON = (SEASON_SUMMER, SEASON_WINTER, SEASON_DESERT)
    TEAM = (TEAM_ALLY, TEAM_ENEMY)
    ALL = MODE + SEASON + TEAM


class CustomizationItemCMHandler(WGCMHandler):
    def _generateOptions(self, ctx=None):
        if self.__ctx.isPurchase:
            return WGCMHandler._generateOptions(self, ctx) + self.__getRemoveFromOtherVehicles()
        result = []
        if self._item.itemTypeID == GUI_ITEM_TYPE.STYLE:
            result += self.__separateItem(self.__getStyleInfoBtn(self._item))
        result.append(self.__getRemoveBtn(self._item))
        if self._item.itemTypeID != GUI_ITEM_TYPE.CAMOUFLAGE:
            return result
        getOptionLabel = lambda option: g_config.i18n['contextMenu_' + option]
        getOptionData = lambda option, remove=False, enabled=True: (
            option, getOptionLabel(option + ('_remove' if remove else '')), {'enabled': enabled})
        setting = self.__ctx.mode.getItemSettings(self._item)
        getSeasonOptionData = lambda option, s: getOptionData(
            option, s in setting['season'], len(setting['season']) != 1 or s not in setting['season'])
        getTeamOptionData = lambda option, remove=False: getOptionData(option, remove, setting['random_enabled'])
        active_mode_idx = setting['random_enabled'] and (setting['random_enabled'] + setting['random_team'])
        modeSubs, modeLabel = [], ''
        for idx, _option in enumerate(Options.MODE):
            if idx != active_mode_idx:
                modeSubs.append(self._makeItem(_option, getOptionLabel(Options.MODE_CHANGE) + getOptionLabel(_option)))
            else:
                modeLabel = getOptionLabel(_option)
        result += (
            self._makeItem(*getOptionData(Options.SEASON_GROUP), optSubMenu=[
                self._makeItem(*getSeasonOptionData(Options.SEASON_SUMMER, SEASONS_CONSTANTS.SUMMER)),
                self._makeItem(*getSeasonOptionData(Options.SEASON_WINTER, SEASONS_CONSTANTS.WINTER)),
                self._makeItem(*getSeasonOptionData(Options.SEASON_DESERT, SEASONS_CONSTANTS.DESERT)),
            ]),
            self._makeSeparator(),
            self._makeItem(*getTeamOptionData(Options.TEAM_GROUP), optSubMenu=[
                self._makeItem(*getTeamOptionData(Options.TEAM_ALLY, setting['ally'])),
                self._makeItem(*getTeamOptionData(Options.TEAM_ENEMY, setting['enemy'])),
            ]),
            self._makeSeparator(),
            self._makeItem(Options.MODE_GROUP, getOptionLabel(Options.MODE_GROUP) + modeLabel, optSubMenu=modeSubs),
        )
        return result

    def __getRemoveFromOtherVehicles(self):  # mostly stolen from tooltips code
        if self._item.isStyleOnly:
            return []
        appliedCount = 0
        vehicle = g_currentVehicle.item
        if self._item.itemTypeID != GUI_ITEM_TYPE.STYLE:
            appliedCount = self.__ctx.mode.getItemAppliedCount(self._item)
        elif vehicle is not None:
            currentStyleDesc = self.__ctx.mode.currentOutfit.style
            isApplied = currentStyleDesc is not None and self._item.id == currentStyleDesc.id
            appliedCount = int(isApplied)
        vehicles = {
            vehicleCD: self.itemsCache.items.getItemByCD(vehicleCD).shortUserName
            for vehicleCD in set(self._item.getInstalledVehicles())}
        item_filter = self._item.descriptor.filter
        if (self._item.mayApply or appliedCount > 0 or not vehicles or vehicle.intCD in vehicles
                or item_filter is not None and not item_filter.match(vehicle.descriptor)):
            return []
        groupLabel = text(R.strings.vehicle_customization.propertySheet.actionBtn.clear())
        if len(vehicles) == 1:
            vehicleCD, vehName = vehicles.popitem()
            return self.__separateItem(self._makeItem(
                Options.REMOVE_FROM_OTHER + '_' + str(vehicleCD), groupLabel + ' ' + vehName))[::-1]
        return self.__separateItem(self._makeItem(Options.REMOVE_FROM_OTHER, groupLabel, optSubMenu=[
            self._makeItem(Options.REMOVE_FROM_OTHER + '_' + str(vehicleCD), vehName)
            for vehicleCD, vehName in sorted(vehicles, key=lambda x: x[1])
        ]))[::-1]

    def onOptionSelect(self, optionId):
        if optionId.startswith(Options.REMOVE_FROM_OTHER):
            return self.__ctx.removeFromOtherVehicle(int(optionId.split('_')[1]), self._item)
        if optionId not in Options.ALL:
            return WGCMHandler.onOptionSelect(self, optionId)
        settings = self.__ctx.mode.getItemSettings(self._item)
        value = optionId.split('_')[1]
        if optionId in Options.SEASON:
            seasons = settings['season']
            if value not in seasons:
                seasons.append(value)
            else:
                seasons.remove(value)
        elif optionId in Options.MODE:
            idx = Options.MODE.index(optionId)
            settings['random_enabled'] = idx > 0
            settings['random_team'] = idx == 2
        elif optionId in Options.TEAM:
            settings[value] = not settings[value]
        self.__ctx.events.onCacheResync()


@overrideMethod(WGCMHandler, '__new__')
def new(base, cls, *a, **kw):
    if not g_config.data['enabled']:
        return base(cls, *a, **kw)
    return base(CustomizationItemCMHandler, *a, **kw)
