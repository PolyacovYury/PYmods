import operator

from PYmodsCore import loadJson
from gui import SystemMessages
from gui.Scaleform.genConsts.SEASONS_CONSTANTS import SEASONS_CONSTANTS
from gui.SystemMessages import SM_TYPE
from items.components.c11n_constants import SeasonType
from items.vehicles import g_cache
from ... import g_config
from ...constants import SEASON_NAME_TO_TYPE, SelectionMode


class CSModImpl(object):
    def __init__(self):
        self._currentSettings = {'custom': {}, 'remap': {}}

    def getItemSettings(self, item):
        name, key = (item.descriptor.userKey, 'custom') if item.priceGroup == 'custom' else (item.id, 'remap')
        settings = self._currentSettings[key].setdefault(name, {})
        origSettings = g_config.camouflages[key].get(name, {})
        settings.setdefault('season', origSettings.get('season', []) or [
            x for x in SEASONS_CONSTANTS.SEASONS if SEASON_NAME_TO_TYPE[x] & item.season])
        settings.setdefault('random_mode', origSettings.get('random_mode', SelectionMode.RANDOM))
        settings.setdefault('ally', origSettings.get('ally', True))
        settings.setdefault('enemy', origSettings.get('enemy', True))
        return settings

    def isOutfitsModified(self):
        self._cleanSettings()
        return any(self._currentSettings.itervalues())

    def cancelChanges(self):
        self._currentSettings = {'custom': {}, 'remap': {}}

    def _cleanSettings(self):
        camouflages = g_cache.customization20().camouflages
        for key, settings in self._currentSettings.iteritems():
            for ID, conf in settings.items():
                orig = g_config.camouflages[key].get(ID, {})
                if 'season' in conf and (
                        camouflages[ID].season & ~SeasonType.EVENT == reduce(
                            operator.ior, (SEASON_NAME_TO_TYPE[x] for x in conf['season']), SeasonType.UNDEFINED)
                        if 'season' not in orig else orig['season'] == conf['season']):
                    del conf['season']
                for team in ('ally', 'enemy'):
                    if team in conf and orig.get(team, True) == conf[team]:
                        del conf[team]
                if 'random_mode' in conf and conf['random_mode'] == orig.get('random_mode', SelectionMode.RANDOM):
                    del conf['random_mode']
                if not conf:
                    del settings[ID]

    def applySettings(self):
        self._cleanSettings()
        for itemsKey in self._currentSettings:
            for camoName in self._currentSettings[itemsKey]:
                g_config.camouflages[itemsKey].setdefault(camoName, {}).update(self._currentSettings[itemsKey][camoName])
        if self._currentSettings['remap']:
            newSettings = {'disable': g_config.disable, 'remap': g_config.camouflages['remap']}
            loadJson(g_config.ID, 'settings', newSettings, g_config.configPath, True)
        if self._currentSettings['custom']:
            for confFolderName in g_config.configFolders:
                configFolder = g_config.configFolders[confFolderName]
                loadJson(g_config.ID, 'settings', {key: g_config.camouflages['custom'][key] for key in configFolder},
                         g_config.configPath + 'camouflages/' + confFolderName + '/', True, False)
        if any(self._currentSettings.itervalues()):
            g_config.collectCamouflageData()
            SystemMessages.pushI18nMessage(g_config.i18n['flashCol_serviceMessage_settings'], type=SM_TYPE.Information)
