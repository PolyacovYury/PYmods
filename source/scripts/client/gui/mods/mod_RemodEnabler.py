# -*- coding: utf-8 -*-
import binascii
import copy
import copy_reg
import datetime
import gc
import glob
import os
import shutil
import time
import traceback
import weakref
from collections import namedtuple
from functools import partial
from zipfile import ZipFile

import Math
import ResMgr

import BigWorld
import GUI
import Keys
import PYmodsCore
import SoundGroups
import material_kinds
from Avatar import PlayerAvatar
from AvatarInputHandler import mathUtils
from CurrentVehicle import g_currentPreviewVehicle, g_currentVehicle
from Vehicle import Vehicle
from adisp import AdispException, async, process
from gui import InputHandler, SystemMessages
from gui.ClientHangarSpace import _VehicleAppearance
from gui.Scaleform.daapi.view.lobby.LobbyView import LobbyView
from gui.Scaleform.daapi.view.login.LoginView import LoginView
from gui.Scaleform.daapi.view.meta.LoginQueueWindowMeta import LoginQueueWindowMeta
from gui.Scaleform.framework import GroupedViewSettings, ScopeTemplates, ViewSettings, ViewTypes, g_entitiesFactories
from gui.Scaleform.framework.entities.abstract.AbstractWindowView import AbstractWindowView
from gui.app_loader.loader import g_appLoader
from gui.battle_control.controllers.finish_sound_ctrl import _SOUND_EVENTS
from helpers import getClientVersion
from items import vehicles
from vehicle_systems import appearance_cache
from vehicle_systems.CompoundAppearance import CompoundAppearance
from vehicle_systems.tankStructure import TankPartNames

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
    def __init__(self):
        self.models = {}
        self.enabled = False
        self.allDesc = {'Player': [''],
                        'Ally': [''],
                        'Enemy': ['']}
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
                                 'hullPosition': None},
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
                     'common': {'camouflage': {'exclusionMask': '',
                                               'tiling': (1.0, 1.0, 0.0, 0.0)}}}


class OS(object):
    def __init__(self):
        self.models = {'static': {}, 'dynamic': {}}
        self.enabled = False
        self.priorities = {skinType: {'Player': [],
                                      'Ally': [],
                                      'Enemy': []} for skinType in self.models}


class OSDescriptor(object):
    def __init__(self):
        self.name = ''
        self.whitelist = []


