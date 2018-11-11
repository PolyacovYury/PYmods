# -*- coding: utf-8 -*-
import BigWorld
import Keys
import Math
import glob
import os
import traceback
from PYmodsCore import PYmodsConfigInterface, refreshCurrentVehicle, checkKeys, loadJson, showI18nDialog, overrideMethod, \
    remDups
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
from items.components.chassis_components import SplineConfig
from items.components.component_constants import ALLOWED_EMBLEM_SLOTS
from items.components.shared_components import EmblemSlot
from items.vehicles import g_cache
from skeletons.gui.shared.utils import IHangarSpace
from vehicle_systems.tankStructure import TankPartNames
from . import __date__, __modID__


class ConfigInterface(PYmodsConfigInterface):
    hangarSpace = dependency.descriptor(IHangarSpace)
    modelDescriptor = property(lambda self: {
            'name': '',
            'message': '',
            'whitelist': [],
            'chassis': {'undamaged': '', 'AODecals': [], 'hullPosition': [], 'soundID': ''},
            'hull': {'undamaged': '', 'emblemSlots': [], 'exhaust': {'nodes': [], 'pixie': ''},
                     'camouflage': {'exclusionMask': '', 'tiling': [1.0, 1.0, 0.0, 0.0]}},
            'turret': {'undamaged': '', 'emblemSlots': [],
                       'camouflage': {'exclusionMask': '', 'tiling': [1.0, 1.0, 0.0, 0.0]}},
            'gun': {'undamaged': '', 'emblemSlots': [], 'soundID': '',
                    'camouflage': {'exclusionMask': '', 'tiling': [1.0, 1.0, 0.0, 0.0]}},
            'engine': {'soundID': ''},
            'common': {'camouflage': {'exclusionMask': '', 'tiling': [1.0, 1.0, 0.0, 0.0]}}})

    def __init__(self):
        self.teams = ('player', 'ally', 'enemy')
        self.settings = {}
        self.modelsData = {'models': {}, 'selected': {'player': {}, 'ally': {}, 'enemy': {}}}
        self.isModAdded = False
        self.collisionMode = 0
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
            kwargs = dict(id='RemodEnablerUI', enabled=self.data['enabled'] and bool(self.modelsData['models']))
            try:
                BigWorld.g_modsListApi.updateModification(**kwargs)
            except AttributeError:
                BigWorld.g_modsListApi.updateMod(**kwargs)

    def readOrdered(self, new_path):
        import json
        config_new = None
        if os.path.isfile(new_path):
            data, excluded, success = cls.json_file_read(new_path, False)
            if success:
                try:
                    config_new = cls.byte_ify(json.loads(data, object_pairs_hook=OrderedDict))
                except StandardError as e:
                    print new_path
                    print e
        return config_new

    def migrateSettings(self, old_data, new_data):
        whitelist = []
        for team in self.teams:
            new_data[team] = new_data.get(team, old_data.pop('swap' + team.capitalize(), True))
            whitelist.extend(x.strip() for x in old_data.pop(team + 'Whitelist', '').split(',') if x.strip())
        new_data['whitelist'] = sorted(remDups(whitelist + new_data.get('whitelist', [])))

    def migrateConfigs(self):
        settings = loadJson(self.ID, 'settings', self.settings, self.configPath)
        if settings and 'remods' in settings:
            for sname, remodData in settings['remods'].items():
                if not remodData.pop('enabled', True):
                    print self.ID + ': WARNING! Disabled remod detected:', sname + (
                        '. Remod disabling is not supported anymore, delete unneeded remods.'
                        'If game crashed - this is, probably, the reason.')
                self.migrateSettings(remodData, remodData)
            loadJson(self.ID, 'settings', settings['remods'], self.configPath, True)

        selectedData = loadJson(self.ID, 'remodsCache', self.modelsData['selected'], self.configPath)
        for key in selectedData.keys():
            if not key.islower():
                selectedData[key.lower()] = selectedData.pop(key)
            if key.lower() == 'remod':
                del selectedData[key.lower()]
        loadJson(self.ID, 'remodsCache', selectedData, self.configPath, True)

        from .remods import migrate_chassis_config
        configsPath = self.configPath + 'remods/*.json'
        for configPath in glob.iglob(configsPath):
            sname = os.path.basename(configPath).split('.')[0]
            old_conf = self.readOrdered(configPath)
            if not old_conf:
                print self.ID + ': error while reading', os.path.basename(configPath) + '.'
                continue
            new_conf = OrderedDict()
            new_conf['message'] = old_conf.get('authorMessage', old_conf.get('message', ''))
            self.migrateSettings(old_conf, new_conf)
            for key, val in old_conf.items():
                if key in ('authorMessage',) or 'Whitelist' in key or 'swap' in key or (
                        key == 'engine' and isinstance(val, dict)):  # engine is dict in old config and string in nre
                    continue
                elif key == 'gun':
                    val = OrderedDict((k, v) for k, v in val.iteritems() if 'ffect' not in k)
                elif key == 'hull':
                    if 'exhaust' in val and 'nodes' in val['exhaust'] and isinstance(val['exhaust']['nodes'], basestring):
                        val['exhaust']['nodes'] = val['exhaust']['nodes'].split()
                elif key == 'chassis':
                    val = migrate_chassis_config(val)
                new_conf[key] = val
            loadJson(self.ID, sname, new_conf, self.configPath + 'remods/', True, sort_keys=False)

    def readCurrentSettings(self, quiet=True):
        super(ConfigInterface, self).readCurrentSettings()
        self.settings = loadJson(self.ID, 'settings', self.settings, self.configPath)
        self.modelsData['selected'] = selectedData = loadJson(
            self.ID, 'remodsCache', self.modelsData['selected'], self.configPath)
        configsDir = self.configPath + 'remods/'
        remodTanks = set()
        for configPath in glob.iglob(configsDir + '*.json'):
            fName = str(os.path.basename(configPath))  # PYCharm thinks that this is unicode
            sName = fName.split('.')[0]
            confDict = loadJson(self.ID, sName, {}, configsDir, encrypted=True)
            if not confDict:
                print self.ID + ': error while reading', fName + '.'
                continue
            settingsDict = self.settings.setdefault(sName, {team: confDict[team] for team in self.teams})
            self.modelsData['models'][sName] = pRecord = self.modelDescriptor
            pRecord['name'] = sName
            pRecord['message'] = confDict.get('message', '')
            settingsDict['whitelist'] = pRecord['whitelist'] = whitelist = remDups(
                x.strip() for x in settingsDict.get('whitelist', confDict['whitelist']) if x.strip())
            for xmlName in whitelist:
                remodTanks.add(xmlName)
                for team in selectedData:
                    if xmlName not in selectedData[team] or selectedData[team][xmlName] is None:
                        if settingsDict[team]:
                            selectedData[team][xmlName] = sName
                        else:
                            selectedData[team][xmlName] = None
            if self.data['isDebug']:
                if not whitelist:
                    print self.ID + ': empty whitelist for', sName + '.'
                else:
                    print self.ID + ': whitelist for', sName + ':', whitelist
            for key, data in pRecord.iteritems():
                if key in ('name', 'message', 'whitelist'):
                    continue
                if key == 'common':
                    confSubDict = confDict
                else:
                    confSubDict = confDict.get(key)
                if not confSubDict:
                    continue
                if 'undamaged' in data:
                    data['undamaged'] = confSubDict['undamaged']
                if 'AODecals' in data and 'AODecals' in confSubDict and 'hullPosition' in confSubDict:
                    data['AODecals'] = []
                    for subList in confSubDict['AODecals']:
                        m = Math.Matrix()
                        for strNum, row in enumerate(subList):
                            for colNum, elemNum in enumerate(row):
                                m.setElement(strNum, colNum, elemNum)
                        data['AODecals'].append(m)
                    data['hullPosition'] = confSubDict['hullPosition']
                if 'camouflage' in data and 'exclusionMask' in confSubDict.get('camouflage', {}):
                    data['camouflage']['exclusionMask'] = confSubDict['camouflage']['exclusionMask']
                    if 'tiling' in confSubDict['camouflage']:
                        data['camouflage']['tiling'] = confSubDict['camouflage']['tiling']
                elif key == 'common' and self.data['isDebug']:
                    print self.ID + ': default camomask not found for', sName
                if 'emblemSlots' in data:
                    data['emblemSlots'] = slots = []
                    for subDict in confSubDict.get('emblemSlots', []):
                        if subDict['type'] not in ALLOWED_EMBLEM_SLOTS:
                            print g_config.ID + (
                                ': not supported emblem slot type:'), subDict['type'] + ', expected:', ALLOWED_EMBLEM_SLOTS
                            continue
                        descr = EmblemSlot(
                            Math.Vector3(tuple(subDict['rayStart'])), Math.Vector3(tuple(subDict['rayEnd'])),
                            Math.Vector3(tuple(subDict['rayUp'])), subDict['size'],
                            subDict.get('hideIfDamaged', False), subDict['type'],
                            subDict.get('isMirrored', False),
                            subDict.get('isUVProportional', True), subDict.get('emblemId', None))
                        slots.append(descr)
                if 'exhaust' in data and 'exhaust' in confSubDict:
                    if 'nodes' in confSubDict['exhaust']:
                        data['exhaust']['nodes'] = confSubDict['exhaust']['nodes']
                    if 'pixie' in confSubDict['exhaust']:
                        data['exhaust']['pixie'] = confSubDict['exhaust']['pixie']
                if key == 'chassis':
                    for k in ('traces', 'tracks', 'wheels', 'groundNodes', 'trackNodes', 'splineDesc', 'trackParams'):
                        data[k] = confSubDict[k]
                if 'soundID' in data and 'soundID' in confSubDict:
                    data['soundID'] = confSubDict['soundID']
            if self.data['isDebug']:
                print self.ID + ': config for', sName, 'loaded.'

        for sName in self.settings.keys():
            if sName not in self.modelsData['models']:
                del self.settings[sName]

        if not self.modelsData['models']:
            if not quiet:
                print self.ID + ': no configs found, model module standing down.'
        for team in self.teams:
            for xmlName in selectedData[team].keys():
                if xmlName not in remodTanks:
                    del selectedData[team][xmlName]
                    continue
                if selectedData[team][xmlName] is None or (
                        selectedData[team][xmlName] and selectedData[team][xmlName] not in self.modelsData['models']):
                    selectedData[team][xmlName] = next(
                        (sName for sName in sorted(self.modelsData['models']) if xmlName in self.settings[sName]['whitelist']
                         and self.settings[sName][team]), None) or ''
        loadJson(self.ID, 'remodsCache', selectedData, self.configPath, True, quiet=quiet)
        loadJson(self.ID, 'settings', self.settings, self.configPath, True, quiet=quiet)

    def load(self):
        self.migrateConfigs()
        super(ConfigInterface, self).load()

    def findModelDesc(self, xmlName, currentTeam, notForPreview=True):
        if not self.modelsData['models']:
            return
        selected = self.modelsData['selected'][currentTeam]
        if not self.previewRemod or notForPreview:
            if xmlName not in selected or not selected[xmlName]:
                return
            return self.modelsData['models'][selected[xmlName]]
        else:
            return self.modelsData['models'][self.previewRemod]

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
            icon='gui/flash/RemodEnabler.png', enabled=self.data['enabled'] and bool(self.modelsData['models']),
            login=True, lobby=True, callback=lambda: (
                    g_appLoader.getDefLobbyApp().containerManager.getContainer(ViewTypes.TOP_WINDOW).getViewCount()
                    or g_appLoader.getDefLobbyApp().loadView(SFViewLoadParams('RemodEnablerUI'))))
        try:
            BigWorld.g_modsListApi.addModification(**kwargs)
        except AttributeError:
            BigWorld.g_modsListApi.addMod(**kwargs)
        self.isModAdded = True

    def lobbyKeyControl(self, event):
        if not event.isKeyDown() or self.isMSAWindowOpen:
            return
        if self.modelsData['models'] and not self.previewRemod:
            if checkKeys(self.data['ChangeViewHotkey']):
                newModeNum = (self.teams.index(self.currentTeam) + 1) % len(self.teams)
                self.currentTeam = self.teams[newModeNum]
                if self.data['isDebug']:
                    print self.ID + ': changing display mode to', self.currentTeam
                SystemMessages.pushMessage(
                    'temp_SM%s<b>%s</b>' % (self.i18n['UI_mode'], self.i18n['UI_mode_' + self.currentTeam]),
                    SystemMessages.SM_TYPE.Warning)
                refreshCurrentVehicle()
            if checkKeys(self.data['SwitchRemodHotkey']):
                curTankType = self.currentTeam
                snameList = sorted(self.modelsData['models'].keys()) + ['']
                selected = self.modelsData['selected'][curTankType]
                vehName = RemodEnablerUI.py_getCurrentVehicleName()
                snameIdx = (snameList.index(selected[vehName]) + 1) % len(snameList)
                for Idx in xrange(snameIdx, len(snameList) - 1):
                    curPRecord = self.modelsData['models'][snameList[Idx]]
                    if vehName not in curPRecord['whitelist']:
                        continue
                    selected[vehName] = curPRecord['name']
                    break
                else:
                    selected[vehName] = ''
                loadJson(self.ID, 'remodsCache', self.modelsData['selected'], self.configPath, True,
                         quiet=not self.data['isDebug'])
                refreshCurrentVehicle()
        if checkKeys(self.data['CollisionHotkey']):
            self.collisionMode += 1
            self.collisionMode %= 3
            if self.collisionMode == 0:
                if self.data['isDebug']:
                    print self.ID + ': disabling collision displaying'
                SystemMessages.pushMessage('temp_SM' + self.i18n['UI_disableCollisionComparison'],
                                           SystemMessages.SM_TYPE.CustomizationForGold)
            elif self.collisionMode == 2:
                if self.data['isDebug']:
                    print self.ID + ': enabling collision display comparison mode'
                SystemMessages.pushMessage('temp_SM' + self.i18n['UI_enableCollisionComparison'],
                                           SystemMessages.SM_TYPE.CustomizationForGold)
            else:
                if self.data['isDebug']:
                    print self.ID + ': enabling collision display'
                SystemMessages.pushMessage('temp_SM' + self.i18n['UI_enableCollision'],
                                           SystemMessages.SM_TYPE.CustomizationForGold)
            refreshCurrentVehicle()


class RemodEnablerUI(AbstractWindowView):
    def _populate(self):
        super(self.__class__, self)._populate()
        self.newRemodData = OrderedDict()

    def objToDict(self, obj):
        if isinstance(obj, list):
            return [self.objToDict(o) for o in obj]
        elif hasattr(obj, 'toDict'):
            return {k: self.objToDict(v) for k, v in obj.toDict().iteritems()}
        else:
            return obj

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

    def py_onSaveSettings(self, settings):
        print self.objToDict(settings)
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


def inj_hkKeyEvent(event):
    LobbyApp = g_appLoader.getDefLobbyApp()
    try:
        if LobbyApp and g_config.data['enabled']:
            g_config.lobbyKeyControl(event)
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
