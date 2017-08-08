# -*- coding: utf-8 -*-
import BigWorld
import Keys
import Math
import PYmodsCore
import ResMgr
import glob
import os
import traceback
from CurrentVehicle import g_currentPreviewVehicle
from gui import InputHandler, SystemMessages
from gui.Scaleform.framework import GroupedViewSettings, ScopeTemplates, ViewSettings, ViewTypes, g_entitiesFactories
from gui.Scaleform.framework.entities.abstract.AbstractWindowView import AbstractWindowView
from gui.app_loader import g_appLoader
from gui.shared.utils.HangarSpace import g_hangarSpace
from items.vehicles import EmblemSlot, g_cache
from vehicle_systems.tankStructure import TankPartNames


def readAODecals(confList):
    retVal = []
    for subDict in confList:
        m = Math.Matrix()
        for strNum, matStr in enumerate(sorted(subDict['transform'].keys())):
            for colNum, elemNum in enumerate(subDict['transform'][matStr]):
                m.setElement(strNum, colNum, elemNum)
        retVal.append(m)

    return retVal


def readEmblemSlots(confList):
    slots = []
    for confDict in confList:
        if confDict['type'] not in ('player', 'clan', 'inscription', 'insigniaOnGun'):
            print '%s: not supported emblem slot type: %s, expected: %s' % (
                g_config.ID, confDict['type'], ' '.join(('player', 'clan', 'inscription', 'insigniaOnGun')))
        descr = EmblemSlot(Math.Vector3(tuple(confDict['rayStart'])), Math.Vector3(tuple(confDict['rayEnd'])),
                           Math.Vector3(tuple(confDict['rayUp'])), confDict['size'],
                           confDict.get('hideIfDamaged', False), confDict['type'], confDict.get('isMirrored', False),
                           confDict.get('isUVProportional', True), confDict.get('emblemId', None))
        slots.append(descr)

    return slots


class OM(object):
    tankGroups = ('Player', 'Ally', 'Enemy')

    def __init__(self):
        self.models = {}
        self.enabled = False
        self.selected = {'Player': {}, 'Ally': {}, 'Enemy': {}, 'Remod': ''}


class OMDescriptor(object):
    def __init__(self):
        self.name = ''
        self.authorMessage = ''
        self.whitelists = {'Player': set(), 'Ally': set(), 'Enemy': set()}
        self.data = {
            'chassis': {'undamaged': '', 'AODecals': None, 'hullPosition': None, 'wwsoundPC': '', 'wwsoundNPC': ''},
            'hull': {'undamaged': '', 'emblemSlots': [], 'exhaust': {'nodes': [], 'pixie': ''},
                     'camouflage': {'exclusionMask': '', 'tiling': (1.0, 1.0, 0.0, 0.0)}},
            'turret': {'undamaged': '', 'emblemSlots': [],
                       'camouflage': {'exclusionMask': '', 'tiling': (1.0, 1.0, 0.0, 0.0)}},
            'gun': {'undamaged': '', 'emblemSlots': [], 'effects': '', 'reloadEffect': '',
                    'camouflage': {'exclusionMask': '', 'tiling': (1.0, 1.0, 0.0, 0.0)}},
            'engine': {'wwsoundPC': '', 'wwsoundNPC': ''},
            'common': {'camouflage': {'exclusionMask': '', 'tiling': (1.0, 1.0, 0.0, 0.0)}}}


class OS(object):
    def __init__(self):
        self.models = {'static': {}, 'dynamic': {}}
        self.enabled = True
        self.priorities = {skinType: {'Player': [], 'Ally': [], 'Enemy': []} for skinType in self.models}


class OSDescriptor(object):
    def __init__(self):
        self.name = ''
        self.whitelist = set()