class _Config(PYmodsCore._Config):
    def __init__(self):
        super(_Config, self).__init__(__file__)
        self.version = '2.9.3 (%s)' % self.version
        self.author = '%s (thx to atacms)' % self.author
        self.possibleModes = ['player', 'ally', 'enemy', 'remod']
        self.defaultSkinConfig = {'static': {'enabled': True,
                                             'swapPlayer': True,
                                             'swapAlly': False,
                                             'swapEnemy': True},
                                  'dynamic': {'enabled': True,
                                              'swapPlayer': True,
                                              'swapAlly': False,
                                              'swapEnemy': True}}
        self.defaultRemodConfig = {'enabled': True,
                                   'swapPlayer': True,
                                   'swapAlly': True,
                                   'swapEnemy': True,
                                   'usePlayerWhitelist': True,
                                   'useAllyWhitelist': True,
                                   'useEnemyWhitelist': True}
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
                     'oldConfigPrints': [],
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
            'UI_flash_useWL_header_text': 'Use whitelists for:',
            'UI_flash_useWL_header_tooltip': 'If disabled, this remod will be installed to all corresponding group tanks.',
            'UI_flash_useWL_player_text': 'Player',
            'UI_flash_useWL_ally_text': 'Allies',
            'UI_flash_useWL_enemy_text': 'Enemies',
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
            'UI_loading_skinType_static': 'Checking static skins...',
            'UI_loading_skinType_dynamic': 'Checking dynamic skins...',
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
        self.OM = OM()
        self.OS = OS()
        self.OMDesc = None
        self.OSDesc = {'static': None, 'dynamic': None}
        self.curVehicleName = None
        self.loadingProxy = None
        self.loadLang()

    def template_settings(self):
        viewKey = self.createHotKey('ChangeViewHotkey')
        viewKey['tooltip'] %= {'remod': self.i18n['UI_setting_ChangeViewHotkey_remod'] if self.data['remod'] else ''}
        template = {'modDisplayName': self.i18n['UI_description'],
                    'settingsVersion': 200,
                    'enabled': True,
                    'column1': [self.createHotKey('DynamicSkinHotkey'),
                                self.createControl('isDebug'),
                                self.createControl('remod')],
                    'column2': [viewKey,
                                self.createHotKey('SwitchRemodHotkey'),
                                self.createHotKey('CollisionHotkey')]}
        return template

    def onWindowClose(self):
        g_currentPreviewVehicle.refreshModel()

    # noinspection PyUnresolvedReferences
    def update_data(self, doPrint=False):
        super(_Config, self).update_data()
        self.settings = self.loadJson('settings', self.settings, self.configPath)
        self.OM.enabled = bool(len(glob.glob('%s/vehicles/remods/*' % BigWorld.curCV)))
        if self.OM.enabled:
            self.OM.selected = self.loadJson('remodsCache', self.OM.selected, self.configPath)
            configsPath = '%sremods/*.json' % self.configPath
            for configPath in glob.iglob(configsPath):
                sname = os.path.basename(configPath).split('.')[0]
                self.configsDict[sname] = confDict = self.loadJson(sname, self.configsDict.get(sname, {}),
                                                                   os.path.dirname(configPath) + '/', encrypted=True)
                if not confDict:
                    print '%s: error while reading %s.' % (self.ID, os.path.basename(configPath))
                    continue
                settingsDict = self.settings['remods'].setdefault(sname, self.defaultRemodConfig)
                if not settingsDict.get('enabled', True):
                    print '%s: %s disabled, moving on' % (self.ID, sname)
                    continue
                self.OM.models[sname] = pRecord = OMDescriptor()
                pRecord.name = sname
                pRecord.authorMessage = confDict.get('authorMessage', '')
                for tankType in self.OM.allDesc:
                    allDesc = self.OM.allDesc[tankType]
                    selected = self.OM.selected[tankType]
                    if not settingsDict.get('swap%s' % tankType, self.defaultRemodConfig['swap%s' % tankType]):
                        if self.data['isDebug']:
                            print '%s: %s swapping in %s disabled.' % (self.ID, tankType.lower(), sname)
                        for xmlName in selected.keys():
                            if sname == selected[xmlName]:
                                selected[xmlName] = ''
                        if sname in allDesc:
                            allDesc.remove(sname)
                        continue
                    useKey = 'use%sWhitelist' % tankType
                    WLKey = '%sWhitelist' % tankType.lower()
                    whiteStr = settingsDict.setdefault(WLKey, confDict.get(WLKey, ''))
                    templist = filter(None, map(lambda x: x.strip(), whiteStr.split(',')))
                    whitelist = pRecord.whitelists[tankType]
                    whitelist.update(templist)
                    if not settingsDict.get(useKey, self.defaultRemodConfig[useKey]) and templist:
                        if sname not in allDesc:
                            allDesc.append(sname)
                        if self.data['isDebug']:
                            print ('%s: empty whitelist for %s. Apply to all %s tanks' if not whitelist else
                                   '%s: %s will be used for all %s tanks if not explicitly designated to another '
                                   'model.') % (self.ID, sname, tankType.lower())
                    else:
                        if self.data['isDebug']:
                            print '%s: whitelist for %s: %s' % (self.ID, tankType.lower(), list(whitelist))
                        if sname in allDesc:
                            allDesc.remove(sname)
                        for xmlName in selected.keys():
                            if sname == selected[xmlName] and xmlName not in whitelist:
                                selected[xmlName] = ''
                for key, data in pRecord.data.iteritems():
                    if key == 'common':
                        confSubDict = confDict
                    else:
                        confSubDict = confDict.get(key)
                    if not confDict:
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
                    for subKey in ('effects', 'reloadEffect'):
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
                for tankType in self.OM.allDesc:
                    for xmlName in self.OM.selected[tankType].keys():
                        if (self.OM.selected[tankType][xmlName] and self.OM.selected[tankType][
                                xmlName] not in self.OM.models):
                            self.OM.selected[tankType][xmlName] = ''
                        if (len(self.OM.allDesc[tankType]) == 1 or self.OM.selected[tankType][xmlName] not in
                                self.OM.allDesc[tankType]) and xmlName not in remodTanks[tankType]:
                            del self.OM.selected[tankType][xmlName]
                if self.OM.selected['Remod'] and self.OM.selected['Remod'] not in self.OM.models:
                    self.OM.selected['Remod'] = ''
                self.loadJson('remodsCache', self.OM.selected, self.configPath, True)
        else:
            print '%s: no remods found, model module standing down.' % self.ID
            self.OM.enabled = False
            self.loadJson('remodsCache', self.OM.selected, self.configPath, True)
        self.OS.enabled = any(os.path.isdir('%s/vehicles/skins%s/' % (BigWorld.curCV, skinType)) and glob.glob(
            '%s/vehicles/skins%s/*' % (BigWorld.curCV, skinType)) for skinType in ('', '_dynamic'))
        if self.OS.enabled:
            self.OS.priorities = self.loadJson('skinsPriority', self.OS.priorities, self.configPath)
            skinsDir = BigWorld.curCV + '/vehicles/skins%s/textures/'
            for skinTypeSuff in ('', '_dynamic'):
                skinDir = skinsDir % skinTypeSuff + '*'
                skinType = 'static' if not skinTypeSuff else skinTypeSuff[1:]
                skinsSettings = self.settings['skins%s' % skinTypeSuff]
                disabledSkins = []
                if self.data['isDebug']:
                    print '%s: loading configs for %s skins' % (self.ID, skinType)
                for skinPath in glob.iglob(skinDir):
                    sname = os.path.basename(skinPath)
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
                    pRecord.whitelist = []
                    for curNation in glob.iglob(skinPath + '/vehicles/*'):
                        for vehicleName in glob.iglob(curNation + '/*'):
                            curVehName = os.path.basename(vehicleName)
                            hasSegmentTex = False
                            if not glob.glob(vehicleName + '/tracks/*.dds') and os.path.isdir(vehicleName + '/tracks'):
                                shutil.rmtree(vehicleName + '/tracks')
                            else:
                                hasSegmentTex = True
                            if not glob.glob(vehicleName + '/*.dds') and not hasSegmentTex:
                                os.rmdir(vehicleName)
                                if self.data['isDebug']:
                                    print '%s: %s folder from %s pack is deleted: empty' % (
                                        self.ID, curVehName, sname)
                            else:
                                if curVehName not in pRecord.whitelist:
                                    pRecord.whitelist.append(curVehName)

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
        g_entitiesFactories.addSettings(
            ViewSettings('RemodEnablerUI', RemodEnablerUI, 'RemodEnabler.swf', ViewTypes.WINDOW, None,
                         ScopeTemplates.GLOBAL_SCOPE, False))
        g_entitiesFactories.addSettings(
            GroupedViewSettings('RemodEnablerLoading', RemodEnablerLoading, 'LoginQueueWindow.swf', ViewTypes.TOP_WINDOW,
                                '', None, ScopeTemplates.DEFAULT_SCOPE))


