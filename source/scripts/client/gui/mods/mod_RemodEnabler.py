# -*- coding: utf-8 -*-
import binascii
import datetime
import gc
import time

import GUI
import Math
import ResMgr

import BigWorld
import Keys
import PYmodsCore
import SoundGroups
import copy
import glob
import material_kinds
import os
import pprint
import shutil
import traceback
import weakref
from Avatar import PlayerAvatar
from AvatarInputHandler import mathUtils
from CurrentVehicle import _CurrentPreviewVehicle, g_currentPreviewVehicle, g_currentVehicle
from Vehicle import Vehicle
from adisp import AdispException, async, process
from collections import namedtuple
from functools import partial
from gui import InputHandler, SystemMessages
from gui.ClientHangarSpace import _VehicleAppearance
from gui.Scaleform.daapi.view.battle.classic.battle_end_warning_panel import _WWISE_EVENTS
from gui.Scaleform.daapi.view.battle.shared.minimap.settings import MINIMAP_ATTENTION_SOUND_ID
from gui.Scaleform.daapi.view.lobby.LobbyView import LobbyView
from gui.Scaleform.daapi.view.login.LoginView import LoginView
from gui.Scaleform.daapi.view.meta.LoginQueueWindowMeta import LoginQueueWindowMeta
from gui.Scaleform.framework import GroupedViewSettings, ScopeTemplates, ViewSettings, ViewTypes, g_entitiesFactories
from gui.Scaleform.framework.entities.abstract.AbstractWindowView import AbstractWindowView
from gui.app_loader.loader import g_appLoader
from helpers import getClientVersion
from items.vehicles import g_cache
from vehicle_systems import appearance_cache
from vehicle_systems.CompoundAppearance import CompoundAppearance
from vehicle_systems.tankStructure import TankNodeNames, TankPartNames
from zipfile import ZipFile

res = ResMgr.openSection('../paths.xml')
sb = res['Paths']
vl = sb.values()[0]
if vl is not None and not hasattr(BigWorld, 'curCV'):
    BigWorld.curCV = vl.asString

EmblemSlot = namedtuple('EmblemSlot', [
    'rayStart', 'rayEnd', 'rayUp', 'size', 'hideIfDamaged', 'type', 'isMirrored', 'isUVProportional', 'emblemId'])


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
                _config.ID, confDict['type'], ' '.join(('player', 'clan', 'inscription', 'insigniaOnGun')))
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
        self.selected = {'Player': {},
                         'Ally': {},
                         'Enemy': {},
                         'Remod': ''}


class OMDescriptor(object):
    def __init__(self):
        self.name = ''
        self.authorMessage = ''
        self.whitelists = {'Player': set(),
                           'Ally': set(),
                           'Enemy': set()}
        self.data = {'chassis': {'undamaged': '',
                                 'AODecals': None,
                                 'hullPosition': None,
                                 'wwsoundPC': '',
                                 'wwsoundNPC': ''},
                     'hull': {'undamaged': '',
                              'emblemSlots': [],
                              'camouflage': {'exclusionMask': '',
                                             'tiling': (1.0, 1.0, 0.0, 0.0)},
                              'exhaust': {'nodes': [],
                                          'pixie': ''}},
                     'turret': {'undamaged': '',
                                'emblemSlots': [],
                                'camouflage': {'exclusionMask': '',
                                               'tiling': (1.0, 1.0, 0.0, 0.0)}},
                     'gun': {'undamaged': '',
                             'emblemSlots': [],
                             'camouflage': {'exclusionMask': '',
                                            'tiling': (1.0, 1.0, 0.0, 0.0)},
                             'effects': '',
                             'reloadEffect': ''},
                     'engine': {'wwsoundPC': '',
                                'wwsoundNPC': ''},
                     'common': {'camouflage': {'exclusionMask': '',
                                               'tiling': (1.0, 1.0, 0.0, 0.0)}}}


class OS(object):
    def __init__(self):
        self.models = {'static': {}, 'dynamic': {}}
        self.enabled = True
        self.priorities = {skinType: {'Player': [],
                                      'Ally': [],
                                      'Enemy': []} for skinType in self.models}


class OSDescriptor(object):
    def __init__(self):
        self.name = ''
        self.whitelist = set()


class _Config(PYmodsCore._Config):
    def __init__(self):
        super(_Config, self).__init__('%(mod_ID)s')
        self.version = '2.9.9 (%(file_compile_date)s)'
        self.author = '%s (thx to atacms)' % self.author
        self.possibleModes = ['player', 'ally', 'enemy', 'remod']
        self.defaultSkinConfig = {'static': {'enabled': True,
                                             'swapPlayer': True,
                                             'swapAlly': True,
                                             'swapEnemy': True},
                                  'dynamic': {'enabled': True,
                                              'swapPlayer': False,
                                              'swapAlly': True,
                                              'swapEnemy': True}}
        self.defaultRemodConfig = {'enabled': True,
                                   'swapPlayer': True,
                                   'swapAlly': True,
                                   'swapEnemy': True}
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
        super(_Config, self).apply_settings(settings)
        if self.isModAdded:
            BigWorld.g_modsListApi.updateMod('CamoSelectorUI', enabled=self.data['enabled'])

    # noinspection PyUnresolvedReferences
    def update_data(self, doPrint=False):
        super(_Config, self).update_data()
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
                    continue
                self.OM.models[sname] = pRecord = OMDescriptor()
                pRecord.name = sname
                pRecord.authorMessage = confDict.get('authorMessage', '')
                for tankType in OM.tankGroups:
                    selected = self.OM.selected[tankType]
                    swapKey = 'swap%s' % tankType
                    WLKey = '%sWhitelist' % tankType.lower()
                    whiteStr = settingsDict.setdefault(WLKey, confDict.get(WLKey, ''))
                    if not settingsDict.setdefault(swapKey, confDict.get(swapKey, self.defaultRemodConfig[swapKey])):
                        if self.data['isDebug']:
                            print '%s: %s swapping in %s disabled.' % (self.ID, tankType.lower(), sname)
                        for xmlName in selected:
                            if sname == selected[xmlName]:
                                selected[xmlName] = None
                        continue
                    templist = filter(None, map(lambda x: x.strip(), whiteStr.split(',')))
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
                print '%s: no configs found, model module standing down.' % self.ID
                self.OM.enabled = False
                self.loadJson('remodsCache', self.OM.selected, self.configPath, True)
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
                self.loadJson('remodsCache', self.OM.selected, self.configPath, True)
        else:
            print '%s: no remods found, model module standing down.' % self.ID
            self.OM.enabled = False
            self.loadJson('remodsCache', self.OM.selected, self.configPath, True)
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
                for sname in [] if skinDirSect is None else skinDirSect.keys():
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
                    for curNation in [] if vehiclesDirSect is None else vehiclesDirSect.keys():
                        nationDirPath = vehiclesDirPath + curNation + '/'
                        nationDirSect = ResMgr.openSection(nationDirPath)
                        for vehicleName in [] if nationDirSect is None else nationDirSect.keys():
                            vehDirPath = nationDirPath + vehicleName + '/'
                            vehDirSect = ResMgr.openSection(vehDirPath)
                            tracksDirPath = vehDirPath + 'tracks/'
                            tracksDirSect = ResMgr.openSection(tracksDirPath)
                            if not (texName for texName in ([] if vehDirSect is None else vehDirSect.keys()) if
                                    texName.endswith('.dds')) and not (texName for texName in (
                                    [] if tracksDirSect is None else tracksDirSect.keys()) if texName.endswith('.dds')):
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
        self.loadJson('skinsPriority', self.OS.priorities, self.configPath, True)
        self.loadJson('settings', self.settings, self.configPath, True)

    def do_config(self):
        super(_Config, self).do_config()
        BigWorld.g_modsListApi.addMod(
            id='RemodEnablerUI', name=self.i18n['UI_flash_header'],
            description=self.i18n['UI_flash_header_tooltip'],
            icon='gui/flash/RemodEnabler.png',
            enabled=self.data['enabled'], login=True, lobby=True,
            callback=lambda: g_appLoader.getDefLobbyApp().loadView(
                'RemodEnablerUI') if self.loadingProxy is None else None)
        self.isModAdded = True
        g_entitiesFactories.addSettings(
            ViewSettings('RemodEnablerUI', RemodEnablerUI, 'RemodEnabler.swf', ViewTypes.WINDOW, None,
                         ScopeTemplates.GLOBAL_SCOPE, False))
        g_entitiesFactories.addSettings(
            GroupedViewSettings('RemodEnablerLoading', RemodEnablerLoading, 'LoginQueueWindow.swf', ViewTypes.TOP_WINDOW,
                                '', None, ScopeTemplates.DEFAULT_SCOPE))


