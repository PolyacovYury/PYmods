# -*- coding: utf-8 -*-
import BigWorld
import Keys
import Math
import glob
import os
import traceback
from PYmodsCore import PYmodsConfigInterface, refreshCurrentVehicle, checkKeys, loadJson, showI18nDialog, overrideMethod
from PYmodsCore.config.json_reader import JSONLoader as cls
from collections import OrderedDict
from gui import InputHandler, SystemMessages
from gui.Scaleform.daapi.view.lobby.LobbyView import LobbyView
from gui.Scaleform.daapi.view.login.LoginView import LoginView
from gui.Scaleform.framework import ScopeTemplates, ViewSettings, ViewTypes, g_entitiesFactories
from gui.Scaleform.framework.entities.abstract.AbstractWindowView import AbstractWindowView
from gui.Scaleform.framework.managers.loaders import SFViewLoadParams
from gui.app_loader import g_appLoader
from helpers import dependency
from items.components import component_constants
from items.components.chassis_components import SplineConfig
from items.components.shared_components import EmblemSlot
from items.vehicles import g_cache
from skeletons.gui.shared.utils import IHangarSpace
from vehicle_systems.tankStructure import TankPartNames
from . import __date__, __modID__


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
        if confDict['type'] not in component_constants.ALLOWED_EMBLEM_SLOTS:
            print g_config.ID + ': not supported emblem slot type:', confDict['type'] + ', expected:', ' '.join(
                component_constants.ALLOWED_EMBLEM_SLOTS)
        descr = EmblemSlot(Math.Vector3(tuple(confDict['rayStart'])), Math.Vector3(tuple(confDict['rayEnd'])),
                           Math.Vector3(tuple(confDict['rayUp'])), confDict['size'],
                           confDict.get('hideIfDamaged', False), confDict['type'], confDict.get('isMirrored', False),
                           confDict.get('isUVProportional', True), confDict.get('emblemId', None))
        slots.append(descr)

    return tuple(slots)


class ModelDescriptor(object):
    def __init__(self):
        self.name = ''
        self.authorMessage = ''
        self.whitelists = {'player': set(), 'ally': set(), 'enemy': set()}
        self.data = {
            'chassis': {'undamaged': '', 'AODecals': None, 'hullPosition': None,
                        'wwsound': '', 'wwsoundPC': '', 'wwsoundNPC': ''},
            'hull': {'undamaged': '', 'emblemSlots': [], 'exhaust': {'nodes': [], 'pixie': ''},
                     'camouflage': {'exclusionMask': '', 'tiling': (1.0, 1.0, 0.0, 0.0)}},
            'turret': {'undamaged': '', 'emblemSlots': [],
                       'camouflage': {'exclusionMask': '', 'tiling': (1.0, 1.0, 0.0, 0.0)}},
            'gun': {'undamaged': '', 'emblemSlots': [], 'effects': '', 'reloadEffect': '',
                    'camouflage': {'exclusionMask': '', 'tiling': (1.0, 1.0, 0.0, 0.0)}},
            'engine': {'wwsound': '', 'wwsoundPC': '', 'wwsoundNPC': ''},
            'common': {'camouflage': {'exclusionMask': '', 'tiling': (1.0, 1.0, 0.0, 0.0)}}}