def skinsPresenceCheck():
    global skinsFound
    for skinsType in skinsFound:
        skinsPath = '%s/vehicles/skins%s/textures/' % (BigWorld.curCV, skinsType)
        if os.path.isdir(skinsPath):
            if glob.glob(skinsPath + '*'):
                skinsFound[skinsType] = True


_config = _Config()
_config.load()
texReplaced = {'': False, '_dynamic': False}
skinsFound = {'': False, '_dynamic': False}
skinsPresenceCheck()
clientIsNew = {'': True, '_dynamic': True}
skinsModelsMissing = {'': True, '_dynamic': True}
needToReReadSkinsModels = {'': False, '_dynamic': False}
modelsDir = BigWorld.curCV + '/vehicles/skins%s/models/'
skinVehNamesLDict = {'': {}, '_dynamic': {}}


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

    def addLine(self, line, prefix=True):
        if len(self.lines) == 8:
            del self.lines[0]
        if prefix:
            line = '>' + line
        self.lines.append(line)
        self.updateMessage()

    def onComplete(self):
        self.lines[-1] += _config.i18n['UI_loading_done'].join(("<font color='#00FF00'>", '</font>'))
        self.updateMessage()

    def addBar(self, pkgName):
        self.curPercentage = 0
        self.addLine(_config.i18n['UI_loading_package'] % pkgName)
        self.addLine(self.createBar(), prefix=False)

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
            'useWL': {'header': _config.createLabel('useWL_header', 'flash'),
                      'ally': _config.createLabel('useWL_ally', 'flash'),
                      'enemy': _config.createLabel('useWL_enemy', 'flash'),
                      'player': _config.createLabel('useWL_player', 'flash')},
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
            settings['remods'].append({
                'useFor': {key.lower(): OMSettings['swap%s' % key] for key in ('Player', 'Ally', 'Enemy')},
                'useWL': {key.lower(): OMSettings['use%sWhitelist' % key] for key in ('Player', 'Ally', 'Enemy')},
                'whitelists': [OMDesc.whitelists[team] for team in ('Player', 'Ally', 'Enemy')]
            })
        for idx, skinType in enumerate(('', '_dynamic')):
            skins = _config.settings['skins%s' % skinType]
            for sname in sorted(_config.OS.models['static' if not skinType else 'dynamic']):
                sDesc = skins[sname]
                texts['skinNames'][idx].append(sname)
                settings['skins'][idx].append({'useFor': {k.lower(): sDesc['swap%s' % k] for k in _config.OM.allDesc}})
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
                OMSettings['use%sWhitelist' % key] = getattr(setObj.useWL, key.lower())
            for teamIdx, team in enumerate(('player', 'ally', 'enemy')):
                OMSettings['%sWhitelist' % team] = ','.join(setObj.whitelists[teamIdx])
        for idx, settingsArray in enumerate(settings.skins):
            for nameIdx, setObj in enumerate(settingsArray):
                for key in _config.OM.allDesc:
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
    buf = open(filename, 'rb').read()
    buf = binascii.crc32(buf) & 0xFFFFFFFF & localPath.__hash__()
    return buf