def skinsPresenceCheck():
    global skinsFound
    dirSect = ResMgr.openSection('vehicles/skins/textures/')
    if dirSect is not None and dirSect.keys():
        skinsFound = True


_config = _Config()
_config.load()
texReplaced = False
skinsFound = False
skinsPresenceCheck()
clientIsNew = True
skinsModelsMissing = True
needToReReadSkinsModels = False
modelsDir = BigWorld.curCV + '/vehicles/skins/models/'
skinVehNamesLDict = {}


class RemodEnablerLoading(LoginQueueWindowMeta):
    def __init__(self):
        super(RemodEnablerLoading, self).__init__()
        self.lines = []
        self.curPercentage = 0
        _config.loadingProxy = weakref.proxy(self)

    def _populate(self):
        super(RemodEnablerLoading, self)._populate()
        self.__initTexts()

    def __initTexts(self):
        self.updateTitle(_config.i18n['UI_loading_header_CRC32'])
        self.updateMessage()
        self.as_setCancelLabelS(_config.i18n['UI_loading_bugReport'])
        self.as_showAutoLoginBtnS(False)

    def updateTitle(self, title):
        self.as_setTitleS(title)

    def updateMessage(self):
        self.as_setMessageS(''.join(line.join(("<p align='left'>", "</p>")) for line in self.lines))

    def addLine(self, line):
        if len(self.lines) == 8:
            del self.lines[0]
        self.lines.append(line)
        self.updateMessage()

    def onComplete(self):
        self.lines[-1] += _config.i18n['UI_loading_done'].join(("<font color='#00FF00'>", '</font>'))
        self.updateMessage()
        SoundGroups.g_instance.playSound2D(MINIMAP_ATTENTION_SOUND_ID)

    def addBar(self, pkgName):
        self.curPercentage = 0
        self.addLine(_config.i18n['UI_loading_package'] % pkgName)
        self.addLine(self.createBar())

    def createBar(self):
        red = 510 - 255 * self.curPercentage / 50
        green = 255 * self.curPercentage / 50
        return "<font color='#007BFF' face='Arial'>%s</font><font color='#{0:0>2x}{1:0>2x}00'>  %s%%</font>".format(
            red if red < 255 else 255, green if green < 255 else 255) % (
                   u'\u2593' * (self.curPercentage / 4) + u'\u2591' * (25 - self.curPercentage / 4), self.curPercentage)

    def updatePercentage(self, percentage):
        self.curPercentage = percentage
        self.lines[-1] = self.createBar()
        self.updateMessage()

    def onBarComplete(self):
        del self.lines[-1]
        self.onComplete()

    def onTryClosing(self):
        return False

    def onCancelClick(self):
        BigWorld.wg_openWebBrowser('http://www.koreanrandom.com/forum/topic/22800-')

    def onWindowClose(self):
        _config.loadingProxy = None
        self.destroy()


class RemodEnablerUI(AbstractWindowView):
    def _populate(self):
        super(RemodEnablerUI, self)._populate()
        self.modeBackup = _config.data['currentMode']
        self.remodBackup = _config.OM.selected['Remod']
        if self._isDAAPIInited():
            self.createData()

    def createData(self):
        _config.update_data(_config.data['isDebug'])
        texts = {
            'header': {
                'main': _config.i18n['UI_flash_header'],
                'remodSetup': _config.i18n['UI_flash_remodSetupBtn'],
                'remodWL': _config.i18n['UI_flash_remodWLBtn'],
                'skinSetup': _config.i18n['UI_flash_skinSetupBtn'],
                'priorities': _config.i18n['UI_flash_skinPriorityBtn']},
            'remodSetupBtn': _config.i18n['UI_flash_remodSetupBtn'],
            'remodWLBtn': _config.i18n['UI_flash_remodWLBtn'],
            'skinsSetupBtn': _config.i18n['UI_flash_skinSetupBtn'],
            'skinsPriorityBtn': _config.i18n['UI_flash_skinPriorityBtn'],
            'skinTypes': [_config.i18n['UI_flash_skinType_%s' % skinType] for skinType in ('static', 'dynamic')],
            'teams': [_config.i18n['UI_flash_team_%s' % team] for team in ('player', 'ally', 'enemy')],
            'remodNames': [],
            'skinNames': [[], []],
            'whiteList': {'addBtn': _config.i18n['UI_flash_whiteList_addBtn'],
                          'delLabel': _config.createLabel('whiteList_del', 'flash'),
                          'defStr': _config.i18n['UI_flash_whiteDropdown_default']},
            'useFor': {'header': _config.createLabel('useFor_header', 'flash'),
                       'ally': _config.createLabel('useFor_ally', 'flash'),
                       'enemy': _config.createLabel('useFor_enemy', 'flash'),
                       'player': _config.createLabel('useFor_player', 'flash')},
            'backBtn': _config.i18n['UI_flash_backBtn'],
            'saveBtn': _config.i18n['UI_flash_saveBtn']
        }
        settings = {
            'remods': [],
            'skins': [[], []],
            'priorities': [[_config.OS.priorities[sType][team] for team in ('Player', 'Ally', 'Enemy')] for sType in
                           ('static', 'dynamic')],
            'whitelists': [],
            'isInHangar': _config.data['isInHangar']
        }
        for sname in sorted(_config.OM.models):
            OMDesc = _config.OM.models[sname]
            OMSettings = _config.settings['remods'][sname]
            texts['remodNames'].append(sname)
            settings['remods'].append({'useFor': {key.lower(): OMSettings['swap%s' % key] for key in OM.tankGroups},
                                       'whitelists': [OMDesc.whitelists[team] for team in OM.tankGroups]})
        for idx, skinType in enumerate(('', '_dynamic')):
            skins = _config.settings['skins%s' % skinType]
            for sname in sorted(_config.OS.models['static' if not skinType else 'dynamic']):
                sDesc = skins[sname]
                texts['skinNames'][idx].append(sname)
                settings['skins'][idx].append({'useFor': {k.lower(): sDesc['swap%s' % k] for k in OM.tankGroups}})
        self.flashObject.as_updateData(texts, settings)
        self.flashObject.as_initMainMenu()

    @staticmethod
    def py_onShowRemod(remodIdx):
        _config.data['currentMode'] = 'remod'
        _config.OM.selected['Remod'] = sorted(_config.OM.models)[remodIdx]
        g_currentPreviewVehicle.refreshModel()

    def py_onModelRestore(self):
        _config.data['currentMode'] = self.modeBackup
        _config.OM.selected['Remod'] = self.remodBackup
        g_currentPreviewVehicle.refreshModel()

    @staticmethod
    def py_getCurrentVehicleName():
        if g_currentPreviewVehicle.isPresent():
            vDesc = g_currentPreviewVehicle.item.descriptor
        elif g_currentVehicle.isPresent():
            vDesc = g_currentVehicle.item.descriptor
        else:
            raise AttributeError('g_currentVehicle.item.descriptor not found')
        return vDesc.name.split(':')[1].lower()

    def py_onRequestVehicleDelete(self):
        from gui import DialogsInterface
        from gui.Scaleform.daapi.view.dialogs import SimpleDialogMeta, I18nConfirmDialogButtons

        DialogsInterface.showDialog(SimpleDialogMeta(_config.i18n['UI_flash_WLVehDelete_header'],
                                                     _config.i18n['UI_flash_WLVehDelete_text'],
                                                     I18nConfirmDialogButtons('common/confirm'), None),
                                    self.flashObject.as_onVehicleDeleteConfirmed)

    @staticmethod
    def py_onSaveSettings(settings):
        remodNames = sorted(_config.OM.models)
        for idx, setObj in enumerate(settings.remods):
            OMSettings = _config.settings['remods'][remodNames[idx]]
            for key in ('Player', 'Ally', 'Enemy'):
                OMSettings['swap%s' % key] = getattr(setObj.useFor, key.lower())
            for teamIdx, team in enumerate(('player', 'ally', 'enemy')):
                OMSettings['%sWhitelist' % team] = ','.join(setObj.whitelists[teamIdx])
        for idx, settingsArray in enumerate(settings.skins):
            for nameIdx, setObj in enumerate(settingsArray):
                for key in OM.tankGroups:
                    _config.settings['skins%s' % ('', '_dynamic')[idx]][
                        sorted(_config.OS.models[('static', 'dynamic')[idx]])[nameIdx]]['swap%s' % key] = getattr(
                        setObj.useFor, key.lower())
        for idx, prioritiesArray in enumerate(settings.priorities):
            for teamIdx, team in enumerate(('Player', 'Ally', 'Enemy')):
                _config.OS.priorities[('static', 'dynamic')[idx]][team] = prioritiesArray[teamIdx]
        _config.loadJson('skinsPriority', _config.OS.priorities, _config.configPath, True)
        _config.loadJson('settings', _config.settings, _config.configPath, True)
        _config.update_data(_config.data['isDebug'])
        g_currentPreviewVehicle.refreshModel()

    @staticmethod
    def py_sendMessage(xmlName, action, status):
        SystemMessages.pushMessage(
            'PYmods_SM' + _config.i18n['UI_flash_vehicle%s_%s' % (action, status)] + xmlName.join(
                ('<b>', '</b>.')), SystemMessages.SM_TYPE.CustomizationForGold)

    def onWindowClose(self):
        self.py_onModelRestore()
        self.destroy()

    @staticmethod
    def py_printLog(*args):
        for arg in args:
            print arg


