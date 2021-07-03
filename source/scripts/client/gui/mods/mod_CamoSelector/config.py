# coding=utf-8
import ResMgr
import items.vehicles
import nations
import os
from CurrentVehicle import g_currentVehicle
from PYmodsCore import Analytics, PYmodsConfigInterface, loadJson, refreshCurrentVehicle, remDups
from gui.Scaleform.genConsts.SEASONS_CONSTANTS import SEASONS_CONSTANTS
from gui.shared.gui_items import GUI_ITEM_TYPE, GUI_ITEM_TYPE_NAMES
from helpers import dependency
from items.components.c11n_constants import EMPTY_ITEM_ID, SeasonType
from skeletons.gui.shared.gui_items import IGuiItemsFactory
from . import __date__, __modID__
from .constants import SEASON_NAME_TO_TYPE, SelectionMode


class ConfigInterface(PYmodsConfigInterface):
    def __init__(self):
        self.disable = []
        self.camoForSeason = {}
        self.arenaCamoCache = {}
        self.hangarCamoCache = {}
        self.outfitCache = {}
        self.camouflages = {}
        self.configFolders = {}
        self.teamCamo = dict.fromkeys(('ally', 'enemy'))
        self.internationalCamoIDs = []
        self.isModAdded = False
        super(ConfigInterface, self).__init__()

    def init(self):
        self.ID = __modID__
        self.version = '3.0.0 (%s)' % __date__
        self.author += ' (thx to tratatank, Blither!)'
        self.data = {
            'enabled': True, 'doRandom': True, 'useBought': True, 'hangarCamoKind': 0, 'fullAlpha': False,
            'disableWithDefault': False, 'fillEmptySlots': True, 'uniformOutfit': False}
        self.i18n = {
            'UI_description': 'Camouflage selector',
            'flash_switcher_buy': 'PURCHASE',
            'flash_switcher_install': 'INSTALL',
            'flashCol_progressionDecal_changeMode_title': 'Mode change',
            'flashCol_progressionDecal_changeMode_message': (
                'Current style can not be edited.\n'
                'If you proceed, you will be moved to custom mode\'s decal tab.\nDo you want to continue?'),
            'flash_propertySheet_edit_button': 'DISASSEMBLE STYLE',
            'flashCol_propertySheet_edit_title': 'Style disassembly',
            'flashCol_propertySheet_edit_disabled': '3D styles can not be disassembled.',
            'flashCol_propertySheet_edit_message': (
                '<b>All</b> installed items will be removed from <b>ALL</b> seasons.\nAre you sure you want to continue?'),
            'flashCol_propertySheet_edit_tooltip': (
                'This action will replace custom outfits for <b>ALL</b> seasons.\n<b>All</b> items will be removed. '
                'You <b>will</b> be able to cancel these changes.'),
            'flashCol_group_multinational': 'Multinational',
            'flashCol_group_custom': 'Custom',
            'flashCol_group_separator': ' / ',
            'flashCol_serviceMessage_settings': 'Customization element settings changed.',
            'contextMenu_season_summer': 'Apply for summer',
            'contextMenu_season_summer_remove': 'Remove from summer',
            'contextMenu_season_winter': 'Apply for winter',
            'contextMenu_season_winter_remove': 'Remove from winter',
            'contextMenu_season_desert': 'Apply for desert',
            'contextMenu_season_desert_remove': 'Remove from desert',
            'contextMenu_selectionMode_group': 'Current selection mode: ',
            'contextMenu_selectionMode_change': 'Change to ',
            'contextMenu_selectionMode_off': 'Disabled',
            'contextMenu_selectionMode_random': 'Random',
            'contextMenu_selectionMode_team': 'Team',
            'contextMenu_team_ally': 'Apply for allies',
            'contextMenu_team_ally_remove': 'Remove from allies',
            'contextMenu_team_enemy': 'Apply for enemies',
            'contextMenu_team_enemy_remove': 'Remove from enemies',
            'UI_setting_doRandom_text': 'Select random camouflages',
            'UI_setting_doRandom_tooltip': (
                'If enabled, mod will select a random available camouflage if no other option is provided.'),
            'UI_setting_useBought_text': 'Use bought camouflages in battle',
            'UI_setting_useBought_tooltip': "If enabled, mod will preserve bought camouflages on other players' tanks.",
            'UI_setting_disableWithDefault_text': 'Disable for vehicles with default camouflage',
            'UI_setting_disableWithDefault_tooltip': 'If enabled, mod will ignore vehicles with a default camouflage.',
            'UI_setting_fullAlpha_text': 'Non-transparent custom camouflages',
            'UI_setting_fullAlpha_tooltip': 'If enabled, all custom camouflages lose their transparency.\n'
                                            'Some call this "dirt-less skins".',
            'UI_setting_fillEmptySlots_text': 'Fill empty slots',
            'UI_setting_fillEmptySlots_tooltip': 'Add random camouflages if a vehicle has empty slots for them.',
            'UI_setting_uniformOutfit_text': 'Same look for all parts',
            'UI_setting_uniformOutfit_tooltip':
                'Random camouflages are picked up so that a vehicle has the same camouflage on all parts (if possible).',
            'UI_setting_hangarCamoKind_text': 'Hangar camouflage season',
            'UI_setting_hangarCamoKind_tooltip': 'This setting controls the season which is used in hangar.',
            'UI_setting_hangarCamo_winter': 'Winter', 'UI_setting_hangarCamo_summer': 'Summer',
            'UI_setting_hangarCamo_desert': 'Desert', 'UI_setting_hangarCamo_random': 'Random'}
        super(ConfigInterface, self).init()

    def loadLang(self):
        super(ConfigInterface, self).loadLang()
        try:
            from helpers.i18n.hangarpainter import _config
            for key in self.i18n:
                if not key.startswith('flashCol_'):
                    continue
                self.i18n[key] = "<font color='#%s'>%s</font>" % (_config.data['colour'], self.i18n[key])
        except ImportError:
            pass

    def createTemplate(self):
        return {
            'modDisplayName': self.i18n['UI_description'], 'enabled': self.data['enabled'],
            'column1': [
                self.tb.createOptions('hangarCamoKind', [
                    self.i18n['UI_setting_hangarCamo_' + x] for x in ('winter', 'summer', 'desert', 'random')]),
                self.tb.createControl('doRandom'),
                self.tb.createControl('disableWithDefault'),
            ],
            'column2': [
                self.tb.createControl('fillEmptySlots'),
                self.tb.createControl('uniformOutfit'),
                self.tb.createControl('useBought'),
                self.tb.createControl('fullAlpha'),
            ]}

    def onMSADestroy(self):
        try:
            from gui.mods import mod_remodenabler
        except ImportError:
            refreshCurrentVehicle()

    def onApplySettings(self, settings):
        if 'fullAlpha' in settings and settings['fullAlpha'] != self.data['fullAlpha']:
            items.vehicles.g_cache._Cache__customization20 = None
            items.vehicles.g_cache.customization20()
        super(ConfigInterface, self).onApplySettings(settings)
        self.hangarCamoCache.clear()

    def readCurrentSettings(self, quiet=True):
        self.configFolders.clear()
        self.camouflages = {'remap': {}, 'custom': {}}
        self.outfitCache = loadJson(self.ID, 'outfitCache', self.outfitCache, self.configPath)
        self.readConfigDir(quiet, recursive=True, dir_name='camouflages')
        settings = loadJson(self.ID, 'settings', {}, self.configPath)
        self.disable = settings.setdefault('disable', self.disable)
        self.camouflages['remap'] = {int(k): v for k, v in settings.setdefault('remap', {}).iteritems()}
        loadJson(self.ID, 'settings', settings, self.configPath, True)

    def onReadConfig(self, quiet, dir_path, name, json_data, sub_dirs, names):
        if name != 'settings':
            return
        self.configFolders[dir_path] = set(json_data)
        self.camouflages['custom'].update(json_data)

    def migrateConfigs(self):
        camouflages = items.vehicles.g_cache.customization20().camouflages
        camoData = {}
        for camoID, x in camouflages.iteritems():
            data = camoData.setdefault(os.path.splitext(os.path.basename(x.texture))[0], {'ids': [], 'nations': []})
            data['ids'].append(camoID)
            for filterNode in getattr(camouflages[camoID].filter, 'include', ()):
                data['nations'] += filterNode.nations or []
        for data in camoData.itervalues():
            if set(data['nations']) >= set(idx for idx, name in enumerate(nations.NAMES) if name != 'italy'):
                self.internationalCamoIDs += data['ids']
        self.migrateSettings(camoData)

    def migrateSettings(self, camoData):
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
                        if season['applied']:
                            for seasonName in SEASON_NAME_TO_TYPE:
                                _season = veh.setdefault(seasonName, {})
                                _season.setdefault('style', {})
                                _season['style']['id'] = dependency.instance(IGuiItemsFactory).createCustomization(
                                    season['intCD']).id if season['intCD'] else EMPTY_ITEM_ID
                                if 'level' in season:
                                    _season['style']['level'] = season['level']
                        season.clear()
                    if 'camo' in season:
                        season[GUI_ITEM_TYPE_NAMES[GUI_ITEM_TYPE.CAMOUFLAGE]] = season.pop('camo')
                    for typeName, tc in season.items():
                        if typeName == GUI_ITEM_TYPE_NAMES[GUI_ITEM_TYPE.CAMOUFLAGE]:
                            for part in tc:
                                if not isinstance(tc[part], list):
                                    continue
                                if not tc[part]:
                                    tc[part] = {'0': {'id': None}}
                                else:
                                    tc[part] = {'0': {k: v for k, v in zip(('id', 'palette', 'patternSize'), tc[part])}}
                        elif typeName != 'style':
                            for part in tc:
                                for region in tc[part]:
                                    if tc[part][region] is None:
                                        tc[part][region] = {'id': None}
        loadJson(self.ID, 'outfitCache', outfitCache, self.configPath, True)
        camoDirPath = '../' + self.configPath + 'camouflages'
        camoDirKeys = getattr(ResMgr.openSection(camoDirPath), 'keys', lambda: [])()
        for camoID in remDups(x for x in camoDirKeys if ResMgr.isDir(camoDirPath + '/' + x)):
            fileName = self.configPath + 'camouflages/' + camoID + '/'
            settings = loadJson(self.ID, 'settings', {}, fileName)
            for key in settings:
                self.migrateSeasons(key, settings[key])
                self.migrateTeams(settings[key])
            loadJson(self.ID, 'settings', settings, fileName, True)
        camouflages = items.vehicles.g_cache.customization20().camouflages
        settings = loadJson(self.ID, 'settings', {}, self.configPath)
        settings.setdefault('disable', self.disable)
        conf = settings.setdefault('remap', {})
        for camoName in conf.keys():
            try:
                camoID = int(camoName)
            except ValueError:
                if camoName not in camoData:
                    print self.ID + ': unknown camouflage for remapping:', camoName
                else:
                    for newID in camoData[camoName]['ids']:
                        conf[newID] = conf[camoName].copy()
                del conf[camoName]
                continue
            if camoID not in camouflages:
                print self.ID + ': unknown camouflage for remapping:', camoName
                del conf[camoName]
            else:
                conf[camoID] = conf.pop(camoName)
        for camoID, camouflage in camouflages.items():
            if camoID not in conf:
                continue
            camoConf = conf[camoID]
            if camoConf.get('random_mode') == SelectionMode.RANDOM:
                del camoConf['random_mode']
            self.migrateSeasons(camoID, camoConf, camouflage.season)
            self.migrateTeams(camoConf)
            for team in ('ally', 'enemy'):
                if camoConf.get(team):
                    del camoConf[team]
            if not camoConf:
                del conf[camoID]
        loadJson(self.ID, 'settings', settings, self.configPath, True)

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
                print self.ID + ': unknown season name for camouflage', key + ':', season
                conf['season'].remove(season)
            else:
                actualSeason |= SEASON_NAME_TO_TYPE[season]
        if itemSeason is not None and itemSeason & ~SeasonType.EVENT == actualSeason:
            del conf['season']

    def migrateTeams(self, conf):
        for key in conf.keys():
            if 'useFor' in key:
                conf[key.replace('useFor', '').lower()] = conf.pop(key)

    def collectCamouflageData(self):
        camouflages = items.vehicles.g_cache.customization20().camouflages
        self.camoForSeason.clear()
        for season in SEASONS_CONSTANTS.SEASONS:
            self.camoForSeason[season] = {'random': [], 'ally': [], 'enemy': []}
        for camoID, camo in camouflages.iteritems():
            if camoID == EMPTY_ITEM_ID:
                continue
            itemName, itemKey = (camo.userKey, 'custom') if camo.priceGroup == 'custom' else (camoID, 'remap')
            cfg = self.camouflages[itemKey].get(itemName, {})
            mode = cfg.get('random_mode', SelectionMode.RANDOM)
            isAlly = cfg.get('ally', True)
            isEnemy = cfg.get('enemy', True)
            seasons = cfg.get('season', []) or [x for x in SEASONS_CONSTANTS.SEASONS if SEASON_NAME_TO_TYPE[x] & camo.season]
            for seasonName in seasons:
                camoForSeason = self.camoForSeason[seasonName]
                if mode == SelectionMode.RANDOM:
                    camoForSeason['random'].append(camoID)
                elif mode == SelectionMode.TEAM:
                    if isAlly:
                        camoForSeason['ally'].append(camoID)
                    if isEnemy:
                        camoForSeason['enemy'].append(camoID)

    def isCamoGlobal(self, camo):
        return camo.id in self.internationalCamoIDs

    def getOutfitCache(self):
        nation, vehicle = g_currentVehicle.item.descriptor.name.split(':')
        return self.outfitCache.get(nation, {}).get(vehicle, {})

    def getHangarCache(self):
        nation, vehicle = g_currentVehicle.item.descriptor.name.split(':')
        return self.hangarCamoCache.get(nation, {}).get(vehicle, {})


g_config = ConfigInterface()
statistic_mod = Analytics(g_config.ID, g_config.version, 'UA-76792179-7', g_config.configFolders)