@async
@process
def skinCRC32All(callback):
    global texReplaced, skinsFound, skinVehNamesLDict
    for skinsType in texReplaced:
        CRC32cacheFile = '%s/vehicles/skins%s/CRC32_textures.txt' % (BigWorld.curCV, skinsType)
        CRC32cache = None
        if os.path.isfile(CRC32cacheFile):
            CRC32cache = open(CRC32cacheFile, 'rb').read()
        skinsPath = '%s/vehicles/skins%s/textures/' % (BigWorld.curCV, skinsType)
        if os.path.isdir(skinsPath):
            if glob.glob(skinsPath + '*'):
                skinsFound[skinsType] = True
                print 'RemodEnabler: listing %s for CRC32' % skinsPath
                _config.loadingProxy.addLine(
                    _config.i18n['UI_loading_skinType_%s' % ('static' if not skinsType else 'dynamic')])
                CRC32 = 0
                resultList = []
                for skin in glob.iglob(skinsPath + '*'):
                    _config.loadingProxy.addLine(_config.i18n['UI_loading_skinPack'] % os.path.basename(skin))
                    skinCRC32 = 0
                    skinName = os.path.basename(skin)
                    for nation in glob.iglob(skin + '/vehicles/*'):
                        nationCRC32 = 0
                        for vehicleName in glob.iglob(nation + '/*'):
                            vehicleCRC32 = 0
                            vehName = os.path.basename(vehicleName)
                            skinVehNamesLDict[skinsType].setdefault(vehName, []).append(skinName)
                            for texture in glob.iglob(vehicleName + '/*.dds'):
                                textureCRC32 = CRC32_from_file(
                                    texture, '/'.join(texture.replace(os.sep, '/').rsplit('/', 4)[1:]))
                                vehicleCRC32 ^= textureCRC32
                            nationCRC32 ^= vehicleCRC32
                            yield doFuncCall()
                        skinCRC32 ^= nationCRC32
                    _config.loadingProxy.onComplete()
                    SoundGroups.g_instance.playSound2D('enemy_sighted_for_team')
                    if skinCRC32 in resultList:
                        print 'RemodEnabler: deleting duplicate skins pack:', skin.replace(os.sep, '/')
                        shutil.rmtree(skin)
                        continue
                    CRC32 ^= skinCRC32
                    resultList.append(skinCRC32)
                if CRC32cache is not None and str(CRC32) == CRC32cache:
                    print 'RemodEnabler: skins%s textures were not changed' % skinsType
                else:
                    if CRC32cache is None:
                        print 'RemodEnabler: skins%s textures were reinstalled (or you deleted the CRC32 cache)' % \
                              skinsType
                    else:
                        print 'RemodEnabler: skins%s textures were changed' % skinsType
                    cf = open(CRC32cacheFile, 'w+b')
                    cf.write(str(CRC32))
                    cf.close()
                    texReplaced[skinsType] = True
            else:
                print 'RemodEnabler: skins%s folder is empty' % skinsType
        else:
            print 'RemodEnabler: skins%s folder not found' % skinsType
    BigWorld.callback(0.0, partial(callback, True))


@async
def modelsCheck(callback):
    global clientIsNew, skinsModelsMissing, needToReReadSkinsModels
    for skinsType in texReplaced:
        modelDir = modelsDir % skinsType
        lastVersionPath = '%s/vehicles/skins%s/last_version.txt' % (BigWorld.curCV, skinsType)
        if os.path.isfile(lastVersionPath):
            lastVersion = open(lastVersionPath).read()
            if getClientVersion() == lastVersion:
                clientIsNew[skinsType] = False
            else:
                print 'RemodEnabler: skins%s client version changed' % skinsType
        else:
            print 'RemodEnabler: skins%s client version cache not found' % skinsType

        if os.path.isdir(modelDir):
            if len(glob.glob(modelDir + '*')):
                skinsModelsMissing[skinsType] = False
            else:
                print 'RemodEnabler: skins%s models dir is empty' % skinsType
        else:
            print 'RemodEnabler: skins%s models dir not found' % skinsType
        needToReReadSkinsModels[skinsType] = skinsFound[skinsType] and (
            clientIsNew[skinsType] or skinsModelsMissing[skinsType] or texReplaced[skinsType])
        if skinsFound[skinsType] and clientIsNew[skinsType]:
            if os.path.isdir(modelDir):
                shutil.rmtree(modelDir)
            lastVersionFile = open(lastVersionPath, 'w+')
            lastVersionFile.write(getClientVersion())
            lastVersionFile.close()
        if skinsFound[skinsType] and not os.path.isdir(modelDir):
            os.makedirs(modelDir)
        elif not skinsFound[skinsType] and os.path.isdir(modelDir):
            print 'RemodEnabler: no skins found, deleting %s' % modelDir
            shutil.rmtree(modelDir)
        elif texReplaced[skinsType] and os.path.isdir(modelDir):
            shutil.rmtree(modelDir)
    BigWorld.callback(0.0, partial(callback, True))