class _Config(PYmodsCore.Config):
    def __init__(self):
        super(self.__class__, self).__init__('RemodEnabler')
        self.version = '3.0.0 (%(file_compile_date)s)'
        self.author = '%s (thx to atacms)' % self.author
        self.possibleModes = ['player', 'ally', 'enemy', 'remod']
        self.defaultSkinConfig = {'static': {'enabled': True, 'swapPlayer': True, 'swapAlly': True, 'swapEnemy': True},
                                  'dynamic': {'enabled': True, 'swapPlayer': False, 'swapAlly': True, 'swapEnemy': True}}
        self.defaultRemodConfig = {'enabled': True, 'swapPlayer': True, 'swapAlly': True, 'swapEnemy': True}
        self.defaultKeys = {'DynamicSkinHotKey': ['KEY_F1', ['KEY_LCONTROL', 'KEY_RCONTROL']],
                            'DynamicSkinHotkey': [Keys.KEY_F1, [Keys.KEY_LCONTROL, Keys.KEY_RCONTROL]],
                            'ChangeViewHotKey': ['KEY_F2', ['KEY_LCONTROL', 'KEY_RCONTROL']],
                            'ChangeViewHotkey': [Keys.KEY_F2, [Keys.KEY_LCONTROL, Keys.KEY_RCONTROL]],
                            'SwitchRemodHotKey': ['KEY_F3', ['KEY_LCONTROL', 'KEY_RCONTROL']],
                            'SwitchRemodHotkey': [Keys.KEY_F3, [Keys.KEY_LCONTROL, Keys.KEY_RCONTROL]],
                            'CollisionHotKey': ['KEY_F4', ['KEY_LCONTROL', 'KEY_RCONTROL']],
                            'CollisionHotkey': [Keys.KEY_F4, [Keys.KEY_LCONTROL, Keys.KEY_RCONTROL]]}
        self.data = {'enabled': True,
                     'isDebug': True,
                     'skinsFound': False,
                     'collisionEnabled': False,
                     'collisionComparisonEnabled': False,
                     'dynamicSkinEnabled': False,
                     'isInHangar': False,
                     'DynamicSkinHotKey': self.defaultKeys['DynamicSkinHotKey'],
                     'DynamicSkinHotkey': self.defaultKeys['DynamicSkinHotkey'],
                     'ChangeViewHotKey': self.defaultKeys['ChangeViewHotKey'],
                     'ChangeViewHotkey': self.defaultKeys['ChangeViewHotkey'],
                     'CollisionHotKey': self.defaultKeys['CollisionHotKey'],
                     'CollisionHotkey': self.defaultKeys['CollisionHotkey'],
                     'SwitchRemodHotKey': self.defaultKeys['SwitchRemodHotKey'],
                     'SwitchRemodHotkey': self.defaultKeys['SwitchRemodHotkey'],
                     'currentMode': self.possibleModes[0],
                     'remod': True}
        self.i18n = {
            'UI_description': 'Remod Enabler',
            'UI_flash_header': 'Remods and skins setup',
            'UI_flash_header_tooltip': "Extended setup for RemodEnabler by "
                                       "<font color='#DD7700'><b>Polyacov_Yury</b></font>",
            'UI_flash_remodSetupBtn': 'Remods setup',
            'UI_flash_remodWLBtn': 'Remod whitelists',
            'UI_flash_remodCreateBtn': 'Create remod',
            'UI_flash_remodCreate_name_text': 'Remod name',
            'UI_flash_remodCreate_name_tooltip': 'Remod unique ID and config file name.',
            'UI_flash_remodCreate_message_text': 'Author message',
            'UI_flash_remodCreate_message_tooltip': 'This message is displayed in hangar every time the remod is selected.'
                                                    '\nLeave blank if not required.',
            'UI_flash_remodCreate_name_empty': '<b>Remod creation failed:</b>\nname is empty.',
            'UI_flash_remodCreate_wrongVehicle': '<b>Remod creation failed:</b>\n'
                                                 'select the vehicle you started to create a remod from.',
            'UI_flash_remodCreate_error': '<b>Remod creation failed:</b>\ncheck python.log for additional information.',
            'UI_flash_remodCreate_success': '<b>Remod created successfully</b>.',
            'UI_flash_skinSetupBtn': 'Skins setup',
            'UI_flash_skinPriorityBtn': 'Skin priorities',
            'UI_flash_skinType_static': 'Static',
            'UI_flash_skinType_dynamic': 'Dynamic',
            'UI_flash_team_player': 'Player',
            'UI_flash_team_ally': 'Ally',
            'UI_flash_team_enemy': 'Enemy',
            'UI_flash_whiteList_addBtn': 'Add current tank',
            'UI_flash_whiteList_del_text': 'View and delete:',
            'UI_flash_whiteList_del_tooltip': 'Open to view all items, select an item to delete.\n\n'
                                              'List is scrollable if longer than 10 items.',
            'UI_flash_whiteDropdown_default': 'Click to expand',
            'UI_flash_useFor_header_text': 'Use this item for:',
            'UI_flash_useFor_enable_text': 'Enabled',
            'UI_flash_useFor_player_text': 'Player',
            'UI_flash_useFor_ally_text': 'Allies',
            'UI_flash_useFor_enemy_text': 'Enemies',
            'UI_flash_WLVehDelete_header': 'Confirmation',
            'UI_flash_WLVehDelete_text': 'Are you sure you want to delete this vehicle from this whitelist?',
            'UI_flash_vehicleDelete_success': 'Vehicle deleted from whitelist: ',
            'UI_flash_vehicleAdd_success': 'Vehicle added to whitelist: ',
            'UI_flash_vehicleAdd_dupe': 'Vehicle already in whitelist: ',
            'UI_flash_backBtn': 'Back',
            'UI_flash_saveBtn': 'Save',
            'UI_loading_bugReport': 'Report a bug',
            'UI_loading_done': ' Done!',
            'UI_loading_header_CRC32': 'RemodEnabler: checking textures',
            'UI_loading_header_models_unpack': 'RemodEnabler: unpacking models',
            'UI_loading_package': 'Unpacking %s:',
            'UI_loading_skinPack': 'Checking %s:',
            'UI_loading_skins': 'Checking skins...',
            'UI_setting_isDebug_text': 'Enable extended log printing',
            'UI_setting_isDebug_tooltip': 'If enabled, your python.log will be harassed with mod\'s debug information.',
            'UI_setting_remod_text': 'Enable all remods preview mode',
            'UI_setting_remod_tooltip': 'If disabled, all remods preview mode will not be active.',
            'UI_setting_ChangeViewHotkey_text': 'View mode switch hotkey',
            'UI_setting_ChangeViewHotkey_tooltip': (
                'This hotkey will switch the preview mode in hangar.\n<b>Possible modes:</b>\n'
                ' • Player tank\n • Ally tank\n • Enemy tank%(remod)s'),
            'UI_setting_ChangeViewHotkey_remod': '\n • Remod preview',
            'UI_setting_DynamicSkinHotkey_text': 'Dynamic skin display switch hotkey',
            'UI_setting_DynamicSkinHotkey_tooltip': (
                'This hotkey will switch dynamic skin preview mode in hangar.\n'
                '<b>Possible modes:</b>\n • OFF\n • Model add'),
            'UI_setting_CollisionHotkey_text': 'Collision view switch hotkey',
            'UI_setting_CollisionHotkey_tooltip': (
                'This hotkey will switch collision preview mode in hangar.\n'
                '<b>Possible modes:</b>\n • OFF\n • Model replace\n • Model add'),
            'UI_setting_SwitchRemodHotkey_text': 'Remod switch hotkey',
            'UI_setting_SwitchRemodHotkey_tooltip': (
                'This hotkey will cycle through all remods (ignoring whitelists in remod preview mode).'),
            'UI_disableCollisionComparison': '<b>RemodEnabler:</b>\nDisabling collision comparison mode.',
            'UI_enableCollisionComparison': '<b>RemodEnabler:</b>\nEnabling collision comparison mode.',
            'UI_enableCollision': '<b>RemodEnabler:</b>\nEnabling collision mode.',
            'UI_enableDynamicSkin': '<b>RemodEnabler:</b>\nEnabling dynamic skins display.',
            'UI_disableDynamicSkin': '<b>RemodEnabler:</b>\nDisabling dynamic skins display.',
            'UI_install_skin': '<b>RemodEnabler:</b>\nSkin installed: ',
            'UI_install_skin_dynamic': '<b>RemodEnabler:</b>\nDynamic skin installed: ',
            'UI_install_remod': '<b>RemodEnabler:</b>\nRemod installed: ',
            'UI_install_default': '<b>RemodEnabler:</b>\nDefault model applied.',
            'UI_mode': '<b>RemodEnabler:</b>\nCurrent display mode: ',
            'UI_mode_player': 'player tank preview',
            'UI_mode_ally': 'ally tank preview',
            'UI_mode_enemy': 'enemy tank preview',
            'UI_mode_remod': 'all remods preview'}
        self.configsDict = {}
        self.settings = {'remods': {}, 'skins': {}, 'skins_dynamic': {}}
        self.skinsCache = {"CRC32": "", "version": ""}
        self.OM = OM()
        self.OS = OS()
        self.OMDesc = None
        self.OSDesc = {'static': None, 'dynamic': None}
        self.curVehicleName = None
        self.loadingProxy = None
        self.isModAdded = False
        self.loadLang()

    def template_settings(self):
        viewKey = self.createHotKey('ChangeViewHotkey')
        viewKey['tooltip'] %= {'remod': self.i18n['UI_setting_ChangeViewHotkey_remod'] if self.data['remod'] else ''}
        template = {'modDisplayName': self.i18n['UI_description'],
                    'settingsVersion': 200,
                    'enabled': self.data['enabled'],
                    'column1': [self.createHotKey('DynamicSkinHotkey'),
                                self.createControl('isDebug'),
                                self.createControl('remod')],
                    'column2': [viewKey,
                                self.createHotKey('SwitchRemodHotkey'),
                                self.createHotKey('CollisionHotkey')]}
        return template

    def onWindowClose(self):
        g_currentPreviewVehicle.refreshModel()

    def apply_settings(self, settings):
        super(self.__class__, self).apply_settings(settings)
        if self.isModAdded:
            kwargs = dict(id='RemodEnablerUI', enabled=self.data['enabled'])
            try:
                BigWorld.g_modsListApi.updateModification(**kwargs)
            except AttributeError:
                BigWorld.g_modsListApi.updateMod(**kwargs)

    # noinspection PyUnresolvedReferences
    def update_data(self, doPrint=False):
        super(self.__class__, self).update_data()
        self.settings = self.loadJson('settings', self.settings, self.configPath)
        self.skinsCache.update(self.loadJson('skinsCache', self.skinsCache, self.configPath))
        configsPath = self.configPath + 'remods/*.json'
        self.OM.enabled = bool(glob.glob(configsPath))
        if self.OM.enabled:
            self.OM.selected = self.loadJson('remodsCache', self.OM.selected, self.configPath)
            for configPath in glob.iglob(configsPath):
                sname = os.path.basename(configPath).split('.')[0]
                self.configsDict[sname] = confDict = self.loadJson(sname, self.configsDict.get(sname, {}),
                                                                   os.path.dirname(configPath) + '/', encrypted=True)
                if not confDict:
                    print '%s: error while reading %s.' % (self.ID, os.path.basename(configPath))
                    continue
                settingsDict = self.settings['remods'].setdefault(sname, {})
                if not settingsDict.setdefault('enabled', self.defaultRemodConfig['enabled']):
                    print '%s: %s disabled, moving on' % (self.ID, sname)
                    if sname in self.OM.models:
                        del self.OM.models[sname]
                    continue
                self.OM.models[sname] = pRecord = OMDescriptor()
                pRecord.name = sname
                pRecord.authorMessage = confDict.get('authorMessage', '')
                for tankType in OM.tankGroups:
                    selected = self.OM.selected[tankType]
                    swapKey = 'swap%s' % tankType
                    WLKey = '%sWhitelist' % tankType.lower()
                    whiteStr = settingsDict.setdefault(WLKey, confDict.get(WLKey, ''))
                    templist = [x.strip() for x in whiteStr.split(',') if x]
                    whitelist = pRecord.whitelists[tankType]
                    whitelist.update(templist)
                    if not whitelist:
                        if self.data['isDebug']:
                            print '%s: empty whitelist for %s. Not applied to %s tanks.' % (
                                self.ID, sname, tankType.lower())
                    else:
                        if self.data['isDebug']:
                            print '%s: whitelist for %s: %s' % (self.ID, tankType.lower(), list(whitelist))
                        for xmlName in selected:
                            if sname == selected[xmlName] and xmlName not in whitelist:
                                selected[xmlName] = None
                    if not settingsDict.setdefault(swapKey, confDict.get(swapKey, self.defaultRemodConfig[swapKey])):
                        if self.data['isDebug']:
                            print '%s: %s swapping in %s disabled.' % (self.ID, tankType.lower(), sname)
                        whitelist.clear()
                        for xmlName in selected:
                            if sname == selected[xmlName]:
                                selected[xmlName] = None
                for key, data in pRecord.data.iteritems():
                    if key == 'common':
                        confSubDict = confDict
                    else:
                        confSubDict = confDict.get(key)
                    if not confSubDict:
                        continue
                    if 'undamaged' in data:
                        data['undamaged'] = confSubDict['undamaged']
                    if 'AODecals' in data and 'AODecals' in confSubDict and 'hullPosition' in confSubDict:
                        data['AODecals'] = readAODecals(confSubDict['AODecals'])
                        data['hullPosition'] = Math.Vector3(tuple(confSubDict['hullPosition']))
                    if 'camouflage' in data and 'exclusionMask' in confSubDict.get('camouflage', {}):
                        data['camouflage']['exclusionMask'] = confSubDict['camouflage']['exclusionMask']
                        if 'tiling' in confSubDict['camouflage']:
                            data['camouflage']['tiling'] = tuple(confDict['camouflage']['tiling'])
                    elif key == 'common' and self.data['isDebug']:
                        print '%s: default camomask not found for %s' % (self.ID, sname)
                    if 'emblemSlots' in data:
                        data['emblemSlots'] = readEmblemSlots(confSubDict.get('emblemSlots', []))
                    if 'exhaust' in data:
                        if 'nodes' in confSubDict.get('exhaust', {}):
                            data['exhaust']['nodes'] = confSubDict['exhaust']['nodes'].split()
                        if 'pixie' in confSubDict.get('exhaust', {}):
                            data['exhaust']['pixie'] = confSubDict['exhaust']['pixie']
                    if key == 'chassis':
                        for k in ('traces', 'tracks', 'wheels', 'groundNodes', 'trackNodes', 'splineDesc', 'trackParams'):
                            data[k] = confSubDict[k]
                    for subKey in ('effects', 'reloadEffect', 'wwsoundPC', 'wwsoundNPC'):
                        if subKey in data and subKey in confSubDict:
                            data[subKey] = confSubDict[subKey]
                if self.data['isDebug']:
                    print '%s: config for %s loaded.' % (self.ID, sname)

            if not self.OM.models:
                if doPrint:
                    print '%s: no configs found, model module standing down.' % self.ID
                self.OM.enabled = False
                self.loadJson('remodsCache', self.OM.selected, self.configPath, True, doPrint=doPrint)
            else:
                remodTanks = {key: set() for key in self.OM.selected}
                for OMDesc in self.OM.models.values():
                    for tankType, whitelist in OMDesc.whitelists.iteritems():
                        for xmlName in whitelist:
                            remodTanks[tankType].add(xmlName)
                            if xmlName not in self.OM.selected[tankType]:
                                self.OM.selected[tankType][xmlName] = None
                for tankType in OM.tankGroups:
                    for xmlName in self.OM.selected[tankType].keys():
                        if (self.OM.selected[tankType][xmlName] and self.OM.selected[tankType][
                                xmlName] not in self.OM.models):
                            self.OM.selected[tankType][xmlName] = None
                        if xmlName not in remodTanks[tankType]:
                            del self.OM.selected[tankType][xmlName]
                if self.OM.selected['Remod'] and self.OM.selected['Remod'] not in self.OM.models:
                    self.OM.selected['Remod'] = ''
                self.loadJson('remodsCache', self.OM.selected, self.configPath, True, doPrint=doPrint)
        else:
            if doPrint:
                print '%s: no remods found, model module standing down.' % self.ID
            self.OM.enabled = False
            self.loadJson('remodsCache', self.OM.selected, self.configPath, True, doPrint=doPrint)
        self.OS.enabled = ResMgr.openSection('vehicles/skins/') is not None and ResMgr.isDir('vehicles/skins/')
        if self.OS.enabled:
            self.OS.priorities = self.loadJson('skinsPriority', self.OS.priorities, self.configPath)
            skinDir = 'vehicles/skins/textures/'
            for skinTypeSuff in ('', '_dynamic'):
                skinType = 'static' if not skinTypeSuff else skinTypeSuff[1:]
                skinsSettings = self.settings['skins%s' % skinTypeSuff]
                disabledSkins = []
                if self.data['isDebug']:
                    print '%s: loading configs for %s skins' % (self.ID, skinType)
                skinDirSect = ResMgr.openSection(skinDir)
                for sname in [] if skinDirSect is None else PYmodsCore.remDups(skinDirSect.keys()):
                    confDict = skinsSettings.setdefault(sname, self.defaultSkinConfig[skinType])
                    if not confDict.get('enabled', True):
                        print '%s: %s disabled, moving on' % (self.ID, sname)
                        disabledSkins.append(sname)
                        continue
                    self.OS.models[skinType][sname] = pRecord = OSDescriptor()
                    pRecord.name = sname
                    priorities = self.OS.priorities[skinType]
                    for tankType in priorities:
                        key = 'swap%s' % tankType
                        if not confDict.setdefault(key, self.defaultSkinConfig[skinType][key]):
                            if self.data['isDebug']:
                                print '%s: %s swapping in %s disabled.' % (self.ID, tankType, sname)
                            if sname in priorities[tankType]:
                                priorities[tankType].remove(sname)
                            continue
                        if sname not in priorities[tankType]:
                            priorities[tankType].append(sname)
                    pRecord.whitelist.clear()
                    vehiclesDirPath = skinDir + sname + '/vehicles/'
                    vehiclesDirSect = ResMgr.openSection(vehiclesDirPath)
                    for curNation in [] if vehiclesDirSect is None else PYmodsCore.remDups(vehiclesDirSect.keys()):
                        nationDirPath = vehiclesDirPath + curNation + '/'
                        nationDirSect = ResMgr.openSection(nationDirPath)
                        for vehicleName in [] if nationDirSect is None else PYmodsCore.remDups(nationDirSect.keys()):
                            vehDirPath = nationDirPath + vehicleName + '/'
                            vehDirSect = ResMgr.openSection(vehDirPath)
                            tracksDirPath = vehDirPath + 'tracks/'
                            tracksDirSect = ResMgr.openSection(tracksDirPath)
                            if not [texName for texName in
                                    ([] if vehDirSect is None else PYmodsCore.remDups(vehDirSect.keys())) if
                                    texName.endswith('.dds')] and not [texName for texName in (
                                    [] if tracksDirSect is None else PYmodsCore.remDups(tracksDirSect.keys())) if
                                                                       texName.endswith('.dds')]:
                                if self.data['isDebug']:
                                    print '%s: %s folder from %s pack is empty' % (
                                        self.ID, vehicleName, sname)
                            else:
                                pRecord.whitelist.add(vehicleName)

                    if self.data['isDebug']:
                        print '%s: config for %s loaded.' % (self.ID, sname)
                snameList = self.OS.models[skinType].keys() + disabledSkins
                for sname in skinsSettings.keys():
                    if sname not in snameList:
                        del skinsSettings[sname]
            if not any(self.OS.models.values()):
                if doPrint:
                    print '%s: no skins configs found, skins module standing down.' % self.ID
                self.OS.enabled = False
                for skinType in self.OS.priorities:
                    for key in self.OS.priorities[skinType]:
                        self.OS.priorities[skinType][key] = []
            else:
                for skinType in self.OS.priorities:
                    for key in self.OS.priorities[skinType]:
                        for sname in list(self.OS.priorities[skinType][key]):
                            if sname not in self.OS.models[skinType]:
                                self.OS.priorities[skinType][key].remove(sname)
        else:
            if doPrint:
                print '%s: no skins found, skins module standing down.' % self.ID
            for skinType in self.OS.priorities:
                for key in self.OS.priorities[skinType]:
                    self.OS.priorities[skinType][key] = []
        self.loadJson('skinsPriority', self.OS.priorities, self.configPath, True, doPrint=doPrint)
        self.loadJson('settings', self.settings, self.configPath, True, doPrint=doPrint)

    def do_config(self):
        super(self.__class__, self).do_config()
        from .skinLoader import RemodEnablerLoading
        # noinspection PyArgumentList
        g_entitiesFactories.addSettings(
            ViewSettings('RemodEnablerUI', RemodEnablerUI, 'RemodEnabler.swf', ViewTypes.WINDOW, None,
                         ScopeTemplates.GLOBAL_SCOPE, False))
        g_entitiesFactories.addSettings(
            GroupedViewSettings('RemodEnablerLoading', RemodEnablerLoading, 'LoginQueueWindow.swf', ViewTypes.TOP_WINDOW,
                                '', None, ScopeTemplates.DEFAULT_SCOPE))
        kwargs = dict(
            id='RemodEnablerUI', name=self.i18n['UI_flash_header'], description=self.i18n['UI_flash_header_tooltip'],
            icon='gui/flash/RemodEnabler.png', enabled=self.data['enabled'], login=True, lobby=True,
            callback=lambda: self.loadingProxy is not None or g_appLoader.getDefLobbyApp().loadView('RemodEnablerUI'))
        try:
            BigWorld.g_modsListApi.addModification(**kwargs)
        except AttributeError:
            BigWorld.g_modsListApi.addMod(**kwargs)
        self.isModAdded = True