def CRC32_from_file(filename, localPath):
    buf = str(ResMgr.openSection(filename).asBinary)
    buf = binascii.crc32(buf) & 0xFFFFFFFF & localPath.__hash__()
    return buf


@async
@process
def skinCRC32All(callback):
    global texReplaced, skinsFound, skinVehNamesLDict
    CRC32cache = _config.skinsCache['CRC32']
    skinsPath = 'vehicles/skins/textures/'
    dirSect = ResMgr.openSection(skinsPath)
    if dirSect is not None and dirSect.keys():
        skinsFound = True
        print 'RemodEnabler: listing %s for CRC32' % skinsPath
        _config.loadingProxy.addLine(_config.i18n['UI_loading_skins'])
        CRC32 = 0
        resultList = []
        for skin in dirSect.keys():
            _config.loadingProxy.addLine(_config.i18n['UI_loading_skinPack'] % os.path.basename(skin))
            skinCRC32 = 0
            skinSect = ResMgr.openSection(skinsPath + skin + '/vehicles/')
            for nation in [] if skinSect is None else skinSect.keys():
                nationCRC32 = 0
                nationSect = ResMgr.openSection(skinsPath + skin + '/vehicles/' + nation)
                for vehicleName in [] if nationSect is None else nationSect.keys():
                    vehicleCRC32 = 0
                    skinVehNamesLDict.setdefault(vehicleName.lower(), []).append(skin)
                    vehicleSect = ResMgr.openSection(skinsPath + skin + '/vehicles/' + nation + '/' + vehicleName)
                    for texture in [] if vehicleSect is None else (texName for texName in vehicleSect.keys() if
                                                                   texName.endswith('.dds')):
                        localPath = 'vehicles/' + nation + '/' + vehicleName + '/' + texture
                        texPath = skinsPath + skin + '/' + localPath
                        textureCRC32 = CRC32_from_file(texPath, localPath)
                        vehicleCRC32 ^= textureCRC32
                    nationCRC32 ^= vehicleCRC32
                    yield doFuncCall()
                skinCRC32 ^= nationCRC32
            _config.loadingProxy.onComplete()
            if skinCRC32 in resultList:
                print 'RemodEnabler: deleting duplicate skins pack:', skin.replace(os.sep, '/')
                shutil.rmtree(skin)
                continue
            CRC32 ^= skinCRC32
            resultList.append(skinCRC32)
        if CRC32cache is not None and str(CRC32) == CRC32cache:
            print 'RemodEnabler: skins textures were not changed'
        else:
            if CRC32cache is None:
                print 'RemodEnabler: skins textures were reinstalled (or you deleted the CRC32 cache)'
            else:
                print 'RemodEnabler: skins textures were changed'
            _config.skinsCache['CRC32'] = str(CRC32)
            texReplaced = True
    else:
        print 'RemodEnabler: skins folder is empty'
    BigWorld.callback(0.0, partial(callback, True))


@async
def modelsCheck(callback):
    global clientIsNew, skinsModelsMissing, needToReReadSkinsModels
    lastVersion = _config.skinsCache['version']
    if lastVersion:
        if getClientVersion() == lastVersion:
            clientIsNew = False
        else:
            print 'RemodEnabler: skins client version changed'
    else:
        print 'RemodEnabler: skins client version cache not found'

    if os.path.isdir(modelsDir):
        if len(glob.glob(modelsDir + '*')):
            skinsModelsMissing = False
        else:
            print 'RemodEnabler: skins models dir is empty'
    else:
        print 'RemodEnabler: skins models dir not found'
    needToReReadSkinsModels = skinsFound and (clientIsNew or skinsModelsMissing or texReplaced)
    if skinsFound and clientIsNew:
        if os.path.isdir(modelsDir):
            shutil.rmtree(modelsDir)
        _config.skinsCache['version'] = getClientVersion()
    if skinsFound and not os.path.isdir(modelsDir):
        os.makedirs(modelsDir)
    elif not skinsFound and os.path.isdir(modelsDir):
        print 'RemodEnabler: no skins found, deleting %s' % modelsDir
        shutil.rmtree(modelsDir)
    elif texReplaced and os.path.isdir(modelsDir):
        shutil.rmtree(modelsDir)
    _config.loadJson('skinsCache', _config.skinsCache, _config.configPath, True)
    BigWorld.callback(0.0, partial(callback, True))


@async
@process
def modelsProcess(callback):
    if needToReReadSkinsModels:
        _config.loadingProxy.updateTitle(_config.i18n['UI_loading_header_models_unpack'])
        SoundGroups.g_instance.playSound2D(_WWISE_EVENTS.APPEAR)
        modelFileFormats = ('.model', '.visual', '.visual_processed')
        print 'RemodEnabler: unpacking vehicle packages'
        for vehPkgPath in glob.glob('./res/packages/vehicles*.pkg') + glob.glob('./res/packages/shared_content*.pkg'):
            completionPercentage = 0
            filesCnt = 0
            _config.loadingProxy.addBar(os.path.basename(vehPkgPath))
            vehPkg = ZipFile(vehPkgPath)
            fileNamesList = filter(
                lambda x: x.startswith('vehicles') and 'normal' in x and os.path.splitext(x)[1] in modelFileFormats,
                vehPkg.namelist())
            allFilesCnt = len(fileNamesList)
            for fileNum, memberFileName in enumerate(fileNamesList):
                if not needToReReadSkinsModels:
                    continue
                for skinName in skinVehNamesLDict.get(os.path.normpath(memberFileName).split('\\')[2].lower(), []):
                    processMember(memberFileName, skinName)
                    filesCnt += 1
                    if not filesCnt % 25:
                        yield doFuncCall()
                currentPercentage = int(100 * float(fileNum) / float(allFilesCnt))
                if currentPercentage != completionPercentage:
                    completionPercentage = currentPercentage
                    _config.loadingProxy.updatePercentage(completionPercentage)
                    yield doFuncCall()
            vehPkg.close()
            _config.loadingProxy.onBarComplete()
    BigWorld.callback(0.0, partial(callback, True))