@async
@process
def modelsProcess(callback):
    if any(needToReReadSkinsModels.values()):
        _config.loadingProxy.updateTitle(_config.i18n['UI_loading_header_models_unpack'])
        modelFileFormats = ('.model', '.primitives', '.visual', '.primitives_processed', '.visual_processed')
        print 'RemodEnabler: starting to unpack vehicles packages'
        for vehPkgPath in glob.glob('./res/packages/vehicles*.pkg') + glob.glob('./res/packages/shared_content*.pkg'):
            completionPercentage = 0
            filesCnt = 0
            pkgStartTime = time.time()
            print 'RemodEnabler: unpacking %s' % os.path.basename(vehPkgPath)
            _config.loadingProxy.addBar(os.path.basename(vehPkgPath))
            vehPkg = ZipFile(vehPkgPath)
            fileNamesList = filter(
                lambda x: x.startswith('vehicles') and 'normal' in x and os.path.splitext(x)[1] in modelFileFormats,
                vehPkg.namelist())
            allFilesCnt = len(fileNamesList)
            for fileNum, memberFileName in enumerate(fileNamesList):
                for skinsType in needToReReadSkinsModels:
                    if not needToReReadSkinsModels[skinsType]:
                        continue
                    skinsVehDict = skinVehNamesLDict[skinsType]
                    # noinspection PyTypeChecker
                    for skinName in skinsVehDict.get(os.path.normpath(memberFileName).split('\\')[2], []):
                        processMember(memberFileName, skinName, skinsType, vehPkg)
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
            SoundGroups.g_instance.playSound2D('enemy_sighted_for_team')
            if _config.data['isDebug']:
                print 'RemodEnabler: file candidates checked:', allFilesCnt
                print 'RemodEnabler: file candidates processed:', filesCnt
                print 'RemodEnabler: pkg process time: %s seconds' % round(time.time() - pkgStartTime, 2)
    BigWorld.callback(0.0, partial(callback, True))


@async
def doFuncCall(callback):
    BigWorld.callback(0.0, partial(callback, None))


# noinspection PyPep8,PyPep8
def processMember(memberFileName, skinName, skinType, vehPkg):
    modelDir = modelsDir % skinType
    skinDir = modelDir.replace('%s/' % BigWorld.curCV, '') + skinName + '/'
    texDir = skinDir.replace('models', 'textures')
    skinsSign = 'vehicles/skins%s/' % skinType
    if '.primitives' in memberFileName:
        vehPkg.extract(memberFileName, modelDir + skinName)
    elif '.model' in memberFileName:
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
                    if skinsSign not in curTexture and os.path.isfile(BigWorld.curCV + '/' + texDir + curTexture):
                        curDiff = texDir + curTexture
                        curProp.writeString('Texture', curDiff.replace('\\', '/'))
                    elif skinsSign in curTexture and not os.path.isfile(BigWorld.curCV + '/' + curTexture):
                        curDiff = curTexture.replace(texDir, '')
                        curProp.writeString('Texture', curDiff.replace('\\', '/'))

        curVisual.save()


@process
def skinCaller():
    if any(skinsFound.values()):
        g_appLoader.getDefLobbyApp().loadView('RemodEnablerLoading')
        jobStartTime = time.time()
        try:
            yield skinCRC32All()
            yield modelsCheck()
            yield modelsProcess()
        except AdispException:
            traceback.print_exc()
        print 'RemodEnabler: total models check time:', datetime.timedelta(seconds=round(time.time() - jobStartTime))
        gc.collect()
        SoundGroups.g_instance.playSound2D(_SOUND_EVENTS.LAST_KILL)
        BigWorld.callback(3, _config.loadingProxy.onWindowClose)


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
            if _config.OM.enabled and PYmodsCore.checkKeys(_config.data['SwitchRemodHotkey']):
                if _config.data['currentMode'] != 'remod':
                    curTankType = _config.data['currentMode'].capitalize()
                    snameList = sorted(_config.OM.models.keys()) + ['']
                    allDesc = _config.OM.allDesc[curTankType]
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
                        if snameList[Idx] not in allDesc and vehName not in curPRecord.whitelists[curTankType]:
                            continue
                        if vehName in selected or len(allDesc) > 1:
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


def new_obj(cls, *args):
    try:
        return old_obj(cls, *args)
    except StandardError:
        if _config.data['isDebug']:
            print 'Cannot directly construct objects of this type: %s' % cls


old_obj = copy_reg.__newobj__
copy_reg.__newobj__ = new_obj