class ConfigInterface(PYmodsConfigInterface):
    hangarSpace = dependency.descriptor(IHangarSpace)

    def __init__(self):
        self.teams = ('player', 'ally', 'enemy')
        self.defaultRemodConfig = {'enabled': True, 'swapPlayer': True, 'swapAlly': True, 'swapEnemy': True}
        self.settings = {'remods': {}}
        self.modelsData = {'enabled': True, 'models': {}, 'selected': {'player': {}, 'ally': {}, 'enemy': {}}}
        self.isModAdded = False
        self.collisionEnabled = False
        self.collisionComparisonEnabled = False
        self.isInHangar = False
        self.currentTeam = self.teams[0]
        self.previewRemod = None
        super(ConfigInterface, self).__init__()

    def init(self):
        self.ID = __modID__
        self.version = '3.0.0 (%s)' % __date__
        self.author += ' (thx to atacms)'
        self.defaultKeys = {'ChangeViewHotkey': [Keys.KEY_F2, [Keys.KEY_LCONTROL, Keys.KEY_RCONTROL]],
                            'SwitchRemodHotkey': [Keys.KEY_F3, [Keys.KEY_LCONTROL, Keys.KEY_RCONTROL]],
                            'CollisionHotkey': [Keys.KEY_F4, [Keys.KEY_LCONTROL, Keys.KEY_RCONTROL]]}
        self.data = {'enabled': True,
                     'isDebug': True,
                     'ChangeViewHotkey': self.defaultKeys['ChangeViewHotkey'],
                     'CollisionHotkey': self.defaultKeys['CollisionHotkey'],
                     'SwitchRemodHotkey': self.defaultKeys['SwitchRemodHotkey']}
        self.i18n = {
            'UI_description': 'Remod Enabler',
            'UI_flash_header': 'Remods setup',
            'UI_flash_header_tooltip': "Extended setup for RemodEnabler by "
                                       "<font color='#DD7700'><b>Polyacov_Yury</b></font>",
            'UI_flash_remodSetupBtn': 'Remods setup',
            'UI_flash_remodCreateBtn': 'Create remod',
            'UI_flash_remodCreate_name_text': 'Remod name',
            'UI_flash_remodCreate_name_tooltip': 'Remod unique ID and config file name.',
            'UI_flash_remodCreate_message_text': 'Author message',
            'UI_flash_remodCreate_message_tooltip': 'This message is displayed in hangar every time the remod is selected.'
                                                    '\nLeave blank if not required.',
            'UI_flash_remodCreate_name_empty': '<b>Remod creation failed:</b>\nname is empty.',
            'UI_flash_remodCreate_error': '<b>Remod creation failed:</b>\ncheck python.log for additional information.',
            'UI_flash_remodCreate_success': '<b>Remod created successfully</b>.',
            'UI_flash_team_player': 'Player',
            'UI_flash_team_ally': 'Ally',
            'UI_flash_team_enemy': 'Enemy',
            'UI_flash_whiteList_addBtn': 'Add',
            'UI_flash_whiteList_header_text': 'Whitelists for:',
            'UI_flash_whiteList_header_tooltip': 'Open to view all items, select an item to delete.\n\n'
                                                 'List is scrollable if longer than 10 items.',
            'UI_flash_whiteDropdown_default': 'Expand',
            'UI_flash_useFor_header_text': 'Use this item for:',
            'UI_flash_useFor_player_text': 'Player',
            'UI_flash_useFor_ally_text': 'Allies',
            'UI_flash_useFor_enemy_text': 'Enemies',
            'UI_flash_WLVehDelete_header': 'Confirmation',
            'UI_flash_WLVehDelete_text': 'Are you sure you want to delete this vehicle from this whitelist?',
            'UI_flash_vehicleDelete_success': 'Vehicle deleted from whitelist: ',
            'UI_flash_vehicleAdd_success': 'Vehicle added to whitelist: ',
            'UI_flash_vehicleAdd_dupe': 'Vehicle already in whitelist: ',
            'UI_flash_vehicleAdd_notSupported': 'Vehicle is not supported by RemodEnabler.',
            'UI_flash_backBtn': 'Back',
            'UI_flash_saveBtn': 'Save',
            'UI_setting_isDebug_text': 'Enable extended log printing',
            'UI_setting_isDebug_tooltip': 'If enabled, your python.log will be harassed with mod\'s debug information.',
            'UI_setting_ChangeViewHotkey_text': 'View mode switch hotkey',
            'UI_setting_ChangeViewHotkey_tooltip': (
                'This hotkey will switch the preview mode in hangar.\n<b>Possible modes:</b>\n'
                ' • Player tank\n • Ally tank\n • Enemy tank'),
            'UI_setting_CollisionHotkey_text': 'Collision view switch hotkey',
            'UI_setting_CollisionHotkey_tooltip': (
                'This hotkey will switch collision preview mode in hangar.\n'
                '<b>Possible modes:</b>\n • OFF\n • Model replace\n • Model add'),
            'UI_setting_SwitchRemodHotkey_text': 'Remod switch hotkey',
            'UI_setting_SwitchRemodHotkey_tooltip': 'This hotkey will cycle through all remods.',
            'UI_disableCollisionComparison': '<b>RemodEnabler:</b>\nDisabling collision comparison mode.',
            'UI_enableCollisionComparison': '<b>RemodEnabler:</b>\nEnabling collision comparison mode.',
            'UI_enableCollision': '<b>RemodEnabler:</b>\nEnabling collision mode.',
            'UI_install_remod': '<b>RemodEnabler:</b>\nRemod installed: ',
            'UI_install_default': '<b>RemodEnabler:</b>\nDefault model applied.',
            'UI_mode': '<b>RemodEnabler:</b>\nCurrent display mode: ',
            'UI_mode_player': 'player tank preview',
            'UI_mode_ally': 'ally tank preview',
            'UI_mode_enemy': 'enemy tank preview'}
        super(ConfigInterface, self).init()

    def createTemplate(self):
        return {'modDisplayName': self.i18n['UI_description'],
                'settingsVersion': 200,
                'enabled': self.data['enabled'],
                'column1': [self.tb.createHotKey('ChangeViewHotkey'),
                            self.tb.createControl('isDebug')],
                'column2': [self.tb.createHotKey('SwitchRemodHotkey'),
                            self.tb.createHotKey('CollisionHotkey')]}

    def onMSADestroy(self):
        refreshCurrentVehicle()

    def onApplySettings(self, settings):
        super(ConfigInterface, self).onApplySettings(settings)
        if self.isModAdded:
            kwargs = dict(id='RemodEnablerUI', enabled=self.data['enabled'])
            try:
                BigWorld.g_modsListApi.updateModification(**kwargs)
            except AttributeError:
                BigWorld.g_modsListApi.updateMod(**kwargs)

    def readOrdered(self, name, path):
        import json
        encrypted = False
        new_path = '%s%s.json' % (path, name)
        config_new = None
        if os.path.isfile(new_path):
            data, excluded, success = cls.json_file_read(new_path, encrypted)
            if success:
                try:
                    config_new = cls.byte_ify(json.loads(data, object_pairs_hook=OrderedDict))
                except StandardError as e:
                    print new_path
                    print e
        return config_new

    def migrateSettings(self, old_data, new_data):
        whitelist = set()
        for team in sorted(self.teams):
            new_data[team] = new_data.get(team, old_data.pop('swap' + team.capitalize(), True))
            whitelist.update(x for x in old_data.pop(team + 'Whitelist', '').split(',') if x)
        new_data['whitelist'] = sorted(whitelist | set(new_data.get('whitelist', [])))

    def migrateConfigs(self):
        configPath_backup = self.configPath    # TODO: remove this after code is complete and tested
        self.configPath = self.configPath.replace(self.ID, self.ID + '_new')
        settings = loadJson(self.ID, 'settings', self.settings, configPath_backup)
        if settings and 'remods' in settings:
            for sname, remodData in settings['remods'].items():
                if not remodData.pop('enabled', True):
                    print self.ID + ': WARNING! Disabled remod detected:', sname + (
                        '. Remod disabling is not supported anymore, delete unneeded remods.'
                        'If game crashed - this is, probably, the reason.')
                self.migrateSettings(remodData, remodData)
        loadJson(self.ID, 'settings', settings, self.configPath, True)
        self.modelsData['selected'] = loadJson(self.ID, 'remodsCache', self.modelsData['selected'], configPath_backup)
        self.modelsData['selected'].pop('remod', '')
        for team, teamData in self.modelsData['selected'].items():
            for xmlName in teamData:
                if teamData[xmlName] is None:  # a vehicle wasn't ever encountered, but now code pre-determines the remods
                    self.findModelDesc(xmlName, team == 'player', team == 'ally')  # no need to save here

        configsPath = configPath_backup + 'remods/*.json'
        for configPath in glob.iglob(configsPath):
            sname = os.path.basename(configPath).split('.')[0]
            old_conf = self.readOrdered(sname, configsPath)
            if not old_conf:
                print self.ID + ': error while reading', os.path.basename(configPath) + '.'
                continue
            new_conf = OrderedDict()
            new_conf['authorMessage'] = old_conf['authorMessage']
            self.migrateSettings(old_conf, new_conf)
            for key, value in old_conf.items():
                if key in ('authorMessage', 'engine') or 'Whitelist' in key or 'swap' in key:
                    continue
                elif key == 'chassis':
                    value = OrderedDict((k, v) for k, v in value.iteritems() if 'sound' not in k)
                new_conf[key] = value
            loadJson(self.ID, sname, new_conf, self.configPath + 'remods/', True, False, sort_keys=False)
        self.configPath = configPath_backup  # !!!!!!!!!!!!!

    def readCurrentSettings(self, quiet=True):
        super(ConfigInterface, self).readCurrentSettings()
        self.settings = loadJson(self.ID, 'settings', self.settings, self.configPath)
        configsPath = self.configPath + 'remods/*.json'
        self.modelsData['enabled'] = bool(glob.glob(configsPath))
        if self.modelsData['enabled']:
            self.modelsData['selected'] = selectedData = loadJson(
                self.ID, 'remodsCache', self.modelsData['selected'], self.configPath)
            for key in selectedData.keys():
                if not key.islower():
                    selectedData[key.lower()] = selectedData.pop(key)
            snameList = set()
            for configPath in glob.iglob(configsPath):
                sname = os.path.basename(configPath).split('.')[0]
                confDict = loadJson(self.ID, sname, {}, os.path.dirname(configPath) + '/', encrypted=True)
                if not confDict:
                    print self.ID + ': error while reading', os.path.basename(configPath) + '.'
                    continue
                settingsDict = self.settings['remods'].setdefault(sname, {})
                snameList.add(sname)
                if not settingsDict.setdefault('enabled', self.defaultRemodConfig['enabled']):
                    print self.ID + ':', sname, 'disabled, moving on'
                    if sname in self.modelsData['models']:
                        del self.modelsData['models'][sname]
                    continue
                self.modelsData['models'][sname] = pRecord = ModelDescriptor()
                pRecord.name = sname
                pRecord.authorMessage = confDict.get('authorMessage', '')
                for tankType in ('player', 'ally', 'enemy'):
                    selected = selectedData[tankType]
                    swapKey = 'swap' + tankType.capitalize()
                    WLKey = tankType + 'Whitelist'
                    whiteStr = settingsDict.setdefault(WLKey, confDict.get(WLKey, ''))
                    templist = [x.strip() for x in whiteStr.split(',') if x]
                    whitelist = pRecord.whitelists[tankType]
                    whitelist.update(templist)
                    if not whitelist:
                        if self.data['isDebug']:
                            print self.ID + ': empty whitelist for', sname + '. Not applied to', tankType, 'tanks.'
                    else:
                        if self.data['isDebug']:
                            print self.ID + ': whitelist for', tankType + ':', list(whitelist)
                        for xmlName in selected:
                            if sname == selected[xmlName] and xmlName not in whitelist:
                                selected[xmlName] = None
                    if not settingsDict.setdefault(swapKey, confDict.get(swapKey, self.defaultRemodConfig[swapKey])):
                        if self.data['isDebug']:
                            print self.ID + ':', tankType, 'swapping in', sname, 'disabled.'
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
                        print self.ID + ': default camomask not found for', sname
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
                    print self.ID + ': config for', sname, 'loaded.'

            for sname in self.modelsData['models'].keys():
                if sname not in snameList:
                    del self.modelsData['models'][sname]

            for sname in self.settings['remods'].keys():
                if sname not in snameList:
                    del self.settings['remods'][sname]

            if not self.modelsData['models']:
                if not quiet:
                    print self.ID + ': no configs found, model module standing down.'
                self.modelsData['enabled'] = False
                loadJson(self.ID, 'remodsCache', selectedData, self.configPath, True, quiet=quiet)
            else:
                remodTanks = {key: set() for key in selectedData}
                for modelDesc in self.modelsData['models'].values():
                    for tankType, whitelist in modelDesc.whitelists.iteritems():
                        for xmlName in whitelist:
                            remodTanks[tankType].add(xmlName)
                            if xmlName not in selectedData[tankType]:
                                selectedData[tankType][xmlName] = None
                for team in ('player', 'ally', 'enemy'):
                    for xmlName in selectedData[team].keys():
                        if selectedData[team][xmlName] and selectedData[team][xmlName] not in self.modelsData['models']:
                            selectedData[team][xmlName] = None
                        if xmlName not in remodTanks[team]:
                            del selectedData[team][xmlName]
                loadJson(self.ID, 'remodsCache', selectedData, self.configPath, True, quiet=quiet)
        else:
            if not quiet:
                print self.ID + ': no remods found, model module standing down.'
            self.modelsData['enabled'] = False
            loadJson(self.ID, 'remodsCache', self.modelsData['selected'], self.configPath, True, quiet=quiet)
        loadJson(self.ID, 'settings', self.settings, self.configPath, True, quiet=quiet)

    def load(self):
        self.migrateConfigs()
        super(ConfigInterface, self).load()

    def findModelDesc(self, xmlName, isPlayerVehicle, isAlly, notForPreview=True):
        modelDesc = None
        if not self.modelsData['enabled']:
            return modelDesc
        curTankType = 'player' if isPlayerVehicle else 'ally' if isAlly else 'enemy'
        selected = self.modelsData['selected']
        if not self.previewRemod or notForPreview:
            if xmlName not in selected[curTankType]:
                return modelDesc
            snameList = sorted(self.modelsData['models']) + ['']
            if selected[curTankType][xmlName] in snameList:
                sname = selected[curTankType][xmlName]
                modelDesc = self.modelsData['models'][sname]
            else:
                sname = ''
            selected[curTankType][xmlName] = sname
            loadJson(self.ID, 'remodsCache', selected, self.configPath, True, quiet=not self.data['isDebug'])
        else:
            modelDesc = self.modelsData['models'][self.previewRemod]
        return modelDesc

    def registerSettings(self):
        super(ConfigInterface, self).registerSettings()
        if not hasattr(BigWorld, 'g_modsListApi'):
            return
        # noinspection PyArgumentList
        g_entitiesFactories.addSettings(
            ViewSettings('RemodEnablerUI', RemodEnablerUI, 'RemodEnabler.swf', ViewTypes.WINDOW, None,
                         ScopeTemplates.GLOBAL_SCOPE, False))
        kwargs = dict(
            id='RemodEnablerUI', name=self.i18n['UI_flash_header'], description=self.i18n['UI_flash_header_tooltip'],
            icon='gui/flash/RemodEnabler.png', enabled=self.data['enabled'] and self.modelsData['enabled'],
            login=True, lobby=True, callback=lambda: (
                    g_appLoader.getDefLobbyApp().containerManager.getContainer(ViewTypes.TOP_WINDOW).getViewCount()
                    or g_appLoader.getDefLobbyApp().loadView(SFViewLoadParams('RemodEnablerUI'))))
        try:
            BigWorld.g_modsListApi.addModification(**kwargs)
        except AttributeError:
            BigWorld.g_modsListApi.addMod(**kwargs)
        self.isModAdded = True


