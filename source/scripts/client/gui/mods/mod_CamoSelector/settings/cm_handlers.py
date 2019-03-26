from PYmodsCore import overrideMethod
from gui.Scaleform.daapi.view.lobby.customization import CustomizationItemCMHandler as WGCMHandler
from gui.Scaleform.genConsts.SEASONS_CONSTANTS import SEASONS_CONSTANTS
from .. import g_config
from ..constants import SelectionMode as SM


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
    MODE = (MODE_OFF, MODE_TEAM, MODE_RANDOM)
    SEASON = (SEASON_SUMMER, SEASON_WINTER, SEASON_DESERT)
    TEAM = (TEAM_ALLY, TEAM_ENEMY)


class CustomizationItemCMHandler(WGCMHandler):
    def _generateOptions(self, ctx=None):
        result = super(CustomizationItemCMHandler, self)._generateOptions(ctx)
        if self.__ctx.isBuy:
            return result
        result = result[-1:]
        settings = self.__ctx.getItemSettings(self.itemsCache.items.getItemByCD(self._intCD))
        selectionMode = settings['random_mode']
        getOptLabel = lambda option: g_config.i18n['contextMenu_' + option]
        getOptData = lambda option, condition=False: (option, getOptLabel(option + ('_remove' if condition else '')))
        getSeasonOptData = lambda option, season: getOptData(option, season in settings['season']) + (
            {'enabled': not (len(settings['season']) == 1 and season in settings['season'])},)
        getTeamData = lambda option, condition=False: getOptData(option, condition) + ({'enabled': selectionMode != SM.OFF},)
        sub = []
        modeLabel = ''
        for mode, opt in zip(SM.ALL, Options.MODE):
            if selectionMode != mode:
                sub.append(self._makeItem(opt, getOptLabel(Options.MODE_CHANGE) + getOptLabel(opt)))
            else:
                modeLabel = getOptLabel(opt)
        result += (
            self._makeItem(*getOptData(Options.SEASON_GROUP), optSubMenu=[
                self._makeItem(*getSeasonOptData(Options.SEASON_SUMMER, SEASONS_CONSTANTS.SUMMER)),
                self._makeItem(*getSeasonOptData(Options.SEASON_WINTER, SEASONS_CONSTANTS.WINTER)),
                self._makeItem(*getSeasonOptData(Options.SEASON_DESERT, SEASONS_CONSTANTS.DESERT))]),
            self._makeItem(Options.MODE_GROUP, getOptLabel(Options.MODE_GROUP) + modeLabel, optSubMenu=sub),
            self._makeItem(*getTeamData(Options.TEAM_GROUP), optSubMenu=[
                self._makeItem(*getTeamData(Options.TEAM_ALLY, settings['ally'])),
                self._makeItem(*getTeamData(Options.TEAM_ENEMY, settings['enemy']))]))
        return result

    def onOptionSelect(self, optionId):
        if optionId not in Options:
            return super(CustomizationItemCMHandler, self).onOptionSelect(optionId)
        settings = self.__ctx.getItemSettings(self.itemsCache.items.getItemByCD(self._intCD))
        value = optionId.split('_')[1]
        if optionId in Options.SEASON:
            seasons = settings['season']
            if value not in seasons:
                seasons.append(value)
            else:
                seasons.remove(value)
        elif optionId in Options.MODE:
            settings['random_mode'] = getattr(SM, value.upper())
        elif optionId in Options.TEAM:
            settings[value] = not settings[value]
        self.__ctx.onCacheResync()


@overrideMethod(WGCMHandler, '__new__')
def new(base, cls, *a, **kw):
    if not g_config.data['enabled']:
        return base(cls, *a, **kw)
    return base(CustomizationItemCMHandler, *a, **kw)