def OM_find(xmlName, playerName, isPlayerVehicle, isAlly, currentMode='battle'):
    _config.OMDesc = None
    if not _config.OM.enabled:
        return
    if _config.data['isDebug']:
        if not isPlayerVehicle:
            print 'RemodEnabler: looking for OMDescriptor for %s, player - %s' % (xmlName, playerName)
        else:
            print 'RemodEnabler: looking for OMDescriptor for %s' % xmlName
    curTankType = 'Player' if isPlayerVehicle else 'Ally' if isAlly else 'Enemy'
    selected = _config.OM.selected
    if currentMode != 'remod':
        snameList = sorted(_config.OM.models.keys()) + ['']
        allDesc = _config.OM.allDesc[curTankType]
        if selected[curTankType].get(xmlName) not in snameList:
            snameIdx = 0
        else:
            snameIdx = snameList.index(selected[curTankType][xmlName])
        for Idx in xrange(snameIdx, len(snameList)):
            curPRecord = _config.OM.models.get(snameList[Idx])
            if snameList[Idx] not in allDesc and xmlName not in curPRecord.whitelists[curTankType]:
                continue
            else:
                if xmlName in selected[curTankType] or len(allDesc) > 1:
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
    xmlName = vDesc.name.split(':')[1].lower()
    if _config.data['isDebug']:
        print 'RemodEnabler: %s assigned to %s' % (xmlName, _config.OMDesc.name)
        print '!! swapping chassis '
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
    elif _config.data['isDebug']:
        print 'warning: AODecals not found. stock AODecal is applied'
        print vDesc.chassis['AODecals'][0].translation
    for part in TankPartNames.ALL:
        getattr(vDesc, part)['models']['undamaged'] = data[part]['undamaged']
    if data['gun']['effects']:
        newGunEffects = vehicles.g_cache._gunEffects.get(data['gun']['effects'])
        if newGunEffects:
            vDesc.gun['effects'] = newGunEffects
    if data['gun']['reloadEffect']:
        newGunReloadEffect = vehicles.g_cache._gunReloadEffects.get(data['gun']['reloadEffect'])
        if newGunReloadEffect:
            vDesc.gun['reloadEffect'] = newGunReloadEffect
    vDesc.gun['emblemSlots'] = data['gun']['emblemSlots']
    cntClan = 1
    cntPlayer = cntInscription = 0
    if not data['hull']['emblemSlots']:
        if _config.data['isDebug']:
            print 'RemodEnabler: hull and turret emblemSlots not provided.'
    else:
        if _config.data['isDebug']:
            print 'RemodEnabler: hull and turret emblemSlots found. processing'
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
            if _config.data['isDebug']:
                print 'RemodEnabler: hull and turret emblemSlots swap completed'
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
    nodes = data['hull']['exhaust']['nodes']
    if nodes:
        vDesc.hull['exhaust'].nodes = nodes


def OS_find(curVehName, playerName, isPlayerVehicle, isAlly, currentMode='battle', skinType='static'):
    _config.OSDesc[skinType] = None
    if not _config.OS.enabled:
        return
    if _config.data['isDebug']:
        if not isPlayerVehicle:
            print 'RemodEnabler: looking for %s OSDescriptor for %s, player - %s' % (skinType, curVehName, playerName)
        else:
            print 'RemodEnabler: looking for %s OSDescriptor for %s' % (skinType, curVehName)
    curTankType = 'Player' if isPlayerVehicle else 'Ally' if isAlly else 'Enemy'
    if currentMode != 'remod':
        for curSName in _config.OS.priorities[skinType][curTankType]:
            curPRecord = _config.OS.models[skinType][curSName]
            # noinspection PyUnresolvedReferences
            if curVehName not in curPRecord.whitelist:
                continue
            else:
                _config.OSDesc[skinType] = curPRecord
                break


OS_dynamic_db = {}


