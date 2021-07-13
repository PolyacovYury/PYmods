from gui import SystemMessages
from gui.Scaleform.genConsts.SEASONS_CONSTANTS import SEASONS_CONSTANTS
from gui.SystemMessages import SM_TYPE
from items.components.c11n_constants import CustomizationType, SeasonType
from items.vehicles import g_cache, makeIntCompactDescrByID
from ... import g_config
from ...constants import SEASON_NAME_TO_TYPE


class ItemSettingsRemap(object):
    def __init__(self):
        self._currentSettings = {'custom': {}, 'remap': {}}

    def getItemSettings(self, item):
        itemsKey, itemKey = g_config.getItemKeys(item.id, item.descriptor)
        origSettings = g_config.getCamoSettings(itemsKey, itemKey)
        settings = self._currentSettings[itemsKey].setdefault(itemKey, {})
        settings.setdefault('season', [i for i in origSettings.get('season', [])] or [
            x for x in SEASONS_CONSTANTS.SEASONS if SEASON_NAME_TO_TYPE[x] & item.season])
        for key, default_value in g_config.defaults.items():
            settings.setdefault(key, origSettings.get(key, default_value))
        settings.setdefault('id', item.id)
        return settings

    def _cleanSettings(self):
        camouflages = g_cache.customization20().camouflages
        for itemsKey, data in self._currentSettings.iteritems():
            for itemKey, settings in data.items():
                orig = g_config.getCamoSettings(itemsKey, itemKey)
                if 'season' in settings:
                    if 'season' in orig:
                        if orig['season'] == settings['season']:
                            del settings['season']
                    elif set(s for s in SeasonType.COMMON_SEASONS if camouflages[settings['id']].season & s) == set(
                            SEASON_NAME_TO_TYPE[x] for x in settings['season']):
                        del settings['season']
                for key, default_value in g_config.defaults.items():
                    if key in settings and orig.get(key, default_value) == settings[key]:
                        del settings[key]
                if settings.keys() in ([], ['id']):
                    del data[itemKey]

    def applySettings(self):
        self._cleanSettings()
        g_config.applyCamoSettings(self._currentSettings)
        if any(self._currentSettings.itervalues()):
            g_config.collectCamouflageData()
            SystemMessages.pushI18nMessage(g_config.i18n['flashCol_serviceMessage_settings'], type=SM_TYPE.Information)

    def isOutfitsModified(self):
        self._cleanSettings()
        return any(self._currentSettings.itervalues())

    def cancelChanges(self):
        self._currentSettings = {'custom': {}, 'remap': {}}

    def getChangedItemData(self):
        self._cleanSettings()
        result = {}
        camouflages = g_cache.customization20().camouflages
        for itemsKey, data in self._currentSettings.iteritems():
            for itemKey, settings in data.items():
                intCD = makeIntCompactDescrByID('customizationItem', CustomizationType.CAMOUFLAGE, settings['id'])
                result[intCD] = len(settings) - 1
                orig = g_config.getCamoSettings(itemsKey, itemKey)
                if 'season' not in settings:
                    continue
                result[intCD] -= 1
                if 'season' in orig:
                    result[intCD] += len(set(orig['season']).symmetric_difference(settings['season']))
                else:
                    result[intCD] += len(set(
                        season for season in SeasonType.COMMON_SEASONS if camouflages[settings['id']].season & season
                    ).symmetric_difference(SEASON_NAME_TO_TYPE[x] for x in settings['season']))
        return result

    def rollbackSettings(self, item):
        itemsKey, itemKey = g_config.getItemKeys(item.id, item.descriptor)
        self._currentSettings[itemsKey].pop(itemKey, {})