@async
def doFuncCall(callback):
    BigWorld.callback(0.0, partial(callback, None))


# noinspection PyPep8,PyPep8
def processMember(memberFileName, skinName):
    skinDir = modelsDir.replace('%s/' % BigWorld.curCV, '') + skinName + '/'
    texDir = skinDir.replace('models', 'textures')
    skinsSign = 'vehicles/skins/'
    if '.model' in memberFileName:
        oldModel = ResMgr.openSection(memberFileName)
        newModelPath = skinDir + memberFileName
        curModel = ResMgr.openSection(newModelPath, True)
        curModel.copy(oldModel)
        if curModel is None:
            print skinDir + memberFileName
        if curModel.has_key('parent') and skinsSign not in curModel['parent'].asString:
            curParent = skinDir + curModel['parent'].asString
            curModel.writeString('parent', curParent.replace('\\', '/'))
        if skinsSign not in curModel['nodefullVisual'].asString:
            curVisual = skinDir + curModel['nodefullVisual'].asString
            curModel.writeString('nodefullVisual', curVisual.replace('\\', '/'))
        curModel.save()
    elif '.visual' in memberFileName:
        oldVisual = ResMgr.openSection(memberFileName)
        newVisualPath = skinDir + memberFileName
        curVisual = ResMgr.openSection(newVisualPath, True)
        curVisual.copy(oldVisual)
        for curName, curSect in curVisual.items():
            if curName != 'renderSet':
                continue
            for curSubName, curSubSect in curSect['geometry'].items():
                if curSubName != 'primitiveGroup':
                    continue
                for curPrimName, curProp in curSubSect['material'].items():
                    if curPrimName != 'property' or not curProp.has_key('Texture'):
                        continue
                    curTexture = curProp['Texture'].asString
                    if skinsSign not in curTexture and ResMgr.isFile(texDir + curTexture):
                        curDiff = texDir + curTexture
                        curProp.writeString('Texture', curDiff.replace('\\', '/'))
                    elif skinsSign in curTexture and not ResMgr.isFile(curTexture):
                        curDiff = curTexture.replace(texDir, '')
                        curProp.writeString('Texture', curDiff.replace('\\', '/'))

        curVisual.writeString('primitivesName', os.path.splitext(memberFileName)[0])
        curVisual.save()


@process
def skinCaller():
    if skinsFound:
        lobbyApp = g_appLoader.getDefLobbyApp()
        if lobbyApp is not None:
            lobbyApp.loadView('RemodEnablerLoading')
        else:
            return
        jobStartTime = time.time()
        try:
            yield skinCRC32All()
            yield modelsCheck()
            yield modelsProcess()
        except AdispException:
            traceback.print_exc()
        print 'RemodEnabler: total models check time:', datetime.timedelta(seconds=round(time.time() - jobStartTime))
        gc.collect()
        BigWorld.callback(1, partial(SoundGroups.g_instance.playSound2D, 'enemy_sighted_for_team'))
        BigWorld.callback(2, _config.loadingProxy.onWindowClose)


def new_populate(self):
    old_populate(self)
    _config.data['isInHangar'] = False
    if _config.data['enabled']:
        BigWorld.callback(3.0, skinCaller)


old_populate = LoginView._populate
LoginView._populate = new_populate


def lobbyKeyControl(event):
    try:
        if event.isKeyDown() and not _config.isMSAWindowOpen:
            if (_config.OM.enabled or _config.OS.enabled) and PYmodsCore.checkKeys(_config.data['ChangeViewHotkey']):
                while True:
                    newModeNum = _config.possibleModes.index(_config.data['currentMode']) + 1
                    if newModeNum >= len(_config.possibleModes):
                        newModeNum = 0
                    _config.data['currentMode'] = _config.possibleModes[newModeNum]
                    if _config.data.get(_config.data['currentMode'], True):
                        break
                if _config.data['isDebug']:
                    print 'RemodEnabler: Changing display mode to %s' % _config.data['currentMode']
                SystemMessages.pushMessage(
                    'PYmods_SM' + _config.i18n['UI_mode'] + _config.i18n['UI_mode_' + _config.data['currentMode']].join(
                        ('<b>', '</b>.')),
                    SystemMessages.SM_TYPE.Warning)
                g_currentPreviewVehicle.refreshModel()
            if PYmodsCore.checkKeys(_config.data['CollisionHotkey']):
                if _config.data['collisionComparisonEnabled']:
                    _config.data['collisionComparisonEnabled'] = False
                    if _config.data['isDebug']:
                        print 'RemodEnabler: Disabling collision displaying'
                    SystemMessages.pushMessage('PYmods_SM' + _config.i18n['UI_disableCollisionComparison'],
                                               SystemMessages.SM_TYPE.CustomizationForGold)
                elif _config.data['collisionEnabled']:
                    _config.data['collisionEnabled'] = False
                    _config.data['collisionComparisonEnabled'] = True
                    if _config.data['isDebug']:
                        print 'RemodEnabler: Enabling collision display comparison mode'
                    SystemMessages.pushMessage('PYmods_SM' + _config.i18n['UI_enableCollisionComparison'],
                                               SystemMessages.SM_TYPE.CustomizationForGold)
                else:
                    _config.data['collisionEnabled'] = True
                    if _config.data['isDebug']:
                        print 'RemodEnabler: Enabling collision display'
                    SystemMessages.pushMessage('PYmods_SM' + _config.i18n['UI_enableCollision'],
                                               SystemMessages.SM_TYPE.CustomizationForGold)
                g_currentPreviewVehicle.refreshModel()
            if PYmodsCore.checkKeys(_config.data['DynamicSkinHotkey']):
                enabled = _config.data['dynamicSkinEnabled']
                _config.data['dynamicSkinEnabled'] = not enabled
                SystemMessages.pushMessage(
                    'PYmods_SM' + _config.i18n['UI_%sableDynamicSkin' % ('en' if not enabled else 'dis')],
                    SystemMessages.SM_TYPE.CustomizationForGold)
                g_currentPreviewVehicle.refreshModel()
            if PYmodsCore.checkKeys([Keys.KEY_INSERT]):
                if g_currentPreviewVehicle.isPresent():
                    vDesc = g_currentPreviewVehicle.item.descriptor
                elif g_currentVehicle.isPresent():
                    vDesc = g_currentVehicle.item.descriptor
                else:
                    raise AttributeError('g_currentVehicle.item.descriptor not found')
                if _config.OMDesc is None and _config.data['isDebug']:
                    printOldConfigs(vDesc)
            if _config.OM.enabled and PYmodsCore.checkKeys(_config.data['SwitchRemodHotkey']):
                if _config.data['currentMode'] != 'remod':
                    curTankType = _config.data['currentMode'].capitalize()
                    snameList = sorted(_config.OM.models.keys()) + ['']
                    selected = _config.OM.selected[curTankType]
                    vehName = _config.curVehicleName
                    if selected.get(vehName) not in snameList:
                        snameIdx = 0
                    else:
                        snameIdx = snameList.index(selected[vehName]) + 1
                        if snameIdx == len(snameList):
                            snameIdx = 0
                    for Idx in xrange(snameIdx, len(snameList)):
                        curPRecord = _config.OM.models.get(snameList[Idx])
                        if snameList[Idx] and vehName not in curPRecord.whitelists[curTankType]:
                            continue
                        if vehName in selected:
                            selected[vehName] = getattr(curPRecord, 'name', '')
                        _config.loadJson('remodsCache', _config.OM.selected, _config.configPath, True)
                        break
                else:
                    snameList = sorted(_config.OM.models.keys())
                    if _config.OM.selected['Remod'] not in snameList:
                        snameIdx = 0
                    else:
                        snameIdx = snameList.index(_config.OM.selected['Remod']) + 1
                        if snameIdx == len(snameList):
                            snameIdx = 0
                    sname = snameList[snameIdx]
                    _config.OM.selected['Remod'] = sname
                    _config.loadJson('remodsCache', _config.OM.selected, _config.configPath, True)
                g_currentPreviewVehicle.refreshModel()
    except StandardError:
        traceback.print_exc()


