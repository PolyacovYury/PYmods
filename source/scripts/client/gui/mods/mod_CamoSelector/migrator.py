import os
from PYmodsCore import loadJson
from gui.Scaleform.genConsts.SEASONS_CONSTANTS import SEASONS_CONSTANTS
from gui.shared.gui_items import GUI_ITEM_TYPE, GUI_ITEM_TYPE_NAMES
from helpers import dependency
from items.components.c11n_constants import EMPTY_ITEM_ID, SeasonType
from items.vehicles import g_cache
from skeletons.gui.shared.gui_items import IGuiItemsFactory
from .constants import SEASON_NAME_TO_TYPE


class SelectionMode(object):
    ALL = OFF, TEAM, RANDOM = range(3)


def migrateSettings(self, camoData):
    migrateOutfitsCache(self)
    migrateRemapSettings(self, camoData)


def migrateOutfitsCache(self):
    outfitCache = loadJson(self.ID, 'outfitCache', {}, self.configPath)
    if os.path.isfile(self.configPath + 'camouflagesCache.json'):
        camouflagesCache = loadJson(self.ID, 'camouflagesCache', {}, self.configPath)
        for nat in camouflagesCache:
            for vehName in camouflagesCache[nat]:
                for season in camouflagesCache[nat][vehName]:
                    outfitCache.setdefault(nat, {}).setdefault(vehName, {}).setdefault(season, {})[
                        GUI_ITEM_TYPE_NAMES[GUI_ITEM_TYPE.CAMOUFLAGE]] = camouflagesCache[nat][vehName][season]
        os.remove(self.configPath + 'camouflagesCache.json')
    for nat in outfitCache.values():
        for veh in nat.values():
            for season in veh.values():
                if 'intCD' in season:  # style ID
                    style_id = dependency.instance(IGuiItemsFactory).createCustomization(
                        season['intCD']).id if season['intCD'] and season['applied'] else EMPTY_ITEM_ID
                    for seasonName in SEASON_NAME_TO_TYPE:
                        _season = veh.setdefault(seasonName, {})
                        _season.setdefault('style', {})
                        _season['style']['id'] = style_id
                        if 'level' in season:
                            _season['style']['progressionLevel'] = season['level']
                    season.clear()
                if 'camo' in season:
                    season[GUI_ITEM_TYPE_NAMES[GUI_ITEM_TYPE.CAMOUFLAGE]] = season.pop('camo')
                for typeName, typeData in season.items():
                    if typeName == GUI_ITEM_TYPE_NAMES[GUI_ITEM_TYPE.CAMOUFLAGE]:
                        for part, partData in typeData.items():
                            if not isinstance(partData, list):
                                continue
                            typeData[part] = {}
                            if not partData:
                                typeData[part]['0'] = {'id': None}
                            else:
                                typeData[part]['0'] = {k: v for k, v in zip(('id', 'palette', 'patternSize'), partData)}
                    elif typeName != 'style':
                        for partData in typeData.values():
                            for region in partData:
                                if partData[region] is None:
                                    partData[region] = {'id': None}
                    elif 'level' in typeData:
                        typeData['progressionLevel'] = typeData.pop('level')
    loadJson(self.ID, 'outfitCache', outfitCache, self.configPath, True)


def migrateRemapSettings(self, camoData):
    camouflages = g_cache.customization20().camouflages
    settings = loadJson(self.ID, 'settings', {}, self.configPath)
    settings.setdefault('disable', self.disabledVehicles)
    conf = settings.setdefault('remap', {})
    for camoName in conf.keys():
        camoConf = conf.pop(camoName)
        try:
            camoID = int(camoName)
        except ValueError:
            if camoName not in camoData:
                print self.LOG, 'unknown camouflage for remapping:', camoName
                continue
            for newID in camoData[camoName]['ids']:
                newConf = migrateCamoConf(self, newID, camoConf.copy(), camouflages, True)
                if newConf:
                    conf[newID] = newConf
            continue
        if camoID not in camouflages:
            print self.LOG, 'unknown camouflage for remapping:', camoName
            continue
        newConf = migrateCamoConf(self, camoID, camoConf, camouflages, True)
        if newConf:
            conf[camoID] = newConf
    loadJson(self.ID, 'settings', settings, self.configPath, True)


def migrateCamoConf(self, camoID, camoConf, camouflages, clean):
    random_mode = camoConf.pop('random_mode', SelectionMode.RANDOM)
    if random_mode == SelectionMode.OFF:
        camoConf['random_enabled'] = False
    elif random_mode == SelectionMode.TEAM:
        camoConf['random_team'] = True
    migrateSeasons(self, camoID, camoConf, camouflages[camoID].season)
    migrateTeams(camoConf)
    if not clean:
        return camoConf
    for name, default_value in self.defaults.items():
        if name == 'season':
            continue
        if camoConf.get(name, default_value) == default_value:
            camoConf.pop(name, None)
    return camoConf


def migrateSeasons(self, key, conf, itemSeason=None):
    if 'kinds' in conf:
        conf['season'] = conf.pop('kinds')
    if 'season' not in conf:
        if itemSeason is None:
            conf['season'] = SEASONS_CONSTANTS.SEASONS[:]
        else:
            return
    elif isinstance(conf['season'], basestring):
        conf['season'] = [x for x in conf['season'].split(',') if x]
    actualSeason = SeasonType.UNDEFINED
    for season in conf['season']:
        if season not in SEASON_NAME_TO_TYPE:
            print self.LOG, 'unknown season name for camouflage', key + ':', season
            conf['season'].remove(season)
        else:
            actualSeason |= SEASON_NAME_TO_TYPE[season]
    if itemSeason is not None and itemSeason & ~SeasonType.EVENT == actualSeason:
        del conf['season']


def migrateTeams(conf):
    for key in conf.keys():
        if 'useFor' in key:
            conf[key.replace('useFor', '').lower()] = conf.pop(key)