def OS_create_dynamic(vehicleID, vDesc, visible=False):
    global OS_dynamic_db
    try:
        OS_dynamic_db[vehicleID] = OS_dyn = {part: {'model': None, 'motor': None} for part in TankPartNames.ALL[1:]}
        OS_dyn['loaded'] = False
        OS_dyn['entered'] = False
        OS_dyn['loading'] = True
        xmlName = vDesc.name.split(':')[1].lower()
        sname = _config.OSDesc['dynamic'].name
        if _config.data['isDebug']:
            print 'RemodEnabler: %s assigned to dynamic skin %s' % (xmlName, sname)
        resList = []
        for modelName in TankPartNames.ALL[1:]:
            modelPath = getattr(vDesc, modelName)['hitTester'].bspModelName.replace(
                'vehicles/', 'vehicles/skins_dynamic/models/%s/vehicles/' % sname).replace(
                'collision_client', 'normal/lod0')
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
        modelPath, model = resourceItems[idx]
        if modelPath not in failed and model is not None:
            module = OS_dyn[modelName]
            module['model'] = model
            module['model'].visible = False
        else:
            failList.append(modelPath)
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
    addedMat = mathUtils.createIdentityMatrix()
    for modelName in TankPartNames.ALL[1:]:
        module = OS_dyn[modelName]
        if module['motor'] not in module['model'].motors:
            if modelName == TankPartNames.GUN and hasattr(vEntity, 'appearance'):
                addedMat = vEntity.appearance.gunMatrix
            module['motor'] = BigWorld.Servo(
                mathUtils.MatrixProviders.product(mathUtils.MatrixProviders.product(scaleMat, addedMat),
                                                  compoundModel.node(modelName)))
            module['model'].addMotor(module['motor'])
        if module['model'] not in vEntity.models:
            try:
                vEntity.addModel(module['model'])
            except StandardError:
                pass
        module['model'].visible = visible


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
            module = OS_dyn[moduleName]
            module['model'].visible = False
            try:
                vEntity.delModel(module['model'])
            except ValueError:
                pass
            if module['motor'] in tuple(module['model'].motors):
                module['model'].delMotor(module['motor'])


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
    xmlName = vDesc.name.split(':')[1].lower()
    OSDesc = _config.OSDesc['static']
    if OSDesc is not None:
        sname = OSDesc.name
        if _config.data['isDebug']:
            print 'RemodEnabler: %s assigned to skin %s' % (xmlName, sname)
        for part in TankPartNames.ALL:
            modelPath = getattr(vDesc, part)['hitTester'].bspModelName.replace(
                'vehicles/', 'vehicles/skins/models/%s/vehicles/' % sname).replace('collision_client', 'normal/lod0')
            if os.path.isfile(BigWorld.curCV + '/' + modelPath):
                getattr(vDesc, part)['models']['undamaged'] = modelPath
    else:
        if _config.data['isDebug']:
            print 'RemodEnabler: %s unchanged' % xmlName
        for part in TankPartNames.ALL:
            getattr(vDesc, part)['models']['undamaged'] = getattr(vDesc, part)['hitTester'].bspModelName.replace(
                'collision_client', 'normal/lod0')
            if xmlName == 'g114_rheinmetall_skorpian':
                getattr(vDesc, part)['models']['undamaged'] = getattr(vDesc, part)['models']['undamaged'].replace(
                    'G114_Skorpian', 'G114_Rheinmetall_Skorpian')


def printOldConfigs(vDesc):
    xmlName = vDesc.name.split(':')[1].lower()
    print 'old chassis configuration:'
    for key in ('traces', 'tracks', 'wheels', 'groundNodes', 'trackNodes', 'splineDesc', 'trackParams'):
        print vDesc.chassis[key]
    for part in ('gun', 'hull', 'turret'):
        print 'old %s emblem slots configuration:' % part
        print getattr(vDesc, part)['emblemSlots']
    _config.data['oldConfigPrints'].append(xmlName)


def new_prerequisites(self, respawnCompactDescr=None):
    if self.respawnCompactDescr is not None:
        respawnCompactDescr = self.respawnCompactDescr
        self.isCrewActive = True
        self.respawnCompactDescr = None
    if respawnCompactDescr is None and self.typeDescriptor is not None:
        return ()
    descr = self.getDescr(respawnCompactDescr)
    if _config.data['enabled']:
        isPlayerVehicle = self.id == BigWorld.player().playerVehicleID
        xmlName = descr.name.split(':')[1].lower()
        playerName = BigWorld.player().arena.vehicles.get(self.id)['name']
        isAlly = BigWorld.player().arena.vehicles.get(self.id)['team'] == BigWorld.player().team
        OM_find(xmlName, playerName, isPlayerVehicle, isAlly)
        if xmlName not in _config.data['oldConfigPrints'] and (
                isPlayerVehicle and _config.OMDesc is None or _config.OMDesc is not None) and _config.data['isDebug']:
            printOldConfigs(descr)
        vehName = descr.chassis['hitTester'].bspModelName.split('/')[2]
        if _config.OMDesc is None:
            if skinsFound['_dynamic']:
                OS_find(vehName, playerName, isPlayerVehicle, isAlly, skinType='dynamic')
                if _config.OSDesc['dynamic'] is not None:
                    OS_create_dynamic(self.id, descr)
            if skinsFound['']:
                OS_find(vehName, playerName, isPlayerVehicle, isAlly)
            OS_apply(descr)
        else:
            OM_apply(descr)
    self.typeDescriptor = descr
    self.appearance, compoundAssembler, prereqs = appearance_cache.createAppearance(
        self.id, self.typeDescriptor, self.health, self.isCrewActive, self.isTurretDetached)
    return prereqs