def inj_hkKeyEvent(event):
    LobbyApp = g_appLoader.getDefLobbyApp()
    try:
        if LobbyApp and _config.data['enabled']:
            lobbyKeyControl(event)
    except StandardError:
        print 'RemodEnabler: ERROR at inj_hkKeyEvent\n%s' % traceback.print_exc()


InputHandler.g_instance.onKeyDown += inj_hkKeyEvent
InputHandler.g_instance.onKeyUp += inj_hkKeyEvent


def OM_find(xmlName, isPlayerVehicle, isAlly, currentMode='battle'):
    _config.OMDesc = None
    _config.OSDesc = dict.fromkeys(_config.OSDesc, None)
    if not _config.OM.enabled:
        return
    curTankType = 'Player' if isPlayerVehicle else 'Ally' if isAlly else 'Enemy'
    selected = _config.OM.selected
    if currentMode != 'remod':
        snameList = sorted(_config.OM.models.keys()) + ['']
        if selected[curTankType].get(xmlName) not in snameList:
            snameIdx = 0
        else:
            snameIdx = snameList.index(selected[curTankType][xmlName])
        for Idx in xrange(snameIdx, len(snameList)):
            curPRecord = _config.OM.models.get(snameList[Idx])
            if snameList[Idx] and xmlName not in curPRecord.whitelists[curTankType]:
                continue
            else:
                if xmlName in selected[curTankType]:
                    selected[curTankType][xmlName] = getattr(curPRecord, 'name', '')
                _config.OMDesc = curPRecord
                break

        # noinspection PyUnboundLocalVariable
        if _config.OMDesc is None and snameList[Idx] and xmlName in selected[curTankType]:
            del selected[curTankType][xmlName]
        _config.loadJson('remodsCache', selected, _config.configPath, True)
    else:
        snameList = sorted(_config.OM.models.keys())
        if selected['Remod'] not in snameList:
            snameIdx = 0
        else:
            snameIdx = snameList.index(selected['Remod'])
        sname = snameList[snameIdx]
        _config.OMDesc = _config.OM.models[sname]
        selected['Remod'] = sname
        _config.loadJson('remodsCache', selected, _config.configPath, True)


def OM_apply(vDesc):
    for key in ('splineDesc', 'trackParams'):
        if vDesc.chassis[key] is None:
            vDesc.chassis[key] = {}
    data = _config.OMDesc.data
    for key in ('traces', 'tracks', 'wheels', 'groundNodes', 'trackNodes', 'splineDesc', 'trackParams'):
        exec "vDesc.chassis['%s']=" % key + data['chassis'][key]
    if data['chassis']['AODecals']:
        AODecalsOffset = vDesc.chassis['hullPosition'] - data['chassis']['hullPosition']
        vDesc.chassis['AODecals'] = copy.deepcopy(data['chassis']['AODecals'])
        vDesc.chassis['AODecals'][0].setElement(3, 1, AODecalsOffset.y)
    for part in TankPartNames.ALL:
        getattr(vDesc, part)['models']['undamaged'] = data[part]['undamaged']
    if data['gun']['effects']:
        newGunEffects = g_cache._gunEffects.get(data['gun']['effects'])
        if newGunEffects:
            vDesc.gun['effects'] = newGunEffects
    if data['gun']['reloadEffect']:
        newGunReloadEffect = g_cache._gunReloadEffects.get(data['gun']['reloadEffect'])
        if newGunReloadEffect:
            vDesc.gun['reloadEffect'] = newGunReloadEffect
    vDesc.gun['emblemSlots'] = data['gun']['emblemSlots']
    if data['hull']['emblemSlots']:
        cntClan = 1
        cntPlayer = cntInscription = 0
        for part in ('hull', 'turret'):
            for slot in getattr(vDesc, part)['emblemSlots']:
                if slot.type == 'inscription':
                    cntInscription += 1
                if slot.type == 'player':
                    cntPlayer += 1
        try:
            vDesc.hull['emblemSlots'] = []
            vDesc.turret['emblemSlots'] = []
            for part in ('hull', 'turret'):
                for slot in data[part]['emblemSlots']:
                    if slot.type in ('player', 'inscription', 'clan'):
                        getattr(vDesc, part)['emblemSlots'].append(slot)
                    if slot.type == 'player' and cntPlayer > 0:
                        cntPlayer -= 1
                    if slot.type == 'inscription' and cntInscription > 0:
                        cntInscription -= 1
                    if slot.type == 'clan' and cntClan > 0:
                        cntClan -= 1

            assert not cntClan and not cntPlayer and not cntInscription
        except StandardError:
            print 'RemodEnabler: provided emblem slots corrupted. Stock slots restored'
            if _config.data['isDebug']:
                print 'cntPlayer =', cntPlayer
                print 'cntInscription =', cntInscription
    for partName in ('hull', 'turret'):
        if not data[partName]['emblemSlots']:
            part = getattr(vDesc, partName)
            for i in range(len(part['emblemSlots'])):
                part['emblemSlots'][i] = part['emblemSlots'][i]._replace(size=0.001)

    exclMask = data['common']['camouflage']['exclusionMask']
    vDesc.type.camouflageExclusionMask = exclMask
    if exclMask:
        vDesc.type.camouflageTiling = data['common']['camouflage']['tiling']
    for partName in ('hull', 'gun', 'turret'):
        camoData = data[partName]['camouflage']
        exclMask = camoData['exclusionMask']
        if exclMask:
            part = getattr(vDesc, partName)
            part['camouflageExclusionMask'] = exclMask
            part['camouflageTiling'] = camoData['tiling']
    exhaust = data['hull']['exhaust']
    for effectDesc in vDesc.hull['customEffects']:
        if exhaust['nodes']:
            effectDesc.nodes[:] = exhaust['nodes']
        effectDesc._selectorDesc = g_cache._customEffects['exhaust'].get(exhaust['pixie'], effectDesc._selectorDesc)
    for partName in ('chassis', 'engine'):
        for key in ('wwsoundPC', 'wwsoundNPC'):
            part = getattr(vDesc, partName)
            soundID = data[partName][key]
            if soundID:
                part[key] = soundID


def OS_find(curVehName, isPlayerVehicle, isAlly, currentMode='battle', skinType='static'):
    _config.OSDesc[skinType] = None
    if not _config.OS.enabled:
        return
    curTankType = 'Player' if isPlayerVehicle else 'Ally' if isAlly else 'Enemy'
    if currentMode != 'remod':
        for curSName in _config.OS.priorities[skinType][curTankType]:
            curPRecord = _config.OS.models[skinType][curSName]
            # noinspection PyUnresolvedReferences
            if curVehName not in curPRecord.whitelist and curVehName.lower() not in curPRecord.whitelist:
                continue
            else:
                _config.OSDesc[skinType] = curPRecord
                break


OS_dynamic_db = {}


def OS_createDynamic(vehicleID, vDesc, visible=False):
    global OS_dynamic_db
    try:
        OS_dynamic_db[vehicleID] = OS_dyn = {part: {'model': None} for part in TankPartNames.ALL[1:]}
        OS_dyn['loaded'] = False
        OS_dyn['entered'] = False
        OS_dyn['loading'] = True
        sname = _config.OSDesc['dynamic'].name
        resList = []
        for modelName in TankPartNames.ALL[1:]:
            modelPath = getattr(vDesc, modelName)['models']['undamaged'].replace(
                'vehicles/', 'vehicles/skins/models/%s/vehicles/' % sname)
            resList.append(modelPath)
        BigWorld.loadResourceListBG(tuple(resList), partial(OS_onLoad_dynamic, vehicleID, visible))
    except StandardError:
        traceback.print_exc()
        print vDesc.name


