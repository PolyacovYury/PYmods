# coding=utf-8
import BigWorld
import ResMgr
import items.vehicles
import nations
import traceback
from CurrentVehicle import g_currentPreviewVehicle, g_currentVehicle
from PYmodsCore import PYmodsConfigInterface, loadJson, refreshCurrentVehicle, remDups
from gui.Scaleform.framework.managers.loaders import ViewLoadParams
from gui.Scaleform.genConsts.SEASONS_CONSTANTS import SEASONS_CONSTANTS
from gui.app_loader import g_appLoader
from .. import __date__, __modID__
from ..shared import RandMode, SEASON_NAME_TO_TYPE, getCamoTextureName


class ConfigInterface(PYmodsConfigInterface):
    def __init__(self):
        self.disable = []
        self.hangarCamoCache = {}
        self.camouflagesCache = {}
        self.camouflages = {}
        self.configFolders = {}
        self.teamCamo = dict.fromkeys(('Ally', 'Enemy'))
        self.interCamo = []
        self.isModAdded = False
        super(ConfigInterface, self).__init__()

    def init(self):
        self.ID = __modID__
        self.version = '2.0.0 (%s)' % __date__
        self.author = '%s (thx to tratatank, Blither!)' % self.author
        self.data = {'enabled': True, 'doRandom': True, 'useBought': True, 'hangarCamoKind': 0,
                     'fullAlpha': False, 'disableWithDefault': False}
        self.i18n = {
            'UI_description': 'Camouflage selector',
            'UI_flash_tabs_0_label': 'Shop',
            'UI_flashCol_tabs_0_text': 'Shop',
            'UI_flashCol_tabs_0_tooltip': 'Those which can be bought freely',
            'UI_flash_tabs_1_label': 'Hidden',
            'UI_flashCol_tabs_1_text': 'Hidden',
            'UI_flashCol_tabs_1_tooltip': 'Those which are inaccessible under usual circumstances',
            'UI_flash_tabs_2_label': 'International',
            'UI_flashCol_tabs_2_text': 'International',
            'UI_flashCol_tabs_2_tooltip': 'Those which are available for all nations',
            'UI_flash_tabs_3_label': 'Custom',
            'UI_flashCol_tabs_3_text': 'Custom',
            'UI_flashCol_tabs_3_tooltip': 'Those which were added via config files',
            'UI_flash_switcher_setup': 'SETUP',
            'UI_flash_switcher_install': 'INSTALL',
            'UI_flash_commit_apply': 'Apply',
            'UI_flash_commit_install': 'Install',
            'UI_flash_commit_install_and_apply': 'Install and apply',
            'UI_flashCol_randMode_label': 'Random selection mode',
            'UI_flash_randMode_off': 'Disable',
            'UI_flash_randMode_random': 'Random',
            'UI_flash_randMode_team': 'Team',
            'UI_flashCol_teamMode_label': 'Use for team',
            'UI_flash_teamMode_ally': 'Ally',
            'UI_flash_teamMode_enemy': 'Enemy',
            'UI_flash_teamMode_both': 'All',
            'UI_flashCol_camoGroup_multinational': 'Multinational',
            'UI_flashCol_camoGroup_special': 'Special',
            'UI_flashCol_camoGroup_modded': 'Custom',
            'UI_message_applied_money': 'Customization elements applied.\nWould buy %(count)s items, would spend %(money)s.',
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
                'column1': [self.tb.createOptions('hangarCamoKind', [self.i18n['UI_setting_hangarCamo_%s' % x] for x in
                                                                     ('winter', 'summer', 'desert', 'random')]),
                            self.tb.createControl('doRandom'),
                            self.tb.createControl('disableWithDefault')],
                'column2': [self.tb.createHotKey('selectHotkey'),
                            self.tb.createEmpty(), self.tb.createEmpty(),
                            self.tb.createControl('useBought'),
                            self.tb.createControl('fullAlpha')]}

    def onMSADestroy(self):
        try:
            from gui.mods import mod_remodenabler
        except ImportError:
            refreshCurrentVehicle()

    def onApplySettings(self, settings):
        if settings['fullAlpha'] != self.data['fullAlpha']:
            items.vehicles.g_cache._Cache__customization20 = None
            items.vehicles.g_cache.customization20()
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
        self.camouflagesCache = loadJson(self.ID, 'camouflagesCache', self.camouflagesCache, self.configPath)
        try:
            camoDirPath = '../' + self.configPath + 'camouflages'
            camoDirSect = ResMgr.openSection(camoDirPath)
            for camoName in remDups(
                    (x for x in camoDirSect.keys() if ResMgr.isDir(camoDirPath + '/' + x))
                    if camoDirSect is not None else []):
                self.configFolders[camoName] = confFolder = set()
                fileName = self.configPath + 'camouflages/' + camoName + '/'
                settings = loadJson(self.ID, 'settings', {}, fileName)
                for key in settings:
                    conf = settings[key]
                    if 'kinds' in conf:
                        conf['season'] = conf['kinds']
                        del conf['kinds']
                    if 'season' in conf:
                        seasonNames = [x for x in conf['season'].split(',') if x]
                        seasonType = 0
                        for season in seasonNames:
                            if season in SEASON_NAME_TO_TYPE:
                                seasonType |= SEASON_NAME_TO_TYPE[season]
                            else:
                                print '%s: unknown season name for camouflage %s: %s' % (self.ID, key, season)
                                conf['season'] = conf['season'].replace(season, '')
                        while ',,' in conf['season']:
                            conf['season'] = conf['season'].replace(',,', ',')
                    else:
                        conf['season'] = ','.join(SEASONS_CONSTANTS.SEASONS)
                    confFolder.add(key)
                self.camouflages['custom'].update(settings)
                loadJson(self.ID, 'settings', settings, fileName, True)
        except StandardError:
            traceback.print_exc()
        camouflages = items.vehicles.g_cache.customization20().camouflages
        camoNames = {id: getCamoTextureName(x) for id, x in camouflages.iteritems() if 'custom' not in x.priceGroupTags}
        camoIndices = {}
        for camoID, camoName in camoNames.iteritems():
            camoIndices.setdefault(camoName, []).append(camoID)
        self.interCamo = []
        for camoName, indices in camoIndices.iteritems():
            nationsList = []
            for ID in indices:
                for filterNode in camouflages[ID].filter.include:
                    if filterNode.nations:
                        nationsList += filterNode.nations
            if set(nationsList) == set(idx for idx, name in enumerate(nations.NAMES) if name != 'italy'):
                self.interCamo.append(camoName)
        settings = loadJson(self.ID, 'settings', {}, self.configPath)
        if 'disable' in settings:
            if not settings['disable']:
                del settings['disable']
            else:
                self.disable = settings['disable']
        if 'remap' in settings:
            conf = settings['remap']
            for camoName in conf.keys():
                try:
                    camoName = int(camoName)
                except ValueError:
                    if camoName not in camoIndices:
                        print '%s: unknown camouflage for remapping: %s' % (self.ID, camoName)
                    else:
                        for camoID in camoIndices[camoName]:
                            conf[camoID] = conf[camoName].copy()
                    del conf[camoName]
                    continue
                if camoName not in camoNames:
                    print '%s: unknown camouflage for remapping: %s' % (self.ID, camoName)
                    del conf[camoName]
                else:
                    conf[camoName] = conf.pop(str(camoName))
            for camoID, camouflage in camouflages.items():
                if camoID not in conf:
                    continue
                camoConf = conf[camoID]
                if camoConf.get('random_mode') == RandMode.RANDOM:
                    del camoConf['random_mode']
                if 'kinds' in camoConf:
                    camoConf['season'] = camoConf['kinds']
                    del camoConf['kinds']
                if 'season' in camoConf:
                    seasonNames = [x for x in camoConf['season'].split(',') if x]
                    seasonType = 0
                    for season in seasonNames:
                        if season in SEASON_NAME_TO_TYPE:
                            seasonType |= SEASON_NAME_TO_TYPE[season]
                        else:
                            print '%s: unknown season name for camouflage %s: %s' % (self.ID, camoID, season)
                            camoConf['season'] = camoConf['season'].replace(season, '')
                    while ',,' in camoConf['season']:
                        camoConf['season'] = camoConf['season'].replace(',,', ',')
                    if seasonType == camouflage.season:
                        del camoConf['season']
                for team in ('Ally', 'Enemy'):
                    if camoConf.get('useFor%s' % team):
                        del camoConf['useFor%s' % team]
                if not camoConf:
                    del conf[camoID]
            self.camouflages['remap'] = conf
        newSettings = {}
        if self.disable:
            newSettings['disable'] = self.disable
        newSettings['remap'] = settings.get('remap', {})
        loadJson(self.ID, 'settings', newSettings, self.configPath, True)

    def registerSettings(self):
        super(self.__class__, self).registerSettings()
        if hasattr(BigWorld, 'g_modsListApi'):
            kwargs = dict(
                id='CamoSelectorUI', name=self.i18n['UI_flash_header'], description=self.i18n['UI_flash_header_tooltip'],
                icon='gui/flash/CamoSelector.png', enabled=self.data['enabled'], login=False, lobby=True,
                callback=lambda: None if g_currentVehicle.item is None or g_currentPreviewVehicle.item is not None else (
                    self.onMSAPopulate(), g_appLoader.getDefLobbyApp().loadView(ViewLoadParams('CamoSelectorMainView'))))
            try:
                BigWorld.g_modsListApi.addModification(**kwargs)
            except AttributeError:
                BigWorld.g_modsListApi.addMod(**kwargs)
            self.isModAdded = True


g_config = ConfigInterface()
# TODO: statistic_mod = Analytics(_config.ID, _config.version, 'UA-76792179-7', _config.configFolders)