def new_startBuild(self, vDesc, vState):
    if _config.data['enabled']:
        xmlName = vDesc.name.split(':')[1].lower()
        _config.curVehicleName = xmlName
        isPlayerVehicle = _config.data['currentMode'] == 'player'
        isAlly = _config.data['currentMode'] == 'ally'
        OM_find(xmlName, 'HangarEntity', isPlayerVehicle, isAlly, _config.data['currentMode'])
        vDesc = copy.deepcopy(vDesc)
        if xmlName not in _config.data['oldConfigPrints'] and _config.data['isDebug']:
            printOldConfigs(vDesc)
        if _config.OMDesc is None:
            vehName = vDesc.chassis['hitTester'].bspModelName.split('/')[2]
            if skinsFound['_dynamic']:
                OS_find(vehName, 'HangarEntity', isPlayerVehicle, isAlly, _config.data['currentMode'], skinType='dynamic')
                if _config.OSDesc['dynamic'] is not None:
                    OS_create_dynamic(
                        self._VehicleAppearance__vEntityId, vDesc, _config.data['dynamicSkinEnabled'] and not _config.data[
                            'collisionComparisonEnabled'])
                    if _config.data['dynamicSkinEnabled']:
                        if not _config.data['collisionEnabled'] and not _config.data['collisionComparisonEnabled']:
                            SystemMessages.pushMessage(
                                'PYmods_SM' + _config.i18n['UI_install_skin_dynamic'] + _config.OSDesc[
                                    'dynamic'].name.join(('<b>', '</b>.')), SystemMessages.SM_TYPE.CustomizationForGold)
            if skinsFound['']:
                OS_find(vehName, 'HangarEntity', isPlayerVehicle, isAlly, _config.data['currentMode'])
            if (_config.OSDesc['dynamic'] is None or not _config.data['dynamicSkinEnabled']) and (
                    not _config.data['collisionEnabled'] and not _config.data['collisionComparisonEnabled']):
                if _config.OSDesc['static'] is not None:
                    SystemMessages.pushMessage(
                        'PYmods_SM' + _config.i18n['UI_install_skin'] + _config.OSDesc['static'].name.join(
                            ('<b>', '</b>.')), SystemMessages.SM_TYPE.CustomizationForGold)
                else:
                    SystemMessages.pushMessage('PYmods_SM' + _config.i18n['UI_install_default'],
                                               SystemMessages.SM_TYPE.CustomizationForGold)
            OS_apply(vDesc)
        else:
            OM_apply(vDesc)
            if not _config.data['collisionEnabled'] and not _config.data['collisionComparisonEnabled']:
                SystemMessages.pushMessage(
                    'PYmods_SM' + _config.i18n['UI_install_remod'] + _config.OMDesc.name.join(
                        ('<b>', '</b>.')) + '\n' + _config.OMDesc.authorMessage,
                    SystemMessages.SM_TYPE.CustomizationForGold)
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
                for moduleName, module in self.modifiedModelsDesc.items():
                    if module['motor'] not in tuple(module['model'].motors):
                        module['motor'] = BigWorld.Servo(
                            mathUtils.MatrixProviders.product(module['matrix'], vEntity.matrix))
                        module['model'].addMotor(module['motor'])
                    if module['model'] not in tuple(vEntity.models):
                        try:
                            vEntity.addModel(module['model'])
                        except StandardError:
                            pass
                    module['model'].visible = True
                addCollisionGUI(self)
            if _config.data['collisionEnabled']:
                for moduleName in TankPartNames.ALL:
                    if model.node(moduleName) is not None:
                        scaleMat = Math.Matrix()
                        scaleMat.setScale((0.001, 0.001, 0.001))
                        model.node(moduleName, scaleMat)
                    else:
                        print 'RemodEnabler_hangarChameleon: %s not found' % moduleName


old_prerequisites = Vehicle.prerequisites
Vehicle.prerequisites = new_prerequisites
old_startBuild = _VehicleAppearance._VehicleAppearance__startBuild
_VehicleAppearance._VehicleAppearance__startBuild = new_startBuild
old_setupModel = _VehicleAppearance._VehicleAppearance__setupModel
_VehicleAppearance._VehicleAppearance__setupModel = new_setupModel
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
            for moduleName, module in self.modifiedModelsDesc.items():
                if module['model'] in tuple(BigWorld.entity(vEntityId).models):
                    BigWorld.entity(vEntityId).delModel(module['model'])
                    if module['motor'] in tuple(module['model'].motors):
                        module['model'].delMotor(module['motor'])
        delCollisionGUI(self)
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
        module = getattr(vDesc, moduleName)
        for Idx, groupNum in enumerate(sorted(module['materials'].keys())):
            armorValue = int(module['materials'][groupNum].armor)
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


def delCollisionGUI(self):
    if hasattr(self, 'collisionTable'):
        del self.collisionTable


class Analytics(PYmodsCore.Analytics):
    def __init__(self):
        super(Analytics, self).__init__()
        self.mod_description = _config.ID
        self.mod_version = _config.version.split(' ', 1)[0]
        self.mod_id_analytics = 'UA-76792179-4'


statistic_mod = Analytics()


def fini():
    try:
        statistic_mod.end()
    except StandardError:
        traceback.print_exc()


def new_LW_populate(self):
    old_LW_populate(self)
    _config.data['isInHangar'] = True
    try:
        statistic_mod.start()
    except StandardError:
        traceback.print_exc()


old_LW_populate = LobbyView._populate
LobbyView._populate = new_LW_populate