def OS_onLoad_dynamic(vehicleID, visible, resourceRefs):
    global OS_dynamic_db
    if vehicleID not in OS_dynamic_db:
        return
    OS_dyn = OS_dynamic_db[vehicleID]
    OS_dyn['loading'] = False
    OS_dyn['loaded'] = True
    failList = []
    failed = resourceRefs.failedIDs
    resourceItems = resourceRefs.items()
    for idx, modelName in enumerate(TankPartNames.ALL[1:]):
        try:
            modelPath, model = resourceItems[idx]
            if modelPath not in failed and model is not None:
                moduleDict = OS_dyn[modelName]
                moduleDict['model'] = model
                moduleDict['model'].visible = False
            else:
                failList.append(modelPath)
        except IndexError as e:
            print e
            print idx, resourceItems
    if failList:
        print 'RemodEnabler: dynamic skin load failed: models not found:'
        OS_dyn['loaded'] = False
        print failList
    if OS_dyn['entered']:
        OS_attach_dynamic(vehicleID, visible)


def OS_attach_dynamic(vehicleID, visible=False):
    global OS_dynamic_db
    if vehicleID not in OS_dynamic_db:
        return
    if not OS_dynamic_db[vehicleID]['loaded']:
        if OS_dynamic_db[vehicleID]['loading']:
            OS_dynamic_db[vehicleID]['entered'] = True
        return
    vEntity = BigWorld.entity(vehicleID)
    if vEntity is None:
        return
    if hasattr(vEntity, 'appearance'):
        compoundModel = vEntity.appearance.compoundModel
    else:
        compoundModel = vEntity.model
    OS_dyn = OS_dynamic_db[vehicleID]
    scaleMat = mathUtils.createIdentityMatrix()
    scaleMat.setScale(Math.Vector3(1.025))
    for modelName in TankPartNames.ALL[1:]:
        moduleDict = OS_dyn[modelName]
        if moduleDict['model'] is not None:
            if moduleDict['model'] not in vEntity.models:
                try:
                    if modelName == TankPartNames.GUN:
                        modelName = TankNodeNames.GUN_INCLINATION
                    compoundModel.node(modelName).attach(moduleDict['model'], scaleMat)
                except StandardError:
                    if _config.data['isDebug']:
                        traceback.print_exc()
            moduleDict['model'].visible = visible


def OS_detach_dynamic(vehicleID):
    global OS_dynamic_db
    if vehicleID in OS_dynamic_db:
        OS_dyn = OS_dynamic_db[vehicleID]
        if not OS_dyn['loaded']:
            return
        OS_dyn['loaded'] = False
        vEntity = BigWorld.entity(vehicleID)
        if vEntity is None:
            return
        for moduleName in TankPartNames.ALL[1:]:
            moduleDict = OS_dyn[moduleName]
            if moduleDict['model'] is not None:
                moduleDict['model'].visible = False


def OS_destroy_dynamic(vehicleID):
    global OS_dynamic_db
    try:
        if vehicleID in OS_dynamic_db:
            OS_detach_dynamic(vehicleID)
            del OS_dynamic_db[vehicleID]
    except StandardError:
        traceback.print_exc()


def new_oVHC(self):
    vehicle = self._CompoundAppearance__vehicle
    if not vehicle.isAlive():
        OS_destroy_dynamic(vehicle.id)
    old_oVHC(self)


def new_startVisual(self):
    old_startVisual(self)
    if self.isStarted and self.isAlive() and _config.data['enabled']:
        BigWorld.callback(0.1, partial(OS_attach_dynamic, self.id))


def new_vehicle_onLeaveWorld(self, vehicle):
    if vehicle.isStarted:
        OS_destroy_dynamic(vehicle.id)
    old_vehicle_onLeaveWorld(self, vehicle)


def new_targetFocus(self, entity):
    global OS_dynamic_db
    old_targetFocus(self, entity)
    if entity in self._PlayerAvatar__vehicles:
        try:
            for vehicleID in OS_dynamic_db:
                if OS_dynamic_db[vehicleID]['loaded']:
                    for moduleName in TankPartNames.ALL[1:]:
                        model = OS_dynamic_db[vehicleID][moduleName]['model']
                        if model is not None:
                            model.visible = vehicleID == entity.id
        except StandardError:
            traceback.print_exc()


def new_targetBlur(self, prevEntity):
    global OS_dynamic_db
    old_targetBlur(self, prevEntity)
    if prevEntity in self._PlayerAvatar__vehicles:
        try:
            for vehicleID in OS_dynamic_db:
                if OS_dynamic_db[vehicleID]['loaded']:
                    for moduleName in TankPartNames.ALL[1:]:
                        model = OS_dynamic_db[vehicleID][moduleName]['model']
                        if model is not None:
                            model.visible = False
        except StandardError:
            traceback.print_exc()


old_targetFocus = PlayerAvatar.targetFocus
PlayerAvatar.targetFocus = new_targetFocus
old_targetBlur = PlayerAvatar.targetBlur
PlayerAvatar.targetBlur = new_targetBlur


def OS_apply(vDesc):
    OSDesc = _config.OSDesc['static']
    if OSDesc is not None:
        sname = OSDesc.name
        for part in TankPartNames.ALL:
            modelPath = getattr(vDesc, part)['models']['undamaged'].replace(
                'vehicles/', 'vehicles/skins/models/%s/vehicles/' % sname)
            if os.path.isfile(BigWorld.curCV + '/' + modelPath):
                getattr(vDesc, part)['models']['undamaged'] = modelPath
            else:
                print 'RemodEnabler: skin model not found:', modelPath


def printOldConfigs(vDesc):
    print 'old chassis configuration:'
    for key in ('traces', 'tracks', 'wheels', 'groundNodes', 'trackNodes', 'splineDesc', 'trackParams'):
        print vDesc.chassis[key]
    for part in ('gun', 'hull', 'turret'):
        print 'old %s emblem slots configuration:' % part
        print getattr(vDesc, part)['emblemSlots']
    for ids in (('_gunEffects', 'effects', 'shot'), ('_gunReloadEffects', 'reloadEffect', 'reload')):
        for key, value in getattr(g_cache, ids[0]).items():
            if value == vDesc.gun[ids[1]]:
                print 'old gun', ids[2], 'effects ID:', key
                break
        else:
            print 'gun', ids[2], 'effect ID not found'
    print 'chassis sound IDs: PC:', vDesc.chassis['wwsoundPC'], 'NPC:', vDesc.chassis['wwsoundNPC']
    print 'engine sound IDs: PC:', vDesc.engine['wwsoundPC'], 'NPC:', vDesc.engine['wwsoundNPC']


def debugOutput(xmlName, vehName, playerName=None):
    if not _config.data['isDebug']:
        return
    info = []
    header = 'RemodEnabler: %s (%s)' % (xmlName, vehName)
    if playerName is not None:
        header += ', player: %s' % playerName
    if _config.OMDesc is not None:
        info.append('OMDesc: %s' % _config.OMDesc.name)
    if _config.OSDesc['static'] is not None:
        info.append('static OSDesc: %s' % _config.OSDesc['static'].name)
    if _config.OSDesc['dynamic'] is not None:
        info.append('dynamic OSDesc: %s' % _config.OSDesc['dynamic'].name)
    if info:
        print header + ' processed:', ', '.join(info)


