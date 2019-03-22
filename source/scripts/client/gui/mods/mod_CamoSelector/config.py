# coding=utf-8
import BigWorld
import ResMgr
import items.vehicles
import nations
import os
import traceback
from CurrentVehicle import g_currentPreviewVehicle, g_currentVehicle
from PYmodsCore import PYmodsConfigInterface, loadJson, refreshCurrentVehicle, remDups, Analytics
from gui.Scaleform.daapi.view.lobby.customization.shared import SEASON_TYPE_TO_NAME
from gui.Scaleform.framework import g_entitiesFactories
from gui.Scaleform.framework.managers.loaders import ViewLoadParams
from gui.Scaleform.genConsts.SEASONS_CONSTANTS import SEASONS_CONSTANTS
from gui.app_loader import g_appLoader
from items.components.c11n_constants import SeasonType
from . import __date__, __modID__
from .constants import RandMode, SEASON_NAME_TO_TYPE


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
        self.version = '2.1.0 (%s)' % __date__
        self.author += ' (thx to tratatank, Blither!)'
        self.data = {'enabled': True, 'doRandom': True, 'useBought': True, 'hangarCamoKind': 0,
                     'fullAlpha': False, 'disableWithDefault': False, 'fillEmptySlots': True, 'uniformOutfit': False}
        self.i18n = {
            'UI_description': 'Camouflage selector',
            'UI_flash_header': 'Camouflages setup',
            'UI_flash_header_tooltip': ('Advanced settings for camouflages added by CamoSelector by '
                                        '<font color=\'#DD7700\'><b>Polyacov_Yury</b></font>'),
            'UI_flash_tabs_0_label': 'Styles',
            'UI_flashCol_tabs_0_text': 'Styles',
            'UI_flashCol_tabs_0_tooltip': "If only you'd know how much time it took me to make this work...",
            'UI_flash_tabs_1_label': 'Paint',
            'UI_flashCol_tabs_1_text': 'Paint',
            'UI_flashCol_tabs_1_tooltip': 'Not camouflages at all. Paints. :)',
            'UI_flash_tabs_2_label': 'Shop',
            'UI_flashCol_tabs_2_text': 'Shop',
            'UI_flashCol_tabs_2_tooltip': 'Those which can be bought normally.',
            'UI_flash_tabs_3_label': 'Hidden',
            'UI_flashCol_tabs_3_text': 'Hidden',
            'UI_flashCol_tabs_3_tooltip': 'Those which are inaccessible under usual circumstances.',
            'UI_flash_tabs_4_label': 'Global',
            'UI_flashCol_tabs_4_text': 'Global map',
            'UI_flashCol_tabs_4_tooltip':
                'Those which are awarded for global map achievements, thus available for all nations.',
            'UI_flash_tabs_5_label': 'Custom',
            'UI_flashCol_tabs_5_text': 'Custom',
            'UI_flashCol_tabs_5_tooltip': 'Those which were added via config files.',
            'UI_flash_tabs_6_label': 'Emblems',
            'UI_flashCol_tabs_6_text': 'Emblems',
            'UI_flashCol_tabs_6_tooltip': 'Those small pictures that are added on your machine in place of nation flags.',
            'UI_flash_tabs_7_label': 'Inscriptions',
            'UI_flashCol_tabs_7_text': 'Inscriptions',
            'UI_flashCol_tabs_7_tooltip': 'Looks like chat is not enough.',
            'UI_flash_tabs_8_label': 'Effects',
            'UI_flashCol_tabs_8_text': 'Effects',
            'UI_flashCol_tabs_8_tooltip': 'Also known as paint scrambles.',
            'UI_flash_switcher_buy': 'PURCHASE',
            'UI_flash_switcher_setup': 'SETUP',
            'UI_flash_switcher_install': 'INSTALL',
            'UI_flash_switcher_tabsInvisible': 'Tabs are invisible while Shift key is pressed. #BlameWG',
            'UI_flash_commit_apply': 'Apply',
            'UI_flash_commit_install': 'Install',
            'UI_flash_commit_install_and_apply': 'Install and apply',
            'UI_flashCol_randMode_label': 'Random selection mode',
            'UI_flash_randMode_off': 'Disable',
            'UI_flash_randMode_random': 'Random',
            'UI_flash_randMode_team': 'Team',
            'UI_flashCol_teamMode_enemy_apply_label': 'Use for team: enemy',
            'UI_flash_teamMode_enemy_apply_btn': 'Apply',
            'UI_flashCol_teamMode_enemy_applied_label': 'Used for team: enemy',
            'UI_flash_teamMode_enemy_applied_btn': 'Remove',
            'UI_flashCol_teamMode_ally_apply_label': 'Use for team: ally',
            'UI_flash_teamMode_ally_apply_btn': 'Apply',
            'UI_flashCol_teamMode_ally_applied_label': 'Used for team: ally',
            'UI_flash_teamMode_ally_applied_btn': 'Remove',
            'UI_flash_teamMode_remove_btn': 'Remove from vehicle',
            'UI_flashCol_season_summer_apply_label': 'Apply for season: summer',
            'UI_flash_season_summer_apply_btn': 'Apply',
            'UI_flashCol_season_summer_applied_label': 'Applied for season: summer',
            'UI_flash_season_summer_applied_btn': 'Remove',
            'UI_flashCol_season_winter_apply_label': 'Apply for season: winter',
            'UI_flash_season_winter_apply_btn': 'Apply',
            'UI_flashCol_season_winter_applied_label': 'Applied for season: winter',
            'UI_flash_season_winter_applied_btn': 'Remove',
            'UI_flashCol_season_desert_apply_label': 'Apply for season: desert',
            'UI_flash_season_desert_apply_btn': 'Apply',
            'UI_flashCol_season_desert_applied_label': 'Applied for season: desert',
            'UI_flash_season_desert_applied_btn': 'Remove',
            'UI_flashCol_camoGroup_multinational': 'Multinational',
            'UI_flashCol_camoGroup_special': 'Special',
            'UI_flashCol_camoGroup_custom': 'Custom',
            'UI_flashCol_applied_money': 'Customization elements applied.\nWould buy %(count)s items, would spend %(money)s.',
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
                if not key.startswith('UI_flashCol_'):
                    continue
                self.i18n[key] = "<font color='#%s'>%s</font>" % (_config.data['colour'], self.i18n[key])
        except ImportError:
            pass

    def createTemplate(self):
        return {'modDisplayName': self.i18n['UI_description'],
                'settingsVersion': 200,
                'enabled': self.data['enabled'],
                'column1': [self.tb.createOptions('hangarCamoKind', [
                                self.i18n['UI_setting_hangarCamo_' + x] for x in ('winter', 'summer', 'desert', 'random')]),
                            self.tb.createControl('doRandom'),
                            self.tb.createControl('disableWithDefault')],
                'column2': [self.tb.createControl('fillEmptySlots'),
                            self.tb.createControl('uniformOutfit'),
                            self.tb.createControl('useBought'),
                            self.tb.createControl('fullAlpha')]}

    def onMSADestroy(self):
        try:
            from gui.mods import mod_remodenabler
        except ImportError:
            refreshCurrentVehicle()

    def onApplySettings(self, settings):
        if 'fullAlpha' in settings and settings['fullAlpha'] != self.data['fullAlpha']:
            items.vehicles.g_cache._Cache__customization20 = None
            items.vehicles.g_cache.customization20()
        # if 'enabled' in settings and settings['enabled'] != self.data['enabled'] and not settings['enabled']:
        #     from .settings import backups
        #     for alias in backups.keys():
        #         settings = g_entitiesFactories.getSettings(alias)
        #         if settings is None:
        #             del backups[alias]
        #             continue
        #         g_entitiesFactories.removeSettings(alias)
        #         g_entitiesFactories.addSettings(backups.pop(alias))
        super(self.__class__, self).onApplySettings(settings)
        self.hangarCamoCache.clear()
        if self.isModAdded:
            kwargs = dict(id='CamoSelectorUI', enabled=self.data['enabled'])
            try:
                BigWorld.g_modsListApi.updateModification(**kwargs)
            except AttributeError:
                BigWorld.g_modsListApi.updateMod(**kwargs)

    def readCurrentSettings(self, quiet=True):
        super(ConfigInterface, self).readCurrentSettings(quiet)
        self.configFolders.clear()
        self.camouflages = {'remap': {}, 'custom': {}}
        self.outfitCache = loadJson(self.ID, 'outfitCache', self.outfitCache, self.configPath)
        camoDirPath = '../' + self.configPath + 'camouflages'
        camoDirKeys = getattr(ResMgr.openSection(camoDirPath), 'keys', lambda: [])()
        for camoName in remDups(x for x in camoDirKeys if ResMgr.isDir(camoDirPath + '/' + x)):
            fileName = self.configPath + 'camouflages/' + camoName + '/'
            settings = loadJson(self.ID, 'settings', {}, fileName)
            self.configFolders[camoName] = set(settings)
            self.camouflages['custom'].update(settings)
            loadJson(self.ID, 'settings', settings, fileName, True)
        settings = loadJson(self.ID, 'settings', {}, self.configPath)
        self.disable = settings.setdefault('disable', self.disable)
        self.camouflages['remap'] = settings.setdefault('remap', {})
        loadJson(self.ID, 'settings', settings, self.configPath, True)

    def load(self):
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
        super(ConfigInterface, self).load()

    def migrateSettings(self, camoData):
        outfitCache = {}
        if os.path.isfile(self.configPath + 'camouflagesCache.json'):
            camouflagesCache = loadJson(self.ID, 'camouflagesCache', {}, self.configPath)
            for nat in camouflagesCache:
                for vehName in camouflagesCache[nat]:
                    for season in camouflagesCache[nat][vehName]:
                        outfitCache.setdefault(nat, {}).setdefault(vehName, {}).setdefault(season, {})['camo'] = \
                            camouflagesCache[nat][vehName][season]
            os.remove(self.configPath + 'camouflagesCache.json')
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
            if camoConf.get('random_mode') == RandMode.RANDOM:
                del camoConf['random_mode']
            self.migrateSeasons(camoID, camoConf, camouflage.season)
            if 'season' in camoConf:
                actualSeason = SeasonType.UNDEFINED
                for season in camoConf['season']:
                    actualSeason |= SEASON_NAME_TO_TYPE[season]
                if camouflage.season & ~SeasonType.EVENT == actualSeason:
                    del camoConf['season']
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
        for season in conf['season']:
            if season not in SEASON_NAME_TO_TYPE:
                print self.ID + ': unknown season name for camouflage', key + ':', season
                conf['season'].remove(season)

    def migrateTeams(self, conf):
        for key in conf.keys():
            if 'useFor' in key:
                conf[key.replace('useFor', '').lower()] = conf.pop(key)

    def registerSettings(self):
        super(self.__class__, self).registerSettings()
        if hasattr(BigWorld, 'g_modsListApi'):
            kwargs = dict(
                id='CamoSelectorUI', name=self.i18n['UI_flash_header'], description=self.i18n['UI_flash_header_tooltip'],
                icon='gui/flash/CamoSelector.png', enabled=self.data['enabled'], login=False, lobby=True,
                callback=lambda: None if g_currentVehicle.isInBattle() or g_currentPreviewVehicle.isPresent() else (
                    self.onMSAPopulate(), g_appLoader.getDefLobbyApp().loadView(ViewLoadParams('CamoSelectorMainView'))))
            try:
                BigWorld.g_modsListApi.addModification(**kwargs)
            except AttributeError:
                BigWorld.g_modsListApi.addMod(**kwargs)
            self.isModAdded = True

    def collectCamouflageData(self):
        camouflages = items.vehicles.g_cache.customization20().camouflages
        self.camoForSeason.clear()
        for season in SEASONS_CONSTANTS.SEASONS:
            self.camoForSeason[season] = {'random': [], 'ally': [], 'enemy': []}
        for camoID, camo in camouflages.iteritems():
            itemName, itemKey = (camo.userKey, 'custom') if camo.priceGroup == 'custom' else (camoID, 'remap')
            cfg = self.camouflages[itemKey].get(itemName, {})
            mode = cfg.get('random_mode', RandMode.RANDOM)
            isAlly = cfg.get('useForAlly', True)
            isEnemy = cfg.get('useForEnemy', True)
            seasons = cfg.get('season', []) or [x for x in SEASONS_CONSTANTS.SEASONS if SEASON_NAME_TO_TYPE[x] & camo.season]
            for seasonName in seasons:
                camoForSeason = self.camoForSeason[seasonName]
                if mode == RandMode.RANDOM:
                    camoForSeason['random'].append(camoID)
                elif mode == RandMode.TEAM:
                    if isAlly:
                        camoForSeason['ally'].append(camoID)
                    if isEnemy:
                        camoForSeason['enemy'].append(camoID)

    def isCamoGlobal(self, camo):
        return camo.id in self.internationalCamoIDs


g_config = ConfigInterface()
statistic_mod = Analytics(g_config.ID, g_config.version, 'UA-76792179-7', g_config.configFolders)