class RemodEnablerUI(AbstractWindowView):
    def _populate(self):
        super(self.__class__, self)._populate()
        self.modeBackup = g_config.currentTeam
        self.newRemodData = OrderedDict()

    def py_onRequestSettings(self):
        g_config.readCurrentSettings(not g_config.data['isDebug'])
        texts = {
            'header': {
                'main': g_config.i18n['UI_flash_header'],
                'remodSetup': g_config.i18n['UI_flash_remodSetupBtn'],
                'remodCreate': g_config.i18n['UI_flash_remodCreateBtn']},
            'remodSetupBtn': g_config.i18n['UI_flash_remodSetupBtn'],
            'remodCreateBtn': g_config.i18n['UI_flash_remodCreateBtn'],
            'create': {'name': g_config.tb.createLabel('remodCreate_name', 'flash'),
                       'message': g_config.tb.createLabel('remodCreate_message', 'flash')},
            'teams': [g_config.i18n['UI_flash_team_' + team] for team in ('player', 'ally', 'enemy')],
            'remodNames': [],
            'whiteList': {'addBtn': g_config.i18n['UI_flash_whiteList_addBtn'],
                          'label': g_config.tb.createLabel('whiteList_header', 'flash'),
                          'defStr': g_config.i18n['UI_flash_whiteDropdown_default']},
            'useFor': {'header': g_config.tb.createLabel('useFor_header', 'flash'),
                       'ally': g_config.tb.createLabel('useFor_ally', 'flash'),
                       'enemy': g_config.tb.createLabel('useFor_enemy', 'flash'),
                       'player': g_config.tb.createLabel('useFor_player', 'flash')},
            'backBtn': g_config.i18n['UI_flash_backBtn'],
            'saveBtn': g_config.i18n['UI_flash_saveBtn']
        }
        settings = {
            'remods': [],
            'whitelists': [],
            'isInHangar': g_config.isInHangar
        }
        for sname in sorted(g_config.modelsData['models']):
            modelsSettings = g_config.settings['remods'][sname]
            texts['remodNames'].append(sname)
            # noinspection PyTypeChecker
            settings['remods'].append({
                'useFor': {key: modelsSettings['swap' + key.capitalize()] for key in ('player', 'ally', 'enemy')},
                'whitelists': [[x for x in str(modelsSettings[team + 'Whitelist']).split(',') if x]
                               for team in ('player', 'ally', 'enemy')]})
        self.flashObject.as_updateData(texts, settings)

    def py_getRemodData(self):
        vehName = self.py_getCurrentVehicleName()
        if vehName:
            try:
                data = self.newRemodData
                data.clear()
                data['authorMessage'] = ''
                for team in ('player', 'ally', 'enemy'):
                    data[team + 'Whitelist'] = [vehName] if vehName else []
                vDesc = self.getCurrentVDesc()
                for key in TankPartNames.ALL + ('engine',):
                    data[key] = OrderedDict()
                for key in TankPartNames.ALL:
                    data[key]['undamaged'] = getattr(vDesc, key).models.undamaged
                chassis = data['chassis']
                for key in ('traces', 'tracks', 'wheels', 'groundNodes', 'trackNodes', 'splineDesc', 'trackParams'):
                    obj = getattr(vDesc.chassis, key)
                    if key != 'splineDesc':
                        obj = str(obj)
                        if key == 'tracks':
                            obj = obj.replace('TrackNode', 'TrackMaterials')
                        elif key == 'trackParams':
                            obj = obj.replace('TrackNode', 'TrackParams')
                    else:
                        obj = 'SplineConfig(%s)' % (', '.join(
                            ("%s=%s" % (attrName.strip('_'), repr(getattr(obj, attrName.strip('_')))) for attrName in
                             SplineConfig.__slots__)))
                    chassis[key] = obj
                chassis['hullPosition'] = vDesc.chassis.hullPosition.tuple()
                chassis['AODecals'] = []
                for decal in vDesc.chassis.AODecals:
                    decDict = {'transform': OrderedDict()}
                    for strIdx in xrange(4):
                        decDict['transform']['row%s' % strIdx] = []
                        for colIdx in xrange(3):
                            decDict['transform']['row%s' % strIdx].append(decal.get(strIdx, colIdx))
                for partName in ('chassis', 'engine'):
                    for key in ('wwsound', 'wwsoundPC', 'wwsoundNPC'):
                        data[partName][key] = getattr(getattr(vDesc, partName).sounds, key)
                pixieID = ''
                for key, value in g_cache._customEffects['exhaust'].iteritems():
                    if value == vDesc.hull.customEffects[0]._selectorDesc:
                        pixieID = key
                        break
                data['hull']['exhaust'] = {'nodes': ' '.join(vDesc.hull.customEffects[0].nodes), 'pixie': pixieID}
                for ids in (('_gunEffects', 'effects'), ('_gunReloadEffects', 'reloadEffect')):
                    for key, value in getattr(g_cache, ids[0]).items():
                        if value == getattr(vDesc.gun, ids[1]):
                            data['gun'][ids[1]] = key
                            break
                exclMask = vDesc.type.camouflage.exclusionMask
                if exclMask:
                    camouflage = data['camouflage'] = OrderedDict()
                    camouflage['exclusionMask'] = exclMask
                    camouflage['tiling'] = vDesc.type.camouflage.tiling
                for partName in TankPartNames.ALL[1:]:
                    part = getattr(vDesc, partName)
                    data[partName]['emblemSlots'] = []
                    exclMask = part.camouflage.exclusionMask if hasattr(part, 'camouflage') else ''
                    if exclMask:
                        camouflage = data[partName]['camouflage'] = OrderedDict()
                        camouflage['exclusionMask'] = exclMask
                        camouflage['tiling'] = part.camouflage.tiling
                    for slot in part.emblemSlots:
                        slotDict = OrderedDict()
                        for key in ('rayStart', 'rayEnd', 'rayUp'):
                            slotDict[key] = getattr(slot, key).tuple()
                        for key in ('size', 'hideIfDamaged', 'type', 'isMirrored', 'isUVProportional', 'emblemId'):
                            slotDict[key] = getattr(slot, key)
                        data[partName]['emblemSlots'].append(slotDict)
            except StandardError:
                SystemMessages.pushMessage(
                    'temp_SM' + g_config.i18n['UI_flash_remodCreate_error'], SystemMessages.SM_TYPE.Warning)
                traceback.print_exc()
        else:
            self.py_sendMessage('', 'Add', 'notSupported')
        modelDesc = getattr(self.getCurrentVDesc(), 'modelDesc', None)
        if modelDesc is not None:
            return {'isRemod': True, 'name': modelDesc.name, 'message': modelDesc.authorMessage, 'vehicleName': vehName,
                    'whitelists': [
                        [x for x in str(g_config.settings['remods'][modelDesc.name][team + 'Whitelist']).split(',')
                         if x] for team in ('player', 'ally', 'enemy')]}
        else:
            return {'isRemod': False, 'name': '', 'message': '', 'vehicleName': vehName,
                    'whitelists': [[vehName] if vehName else [] for _ in ('player', 'ally', 'enemy')]}

    @staticmethod
    def py_onShowRemod(remodIdx):
        g_config.previewRemod = sorted(g_config.modelsData['models'])[remodIdx]
        refreshCurrentVehicle()

    def py_onModelRestore(self):
        g_config.currentTeam = self.modeBackup
        g_config.previewRemod = None
        refreshCurrentVehicle()

    @staticmethod
    def getCurrentVDesc():
        return g_config.hangarSpace.space.getVehicleEntity().appearance._HangarVehicleAppearance__vDesc

    @staticmethod
    def py_getCurrentVehicleName():
        return RemodEnablerUI.getCurrentVDesc().name.split(':')[1].lower()

    def py_onRequestVehicleDelete(self, teamIdx):
        showI18nDialog(
            g_config.i18n['UI_flash_WLVehDelete_header'], g_config.i18n['UI_flash_WLVehDelete_text'], 'common/confirm',
            lambda proceed: self.flashObject.as_onVehicleDeleteConfirmed(proceed, teamIdx))

    @staticmethod
    def py_onSaveSettings(settings):
        remodNames = sorted(g_config.modelsData['models'])
        for idx, setObj in enumerate(settings.remods):
            modelsSettings = g_config.settings['remods'][remodNames[idx]]
            for key in ('player', 'ally', 'enemy'):
                modelsSettings['swap' + key.capitalize()] = getattr(setObj.useFor, key)
            for teamIdx, team in enumerate(('player', 'ally', 'enemy')):
                modelsSettings[team + 'Whitelist'] = ','.join(setObj.whitelists[teamIdx])
        loadJson(g_config.ID, 'settings', g_config.settings, g_config.configPath, True, quiet=not g_config.data['isDebug'])
        g_config.readCurrentSettings(not g_config.data['isDebug'])
        refreshCurrentVehicle()

    def py_onCreateRemod(self, settings):
        try:
            if not settings.name:
                SystemMessages.pushMessage('temp_SM' + g_config.i18n['UI_flash_remodCreate_name_empty'],
                                           SystemMessages.SM_TYPE.Warning)
                return
            from collections import OrderedDict
            data = self.newRemodData
            data['authorMessage'] = settings.message
            for teamIdx, team in enumerate(('player', 'ally', 'enemy')):
                data[team + 'Whitelist'] = ','.join(settings.whitelists[teamIdx])
            loadJson(g_config.ID, str(settings.name), data, g_config.configPath + 'remods/', True, False, sort_keys=False)
            g_config.readCurrentSettings()
            SystemMessages.pushMessage(
                'temp_SM' + g_config.i18n['UI_flash_remodCreate_success'], SystemMessages.SM_TYPE.CustomizationForGold)
        except StandardError:
            SystemMessages.pushMessage(
                'temp_SM' + g_config.i18n['UI_flash_remodCreate_error'], SystemMessages.SM_TYPE.Warning)
            traceback.print_exc()

    @staticmethod
    def py_sendMessage(xmlName, action, status):
        SystemMessages.pushMessage(
            'temp_SM%s<b>%s</b>.' % (g_config.i18n['UI_flash_vehicle%s_%s' % (action, status)], xmlName),
            SystemMessages.SM_TYPE.CustomizationForGold)

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
    if g_config.modelsData['enabled'] and not g_config.previewRemod:
        if checkKeys(g_config.data['ChangeViewHotkey']):
            newModeNum = (g_config.teams.index(g_config.currentTeam) + 1) % len(g_config.teams)
            g_config.currentTeam = g_config.teams[newModeNum]
            if g_config.data['isDebug']:
                print g_config.ID + ': changing display mode to', g_config.currentTeam
            SystemMessages.pushMessage(
                'temp_SM%s<b>%s</b>' % (g_config.i18n['UI_mode'], g_config.i18n['UI_mode_' + g_config.currentTeam]),
                SystemMessages.SM_TYPE.Warning)
            refreshCurrentVehicle()
        if checkKeys(g_config.data['SwitchRemodHotkey']):
            curTankType = g_config.currentTeam
            snameList = sorted(g_config.modelsData['models'].keys()) + ['']
            selected = g_config.modelsData['selected'][curTankType]
            vehName = RemodEnablerUI.py_getCurrentVehicleName()
            if selected.get(vehName) not in snameList:
                snameIdx = 0
            else:
                snameIdx = (snameList.index(selected[vehName]) + 1) % len(snameList)
            for Idx in xrange(snameIdx, len(snameList)):
                curPRecord = g_config.modelsData['models'].get(snameList[Idx])
                if snameList[Idx] and vehName not in curPRecord.whitelists[curTankType]:
                    continue
                selected[vehName] = getattr(curPRecord, 'name', '')
                loadJson(g_config.ID, 'remodsCache', g_config.modelsData['selected'], g_config.configPath, True,
                         quiet=not g_config.data['isDebug'])
                break
            refreshCurrentVehicle()
    if checkKeys(g_config.data['CollisionHotkey']):
        if g_config.collisionComparisonEnabled:
            g_config.collisionComparisonEnabled = False
            if g_config.data['isDebug']:
                print g_config.ID + ': disabling collision displaying'
            SystemMessages.pushMessage('temp_SM' + g_config.i18n['UI_disableCollisionComparison'],
                                       SystemMessages.SM_TYPE.CustomizationForGold)
        elif g_config.collisionEnabled:
            g_config.collisionEnabled = False
            g_config.collisionComparisonEnabled = True
            if g_config.data['isDebug']:
                print g_config.ID + ': enabling collision display comparison mode'
            SystemMessages.pushMessage('temp_SM' + g_config.i18n['UI_enableCollisionComparison'],
                                       SystemMessages.SM_TYPE.CustomizationForGold)
        else:
            g_config.collisionEnabled = True
            if g_config.data['isDebug']:
                print g_config.ID + ': enabling collision display'
            SystemMessages.pushMessage('temp_SM' + g_config.i18n['UI_enableCollision'],
                                       SystemMessages.SM_TYPE.CustomizationForGold)
        refreshCurrentVehicle()


def inj_hkKeyEvent(event):
    LobbyApp = g_appLoader.getDefLobbyApp()
    try:
        if LobbyApp and g_config.data['enabled']:
            lobbyKeyControl(event)
    except StandardError:
        print g_config.ID + ': ERROR at inj_hkKeyEvent'
        traceback.print_exc()


InputHandler.g_instance.onKeyDown += inj_hkKeyEvent
InputHandler.g_instance.onKeyUp += inj_hkKeyEvent
g_config = ConfigInterface()


@overrideMethod(LoginView, '_populate')
def new_Login_populate(base, self):
    base(self)
    g_config.isInHangar = False


@overrideMethod(LobbyView, '_populate')
def new_Lobby_populate(base, self):
    base(self)
    g_config.isInHangar = True