class RemodEnablerUI(AbstractWindowView):
    def _populate(self):
        super(self.__class__, self)._populate()
        self.modeBackup = g_config.data['currentMode']
        self.remodBackup = g_config.OM.selected['Remod']

    def py_onRequestSettings(self):
        g_config.update_data(g_config.data['isDebug'])
        texts = {
            'header': {
                'main': g_config.i18n['UI_flash_header'],
                'remodSetup': g_config.i18n['UI_flash_remodSetupBtn'],
                'remodWL': g_config.i18n['UI_flash_remodWLBtn'],
                'remodCreate': g_config.i18n['UI_flash_remodCreateBtn'],
                'skinSetup': g_config.i18n['UI_flash_skinSetupBtn'],
                'priorities': g_config.i18n['UI_flash_skinPriorityBtn']},
            'remodSetupBtn': g_config.i18n['UI_flash_remodSetupBtn'],
            'remodWLBtn': g_config.i18n['UI_flash_remodWLBtn'],
            'remodCreateBtn': g_config.i18n['UI_flash_remodCreateBtn'],
            'skinsSetupBtn': g_config.i18n['UI_flash_skinSetupBtn'],
            'skinsPriorityBtn': g_config.i18n['UI_flash_skinPriorityBtn'],
            'create': {'name': g_config.createLabel('remodCreate_name', 'flash'),
                       'message': g_config.createLabel('remodCreate_message', 'flash')},
            'skinTypes': [g_config.i18n['UI_flash_skinType_%s' % skinType] for skinType in ('static', 'dynamic')],
            'teams': [g_config.i18n['UI_flash_team_%s' % team] for team in ('player', 'ally', 'enemy')],
            'remodNames': [],
            'skinNames': [[], []],
            'whiteList': {'addBtn': g_config.i18n['UI_flash_whiteList_addBtn'],
                          'delLabel': g_config.createLabel('whiteList_del', 'flash'),
                          'defStr': g_config.i18n['UI_flash_whiteDropdown_default']},
            'useFor': {'header': g_config.createLabel('useFor_header', 'flash'),
                       'ally': g_config.createLabel('useFor_ally', 'flash'),
                       'enemy': g_config.createLabel('useFor_enemy', 'flash'),
                       'player': g_config.createLabel('useFor_player', 'flash'),
                       'enable': g_config.createLabel('useFor_enable', 'flash')},
            'backBtn': g_config.i18n['UI_flash_backBtn'],
            'saveBtn': g_config.i18n['UI_flash_saveBtn']
        }
        settings = {
            'remods': [],
            'skins': [[], []],
            'priorities': [[g_config.OS.priorities[sType][team] for team in ('Player', 'Ally', 'Enemy')] for sType in
                           ('static', 'dynamic')],
            'whitelists': [],
            'isInHangar': g_config.data['isInHangar']
        }
        for sname in sorted(g_config.OM.models):
            OMSettings = g_config.settings['remods'][sname]
            texts['remodNames'].append(sname)
            # noinspection PyTypeChecker
            settings['remods'].append({'useFor': {key.lower(): OMSettings['swap%s' % key] for key in OM.tankGroups},
                                       'whitelists': [str(OMSettings[team.lower() + 'Whitelist']).split(',')
                                                      for team in OM.tankGroups]})
        for idx, skinType in enumerate(('', '_dynamic')):
            skins = g_config.settings['skins%s' % skinType]
            for sname in sorted(g_config.OS.models['static' if not skinType else 'dynamic']):
                sDesc = skins[sname]
                texts['skinNames'][idx].append(sname)
                # noinspection PyUnresolvedReferences
                settings['skins'][idx].append({'useFor': {k.lower(): sDesc['swap%s' % k] for k in OM.tankGroups}})
        self.flashObject.as_updateData(texts, settings)

    @staticmethod
    def py_getRemodData():
        OMDesc = g_config.OMDesc
        currentVehicle = RemodEnablerUI.py_getCurrentVehicleName()
        if OMDesc is not None:
            return {'isRemod': True, 'name': OMDesc.name, 'message': OMDesc.authorMessage, 'vehicleName': currentVehicle,
                    'whitelists': [str(g_config.settings['remods'][OMDesc.name][team.lower() + 'Whitelist']).split(',')
                                   for team in OM.tankGroups]}
        else:
            return {'isRemod': False, 'name': '', 'message': '', 'vehicleName': currentVehicle,
                    'whitelists': [[currentVehicle] for _ in OM.tankGroups]}

    @staticmethod
    def py_onShowRemod(remodIdx):
        g_config.data['currentMode'] = 'remod'
        g_config.OM.selected['Remod'] = sorted(g_config.OM.models)[remodIdx]
        g_currentPreviewVehicle.refreshModel()

    def py_onModelRestore(self):
        g_config.data['currentMode'] = self.modeBackup
        g_config.OM.selected['Remod'] = self.remodBackup
        g_currentPreviewVehicle.refreshModel()

    @staticmethod
    def py_getCurrentVehicleName():
        vDesc = g_hangarSpace._HangarSpace__space._ClientHangarSpace__vAppearance._VehicleAppearance__vDesc
        return vDesc.name.split(':')[1].lower()

    def py_onRequestVehicleDelete(self, teamIdx):
        from gui import DialogsInterface
        from gui.Scaleform.daapi.view.dialogs import SimpleDialogMeta, I18nConfirmDialogButtons

        DialogsInterface.showDialog(SimpleDialogMeta(g_config.i18n['UI_flash_WLVehDelete_header'],
                                                     g_config.i18n['UI_flash_WLVehDelete_text'],
                                                     I18nConfirmDialogButtons('common/confirm'), None),
                                    lambda proceed: self.flashObject.as_onVehicleDeleteConfirmed(proceed, teamIdx))

    @staticmethod
    def py_onSaveSettings(settings):
        remodNames = sorted(g_config.OM.models)
        for idx, setObj in enumerate(settings.remods):
            OMSettings = g_config.settings['remods'][remodNames[idx]]
            for key in ('Player', 'Ally', 'Enemy'):
                OMSettings['swap%s' % key] = getattr(setObj.useFor, key.lower())
            for teamIdx, team in enumerate(('player', 'ally', 'enemy')):
                OMSettings['%sWhitelist' % team] = ','.join(setObj.whitelists[teamIdx])
        for idx, settingsArray in enumerate(settings.skins):
            for nameIdx, setObj in enumerate(settingsArray):
                for key in OM.tankGroups:
                    g_config.settings['skins%s' % ('', '_dynamic')[idx]][
                        sorted(g_config.OS.models[('static', 'dynamic')[idx]])[nameIdx]]['swap%s' % key] = getattr(
                        setObj.useFor, key.lower())
        for idx, prioritiesArray in enumerate(settings.priorities):
            for teamIdx, team in enumerate(('Player', 'Ally', 'Enemy')):
                g_config.OS.priorities[('static', 'dynamic')[idx]][team] = prioritiesArray[teamIdx]
        g_config.loadJson('skinsPriority', g_config.OS.priorities, g_config.configPath, True,
                          doPrint=g_config.data['isDebug'])
        g_config.loadJson('settings', g_config.settings, g_config.configPath, True, doPrint=g_config.data['isDebug'])
        g_config.update_data(g_config.data['isDebug'])
        g_currentPreviewVehicle.refreshModel()

    @staticmethod
    def py_onCreateRemod(settings):
        try:
            if not settings.name:
                SystemMessages.pushMessage('PYmods_SM' + g_config.i18n['UI_flash_remodCreate_name_empty'],
                                           SystemMessages.SM_TYPE.Warning)
                return
            if settings.vehicleName != RemodEnablerUI.py_getCurrentVehicleName():
                SystemMessages.pushMessage('PYmods_SM' + g_config.i18n['UI_flash_remodCreate_wrongVehicle'],
                                           SystemMessages.SM_TYPE.Warning)
                return
            from collections import OrderedDict
            data = OrderedDict()
            data['authorMessage'] = settings.message
            for teamIdx, team in enumerate(OM.tankGroups):
                data[team.lower() + 'Whitelist'] = ','.join(settings.whitelists[teamIdx])

            vDesc = g_hangarSpace._HangarSpace__space._ClientHangarSpace__vAppearance._VehicleAppearance__vDesc
            for key in TankPartNames.ALL + ('engine',):
                data[key] = OrderedDict()
            for key in TankPartNames.ALL:
                data[key]['undamaged'] = getattr(vDesc, key)['models']['undamaged']
            chassis = data['chassis']
            for key in ('traces', 'tracks', 'wheels', 'groundNodes', 'trackNodes', 'splineDesc', 'trackParams'):
                chassis[key] = str(vDesc.chassis[key])
            chassis['hullPosition'] = vDesc.chassis['hullPosition'].tuple()
            chassis['AODecals'] = []
            for decal in vDesc.chassis['AODecals']:
                decDict = {'transform': OrderedDict()}
                for strIdx in xrange(4):
                    decDict['transform']['row%s' % strIdx] = []
                    for colIdx in xrange(3):
                        decDict['transform']['row%s' % strIdx].append(decal.get(strIdx, colIdx))
            for key in ('wwsoundPC', 'wwsoundNPC'):
                chassis[key] = vDesc.chassis[key]
            pixieID = ''
            for key, value in g_cache._customEffects['exhaust'].iteritems():
                if value == vDesc.hull['customEffects'][0]._selectorDesc:
                    pixieID = key
                    break
            data['hull']['exhaust'] = {'nodes': ' '.join(vDesc.hull['customEffects'][0].nodes), 'pixie': pixieID}
            for ids in (('_gunEffects', 'effects'), ('_gunReloadEffects', 'reloadEffect')):
                for key, value in getattr(g_cache, ids[0]).items():
                    if value == vDesc.gun[ids[1]]:
                        data['gun'][ids[1]] = key
                        break
            exclMask = vDesc.type.camouflageExclusionMask
            if exclMask:
                camouflage = data['camouflage'] = OrderedDict()
                camouflage['exclusionMask'] = exclMask
                camouflage['tiling'] = vDesc.type.camouflageTiling
            for partName in TankPartNames.ALL[1:]:
                part = getattr(vDesc, partName)
                data[partName]['emblemSlots'] = []
                exclMask = part['camouflageExclusionMask']
                if exclMask:
                    camouflage = data[partName]['camouflage'] = OrderedDict()
                    camouflage['exclusionMask'] = exclMask
                    camouflage['tiling'] = part['camouflageTiling']
                for slot in part['emblemSlots']:
                    slotDict = OrderedDict()
                    for key in ('rayStart', 'rayEnd', 'rayUp'):
                        slotDict[key] = getattr(slot, key).tuple()
                    for key in ('size', 'hideIfDamaged', 'type', 'isMirrored', 'isUVProportional', 'emblemId'):
                        slotDict[key] = getattr(slot, key)
                    data[partName]['emblemSlots'].append(slotDict)
            data['engine']['wwsoundPC'] = vDesc.engine['wwsoundPC']
            data['engine']['wwsoundNPC'] = vDesc.engine['wwsoundNPC']
            g_config.loadJson(str(settings.name), data, g_config.configPath + 'remods/', True, False, sort_keys=False)
            g_config.update_data()
            SystemMessages.pushMessage(
                'PYmods_SM' + g_config.i18n['UI_flash_remodCreate_success'], SystemMessages.SM_TYPE.CustomizationForGold)
        except StandardError:
            SystemMessages.pushMessage(
                'PYmods_SM' + g_config.i18n['UI_flash_remodCreate_error'], SystemMessages.SM_TYPE.Warning)
            traceback.print_exc()

    @staticmethod
    def py_sendMessage(xmlName, action, status):
        SystemMessages.pushMessage(
            'PYmods_SM' + g_config.i18n['UI_flash_vehicle%s_%s' % (action, status)] + xmlName.join(
                ('<b>', '</b>.')), SystemMessages.SM_TYPE.CustomizationForGold)

    def onWindowClose(self):
        self.py_onModelRestore()
        self.destroy()

    @staticmethod
    def py_printLog(*args):
        for arg in args:
            print arg