def new_prerequisites(self, respawnCompactDescr=None):
    if self.respawnCompactDescr is not None:
        respawnCompactDescr = self.respawnCompactDescr
        self.isCrewActive = True
        self.respawnCompactDescr = None
    if respawnCompactDescr is None and self.typeDescriptor is not None:
        return ()
    vDesc = self.getDescr(respawnCompactDescr)
    if _config.data['enabled']:
        isPlayerVehicle = self.id == BigWorld.player().playerVehicleID
        xmlName = vDesc.name.split(':')[1].lower()
        playerName = BigWorld.player().arena.vehicles.get(self.id)['name']
        isAlly = BigWorld.player().arena.vehicles.get(self.id)['team'] == BigWorld.player().team
        OM_find(xmlName, isPlayerVehicle, isAlly)
        for partName in TankPartNames.ALL + ('engine',):
            new_part = None
            try:
                old_part = getattr(vDesc, partName)
                new_part = copy.deepcopy(old_part)
                setattr(vDesc, partName, new_part)
                if 'hitTester' in old_part:
                    getattr(vDesc, partName)['hitTester'] = old_part['hitTester']
            except TypeError:
                print partName
                pprint.pprint(getattr(vDesc, partName))
                pprint.pprint(new_part)
        vehNation, vehName = vDesc.chassis['models']['undamaged'].split('/')[1:3]
        vehDefNation = vDesc.chassis['hitTester'].bspModelName.split('/')[1]
        if _config.OMDesc is None:
            if vehNation == vehDefNation:
                if skinsFound:
                    OS_find(vehName, isPlayerVehicle, isAlly, skinType='dynamic')
                    if _config.OSDesc['dynamic'] is not None:
                        OS_createDynamic(self.id, vDesc)
                    OS_find(vehName, isPlayerVehicle, isAlly)
                    OS_apply(vDesc)
            elif _config.data['isDebug']:
                print 'RemodEnabler: unknown vehicle nation for %s: %s' % (vehName, vehNation)
        else:
            OM_apply(vDesc)
        debugOutput(xmlName, vehName, playerName)
    self.typeDescriptor = vDesc
    self.appearance, compoundAssembler, prereqs = appearance_cache.createAppearance(
        self.id, self.typeDescriptor, self.health, self.isCrewActive, self.isTurretDetached)
    return prereqs


def new_startBuild(self, vDesc, vState):
    if _config.data['enabled']:
        xmlName = vDesc.name.split(':')[1].lower()
        _config.curVehicleName = xmlName
        isPlayerVehicle = _config.data['currentMode'] == 'player'
        isAlly = _config.data['currentMode'] == 'ally'
        OM_find(xmlName, isPlayerVehicle, isAlly, _config.data['currentMode'])
        for partName in TankPartNames.ALL + ('engine',):
            new_part = None
            try:
                old_part = getattr(vDesc, partName)
                new_part = copy.deepcopy(old_part)
                setattr(vDesc, partName, new_part)
                if 'hitTester' in old_part:
                    getattr(vDesc, partName)['hitTester'] = old_part['hitTester']
            except TypeError:
                print partName
                pprint.pprint(getattr(vDesc, partName))
                pprint.pprint(new_part)
        message = None
        collisionNotVisible = not _config.data['collisionEnabled'] and not _config.data['collisionComparisonEnabled']
        vehNation, vehName = vDesc.chassis['models']['undamaged'].split('/')[1:3]
        vehDefNation = vDesc.chassis['hitTester'].bspModelName.split('/')[1]
        if _config.OMDesc is None:
            if vehNation == vehDefNation:
                if skinsFound:
                    OS_find(vehName, isPlayerVehicle, isAlly, _config.data['currentMode'], skinType='dynamic')
                    if _config.OSDesc['dynamic'] is not None:
                        OS_createDynamic(self._VehicleAppearance__vEntityId, vDesc,
                                         _config.data['dynamicSkinEnabled'] and not _config.data[
                                             'collisionComparisonEnabled'])
                        if _config.data['dynamicSkinEnabled'] and collisionNotVisible:
                            message = _config.i18n['UI_install_skin_dynamic'] + _config.OSDesc['dynamic'].name.join(
                                ('<b>', '</b>.'))
                    OS_find(vehName, isPlayerVehicle, isAlly, _config.data['currentMode'])
                    OS_apply(vDesc)
            elif _config.data['isDebug']:
                print 'RemodEnabler: unknown vehicle nation for %s: %s' % (vehName, vehNation)
            if _config.data['isDebug'] and (
                    _config.OSDesc['dynamic'] is None or not _config.data['dynamicSkinEnabled']) and collisionNotVisible:
                if _config.OSDesc['static'] is not None:
                    message = _config.i18n['UI_install_skin'] + _config.OSDesc['static'].name.join(('<b>', '</b>.'))
                else:
                    message = _config.i18n['UI_install_default']
        else:
            OM_apply(vDesc)
            if collisionNotVisible:
                message = _config.i18n['UI_install_remod'] + _config.OMDesc.name.join(
                    ('<b>', '</b>.')) + '\n' + _config.OMDesc.authorMessage
        if message is not None:
            SystemMessages.pushMessage('PYmods_SM' + message, SystemMessages.SM_TYPE.CustomizationForGold)
        debugOutput(xmlName, vehName)
    old_startBuild(self, vDesc, vState)


def new_setupModel(self, buildIdx):
    old_setupModel(self, buildIdx)
    if _config.data['enabled']:
        vEntityId = self._VehicleAppearance__vEntityId
        vEntity = BigWorld.entity(vEntityId)
        vDesc = self._VehicleAppearance__vDesc
        model = vEntity.model
        self.collisionLoaded = True
        self.modifiedModelsDesc = dict(
            [(part, {'model': None, 'motor': None, 'matrix': None}) for part in TankPartNames.ALL])
        failList = []
        for modelName in self.modifiedModelsDesc.keys():
            try:
                self.modifiedModelsDesc[modelName]['model'] = BigWorld.Model(
                    getattr(vDesc, modelName)['hitTester'].bspModelName)
                self.modifiedModelsDesc[modelName]['model'].visible = False
            except StandardError:
                self.collisionLoaded = False
                failList.append(getattr(vDesc, modelName)['hitTester'].bspModelName)

        if failList:
            print 'RemodEnabler: collision load failed: models not found'
            print failList
        if _config.OSDesc['dynamic'] is not None:
            OS_attach_dynamic(
                vEntityId, _config.data['dynamicSkinEnabled'] and not _config.data['collisionComparisonEnabled'])
        if self.collisionLoaded:
            if any((_config.data['collisionEnabled'], _config.data['collisionComparisonEnabled'])):
                # Getting offset matrices
                hullOffset = mathUtils.createTranslationMatrix(vEntity.typeDescriptor.chassis['hullPosition'])
                turretOffset = mathUtils.createTranslationMatrix(vEntity.typeDescriptor.hull['turretPositions'][0])
                gunOffset = mathUtils.createTranslationMatrix(vEntity.typeDescriptor.turret['gunPosition'])
                # Getting local transform matrices
                hullMP = mathUtils.MatrixProviders.product(mathUtils.createIdentityMatrix(), hullOffset)
                turretMP = mathUtils.MatrixProviders.product(mathUtils.createIdentityMatrix(), turretOffset)
                gunMP = mathUtils.MatrixProviders.product(mathUtils.createIdentityMatrix(), gunOffset)
                # turretMP = mathUtils.MatrixProviders.product(vEntity.appearance.turretMatrix, turretOffset)
                # gunMP = mathUtils.MatrixProviders.product(vEntity.appearance.gunMatrix, gunOffset)
                # Getting full transform matrices relative to vehicle coordinate system
                self.modifiedModelsDesc[TankPartNames.CHASSIS][
                    'matrix'] = fullChassisMP = mathUtils.createIdentityMatrix()
                self.modifiedModelsDesc[TankPartNames.HULL]['matrix'] = fullHullMP = mathUtils.MatrixProviders.product(
                    hullMP, fullChassisMP)
                self.modifiedModelsDesc[TankPartNames.TURRET][
                    'matrix'] = fullTurretMP = mathUtils.MatrixProviders.product(turretMP, fullHullMP)
                self.modifiedModelsDesc[TankPartNames.GUN]['matrix'] = mathUtils.MatrixProviders.product(gunMP,
                                                                                                         fullTurretMP)
                for moduleName, moduleDict in self.modifiedModelsDesc.items():
                    if moduleDict['motor'] not in tuple(moduleDict['model'].motors):
                        moduleDict['motor'] = BigWorld.Servo(
                            mathUtils.MatrixProviders.product(moduleDict['matrix'], vEntity.matrix))
                        moduleDict['model'].addMotor(moduleDict['motor'])
                    if moduleDict['model'] not in tuple(vEntity.models):
                        try:
                            vEntity.addModel(moduleDict['model'])
                        except StandardError:
                            pass
                    moduleDict['model'].visible = True
                addCollisionGUI(self)
            if _config.data['collisionEnabled']:
                for moduleName in TankPartNames.ALL:
                    if model.node(moduleName) is not None:
                        scaleMat = Math.Matrix()
                        scaleMat.setScale((0.001, 0.001, 0.001))
                        model.node(moduleName, scaleMat)
                    else:
                        print 'RemodEnabler: collision model for %s not found' % moduleName