def lobbyKeyControl(event):
    if not event.isKeyDown() or g_config.isMSAWindowOpen:
        return
    if (g_config.OM.enabled or g_config.OS.enabled) and PYmodsCore.checkKeys(g_config.data['ChangeViewHotkey']):
        while True:
            newModeNum = g_config.possibleModes.index(g_config.data['currentMode']) + 1
            if newModeNum >= len(g_config.possibleModes):
                newModeNum = 0
            g_config.data['currentMode'] = g_config.possibleModes[newModeNum]
            if g_config.data.get(g_config.data['currentMode'], True):
                break
        if g_config.data['isDebug']:
            print 'RemodEnabler: Changing display mode to %s' % g_config.data['currentMode']
        SystemMessages.pushMessage(
            'PYmods_SM' + g_config.i18n['UI_mode'] + g_config.i18n['UI_mode_' + g_config.data['currentMode']].join(
                ('<b>', '</b>.')),
            SystemMessages.SM_TYPE.Warning)
        g_currentPreviewVehicle.refreshModel()
    if PYmodsCore.checkKeys(g_config.data['CollisionHotkey']):
        if g_config.data['collisionComparisonEnabled']:
            g_config.data['collisionComparisonEnabled'] = False
            if g_config.data['isDebug']:
                print 'RemodEnabler: Disabling collision displaying'
            SystemMessages.pushMessage('PYmods_SM' + g_config.i18n['UI_disableCollisionComparison'],
                                       SystemMessages.SM_TYPE.CustomizationForGold)
        elif g_config.data['collisionEnabled']:
            g_config.data['collisionEnabled'] = False
            g_config.data['collisionComparisonEnabled'] = True
            if g_config.data['isDebug']:
                print 'RemodEnabler: Enabling collision display comparison mode'
            SystemMessages.pushMessage('PYmods_SM' + g_config.i18n['UI_enableCollisionComparison'],
                                       SystemMessages.SM_TYPE.CustomizationForGold)
        else:
            g_config.data['collisionEnabled'] = True
            if g_config.data['isDebug']:
                print 'RemodEnabler: Enabling collision display'
            SystemMessages.pushMessage('PYmods_SM' + g_config.i18n['UI_enableCollision'],
                                       SystemMessages.SM_TYPE.CustomizationForGold)
        g_currentPreviewVehicle.refreshModel()
    if PYmodsCore.checkKeys(g_config.data['DynamicSkinHotkey']):
        enabled = g_config.data['dynamicSkinEnabled']
        g_config.data['dynamicSkinEnabled'] = not enabled
        SystemMessages.pushMessage(
            'PYmods_SM' + g_config.i18n['UI_%sableDynamicSkin' % ('en' if not enabled else 'dis')],
            SystemMessages.SM_TYPE.CustomizationForGold)
        g_currentPreviewVehicle.refreshModel()
    if g_config.OM.enabled and PYmodsCore.checkKeys(g_config.data['SwitchRemodHotkey']):
        if g_config.data['currentMode'] != 'remod':
            curTankType = g_config.data['currentMode'].capitalize()
            snameList = sorted(g_config.OM.models.keys()) + ['']
            selected = g_config.OM.selected[curTankType]
            vehName = g_config.curVehicleName
            if selected.get(vehName) not in snameList:
                snameIdx = 0
            else:
                snameIdx = snameList.index(selected[vehName]) + 1
                if snameIdx == len(snameList):
                    snameIdx = 0
            for Idx in xrange(snameIdx, len(snameList)):
                curPRecord = g_config.OM.models.get(snameList[Idx])
                if snameList[Idx] and vehName not in curPRecord.whitelists[curTankType]:
                    continue
                if vehName in selected:
                    selected[vehName] = getattr(curPRecord, 'name', '')
                g_config.loadJson('remodsCache', g_config.OM.selected, g_config.configPath, True,
                                  doPrint=g_config.data['isDebug'])
                break
        else:
            snameList = sorted(g_config.OM.models.keys())
            if g_config.OM.selected['Remod'] not in snameList:
                snameIdx = 0
            else:
                snameIdx = snameList.index(g_config.OM.selected['Remod']) + 1
                if snameIdx == len(snameList):
                    snameIdx = 0
            sname = snameList[snameIdx]
            g_config.OM.selected['Remod'] = sname
            g_config.loadJson('remodsCache', g_config.OM.selected, g_config.configPath, True,
                              doPrint=g_config.data['isDebug'])
        g_currentPreviewVehicle.refreshModel()


def inj_hkKeyEvent(event):
    LobbyApp = g_appLoader.getDefLobbyApp()
    try:
        if LobbyApp and g_config.data['enabled']:
            lobbyKeyControl(event)
    except StandardError:
        print 'RemodEnabler: ERROR at inj_hkKeyEvent'
        traceback.print_exc()


InputHandler.g_instance.onKeyDown += inj_hkKeyEvent
InputHandler.g_instance.onKeyUp += inj_hkKeyEvent
g_config = _Config()