def new_refreshModel(self):
    if self.isPresent() and (_config.OMDesc is not None or any(_config.OSDesc.values())):
        self._CurrentPreviewVehicle__item = self._CurrentPreviewVehicle__getPreviewVehicle(self.item.intCD)
    old_refreshModel(self)


old_prerequisites = Vehicle.prerequisites
Vehicle.prerequisites = new_prerequisites
old_startBuild = _VehicleAppearance._VehicleAppearance__startBuild
_VehicleAppearance._VehicleAppearance__startBuild = new_startBuild
old_setupModel = _VehicleAppearance._VehicleAppearance__setupModel
_VehicleAppearance._VehicleAppearance__setupModel = new_setupModel
old_refreshModel = _CurrentPreviewVehicle.refreshModel
_CurrentPreviewVehicle.refreshModel = new_refreshModel
old_vehicle_onLeaveWorld = PlayerAvatar.vehicle_onLeaveWorld
PlayerAvatar.vehicle_onLeaveWorld = new_vehicle_onLeaveWorld
old_startVisual = Vehicle.startVisual
Vehicle.startVisual = new_startVisual
old_oVHC = CompoundAppearance.onVehicleHealthChanged
CompoundAppearance.onVehicleHealthChanged = new_oVHC


def clearCollision(self):
    if _config.data['enabled']:
        vEntityId = self._VehicleAppearance__vEntityId
        if getattr(self, 'collisionLoaded', False):
            for moduleName, moduleDict in self.modifiedModelsDesc.items():
                if moduleDict['model'] in tuple(BigWorld.entity(vEntityId).models):
                    BigWorld.entity(vEntityId).delModel(moduleDict['model'])
                    if moduleDict['motor'] in tuple(moduleDict['model'].motors):
                        moduleDict['model'].delMotor(moduleDict['motor'])
        if hasattr(self, 'collisionTable'):
            del self.collisionTable
        OS_destroy_dynamic(vEntityId)


def new_refresh(self):
    clearCollision(self)
    old_refresh(self)


def new_recreate(self, vDesc, vState, onVehicleLoadedCallback=None):
    clearCollision(self)
    old_recreate(self, vDesc, vState, onVehicleLoadedCallback)


old_refresh = _VehicleAppearance.refresh
_VehicleAppearance.refresh = new_refresh
old_recreate = _VehicleAppearance.recreate
_VehicleAppearance.recreate = new_recreate


class TextBox(object):
    def __init__(self, text='', position=(0, 0.6, 1), colour=(255, 255, 255, 255), size=(0, 0.04)):
        self.GUIComponent = GUI.Text('')
        self.GUIComponent.verticalAnchor = 'CENTER'
        self.GUIComponent.horizontalAnchor = 'CENTER'
        self.GUIComponent.verticalPositionMode = 'CLIP'
        self.GUIComponent.horizontalPositionMode = 'CLIP'
        self.GUIComponent.materialFX = 'BLEND'
        self.GUIComponent.colour = colour
        self.GUIComponent.heightMode = 'CLIP'
        self.GUIComponent.explicitSize = True
        self.GUIComponent.position = position
        self.GUIComponent.font = 'system_small'
        self.GUIComponent.text = text
        self.GUIComponent.size = size
        self.GUIComponent.visible = True

    def addRoot(self):
        GUI.addRoot(self.GUIComponent)

    def delRoot(self):
        GUI.delRoot(self.GUIComponent)

    def __del__(self):
        self.delRoot()


class TexBox(object):
    def __init__(self, texturePath='', position=(0, 0, 1), size=(0.09, 0.045)):
        self.GUIComponent = GUI.Simple('')
        self.GUIComponent.verticalAnchor = 'CENTER'
        self.GUIComponent.horizontalAnchor = 'CENTER'
        self.GUIComponent.verticalPositionMode = 'CLIP'
        self.GUIComponent.horizontalPositionMode = 'CLIP'
        self.GUIComponent.widthMode = 'CLIP'
        self.GUIComponent.heightMode = 'CLIP'
        self.GUIComponent.materialFX = 'BLEND'
        self.GUIComponent.colour = (255, 255, 255, 255)
        self.GUIComponent.size = size
        self.GUIComponent.position = position
        self.GUIComponent.textureName = texturePath
        self.GUIComponent.mapping = ((0.0, 0.0), (0.0, 1.0), (1.0, 1.0), (1.0, 0.0))
        self.GUIComponent.visible = True

    def addRoot(self):
        GUI.addRoot(self.GUIComponent)

    def delRoot(self):
        GUI.delRoot(self.GUIComponent)

    def __del__(self):
        self.delRoot()


def addCollisionGUI(self):
    vDesc = self._VehicleAppearance__vDesc
    self.collisionTable = {}
    for moduleIdx, moduleName in enumerate(TankPartNames.ALL):
        self.collisionTable[moduleName] = curCollisionTable = {'textBoxes': [],
                                                               'texBoxes': [],
                                                               'armorValues': {}}
        moduleDict = getattr(vDesc, moduleName)
        for Idx, groupNum in enumerate(sorted(moduleDict['materials'].keys())):
            armorValue = int(moduleDict['materials'][groupNum].armor)
            curCollisionTable['armorValues'].setdefault(armorValue, [])
            if groupNum not in curCollisionTable['armorValues'][armorValue]:
                curCollisionTable['armorValues'][armorValue].append(groupNum)
        for Idx, armorValue in enumerate(sorted(curCollisionTable['armorValues'], reverse=True)):
            x = (6 + moduleIdx) / 10.0 + 0.025
            y = (-1 - Idx) / 20.0 - 0.002
            textBox = TextBox('%s' % armorValue, (x, y, 0.7), (240, 240, 240, 255))
            textBox.addRoot()
            curCollisionTable['textBoxes'].append(textBox)
            textBox = TextBox('%s' % armorValue, (x, y, 0.725), (0, 0, 0, 255))
            textBox.addRoot()
            curCollisionTable['textBoxes'].append(textBox)
            kindsCap = len(curCollisionTable['armorValues'][armorValue])
            for matIdx, matKind in enumerate(curCollisionTable['armorValues'][armorValue]):
                matKindName = material_kinds.IDS_BY_NAMES.keys()[material_kinds.IDS_BY_NAMES.values().index(matKind)]
                texName = 'objects/misc/collisions_mat/%s.dds' % matKindName
                colWidth = 0.09
                colPad = colWidth / 2.0
                x = (6 + moduleIdx) / 10.0 + 0.025 - colPad + colPad / float(kindsCap) + (
                    colWidth / float(kindsCap) * float(matIdx))
                y = (-1 - Idx) / 20.0
                texBox = TexBox(texName, (x, y, 0.8), (0.09 / float(kindsCap), 0.045))
                texBox.addRoot()
                curCollisionTable['texBoxes'].append(texBox)
        GUI.reSort()


def new_LW_populate(self):
    old_LW_populate(self)
    _config.data['isInHangar'] = True


old_LW_populate = LobbyView._populate
LobbyView._populate = new_LW_populate
statistic_mod = PYmodsCore.Analytics(_config.ID, _config.version.split(' ', 1)[0], 'UA-76792179-4')
