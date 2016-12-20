# -*- coding: utf-8 -*-
import glob
import heapq
import os
import random
import time
import traceback
import weakref

import BigWorld
import ResMgr

import CurrentVehicle
import Keys
import PYmodsCore
import items.vehicles
import nations
from Account import Account
from CurrentVehicle import g_currentPreviewVehicle, g_currentVehicle
from gui import InputHandler, SystemMessages, g_tankActiveCamouflage
from gui.ClientHangarSpace import ClientHangarSpace
from gui.Scaleform.daapi.settings.views import VIEW_ALIAS
from gui.Scaleform.daapi.view.lobby.LobbyView import LobbyView
from gui.Scaleform.daapi.view.lobby.customization.main_view import MainView
from gui.Scaleform.framework import ScopeTemplates, ViewSettings, ViewTypes, g_entitiesFactories
from gui.Scaleform.framework.entities.abstract.AbstractWindowView import AbstractWindowView
from gui.app_loader import g_appLoader
from gui.customization import g_customizationController
from gui.customization.data_aggregator import DataAggregator
from gui.customization.shared import CUSTOMIZATION_TYPE
from helpers import i18n
from items import _xml
from items.vehicles import CAMOUFLAGE_KINDS, CAMOUFLAGE_KIND_INDICES
from vehicle_systems.CompoundAppearance import CompoundAppearance

res = ResMgr.openSection('../paths.xml')
sb = res['Paths']
vl = sb.values()[0]
if vl is not None and not hasattr(BigWorld, 'curCV'):
    BigWorld.curCV = vl.asString


class CamoSelectorUI(AbstractWindowView):
    def _populate(self):
        super(CamoSelectorUI, self)._populate()
        if self._isDAAPIInited():
            self.createData()
            _config.UIProxy = weakref.proxy(self)

    def createData(self):
        # noinspection PyUnresolvedReferences
        texts = {
            'header': _config.i18n['UI_flash_header'],
            'nations': map(lambda x: i18n.makeString('#nations:%s' % x), nations.NAMES) + [
                _config.i18n['UI_flash_camoMode_modded'], _config.i18n['UI_flash_camoMode_international']],
            'camouflages': [[] for _ in xrange(len(nations.NAMES) + 2)],
            'randomOptions': {'label': _config.i18n['UI_flash_randomOptions_text'],
                              'tooltip': _config.i18n['UI_flash_randomOptions_tooltip'],
                              'options': [_config.i18n['UI_flash_randomOptions_OFF'],
                                          _config.i18n['UI_flash_randomOptions_overrideRandom'],
                                          _config.i18n['UI_flash_randomOptions_includeInRandom']]},
            'useFor': {'header': {'label': _config.i18n['UI_flash_useFor_header_label'],
                                  'tooltip': _config.i18n['UI_flash_useFor_header_tooltip']},
                       'ally': {'label': _config.i18n['UI_flash_useFor_ally_label'],
                                'tooltip': _config.i18n['UI_flash_useFor_ally_tooltip']},
                       'enemy': {'label': _config.i18n['UI_flash_useFor_enemy_label'],
                                 'tooltip': _config.i18n['UI_flash_useFor_enemy_tooltip']}},
            'kinds': {'header': {'label': _config.i18n['UI_flash_kinds_header_label'],
                                 'tooltip': _config.i18n['UI_flash_kinds_header_tooltip']},
                      'winter': {'label': _config.i18n['UI_flash_kinds_winter_label'],
                                 'tooltip': _config.i18n['UI_flash_kinds_winter_tooltip']},
                      'summer': {'label': _config.i18n['UI_flash_kinds_summer_label'],
                                 'tooltip': _config.i18n['UI_flash_kinds_summer_tooltip']},
                      'desert': {'label': _config.i18n['UI_flash_kinds_desert_label'],
                                 'tooltip': _config.i18n['UI_flash_kinds_desert_tooltip']}},
            'installTooltip': _config.i18n['UI_flash_installTooltip'],
            'save': _config.i18n['UI_flash_save']}
        settings = [[] for _ in xrange(len(nations.NAMES) + 2)]
        for idx, nation in enumerate(nations.NAMES + ('modded', 'international')):
            nationID = min(idx, len(nations.NAMES) - 1)
            camouflages = items.vehicles.g_cache.customization(nationID)['camouflages']
            camoNames = {camouflage['name']: camoID for camoID, camouflage in camouflages.items()}
            for camoName in camoNames.keys():
                if nation == 'modded':
                    if camoName not in _config.camouflages['modded']:
                        del camoNames[camoName]
                elif nation == 'international':
                    if camoName not in _config.origInterCamo:
                        del camoNames[camoName]
                elif camoName in _config.interCamo:
                    del camoNames[camoName]
            for camoName in sorted(camoNames.keys()):
                camoID = camoNames[camoName]
                camouflageDesc = camouflages[camoID]
                _config.camouflages.get(nation, {})
                camouflage = _config.camouflages.get(nation, {}).get(camoName, {})
                texts['camouflages'][idx].append(camoName)
                camoSettings = {'randomOption': camouflage.get('random_mode', 2),
                                'camoInShop': g_customizationController.dataAggregator._elementIsInShop(
                                    camoID, 0, nationID),
                                'isInternational': camoName in _config.interCamo,
                                'useFor': {'ally': camouflage.get('useForAlly', True),
                                           'enemy': camouflage.get('useForEnemy', True)},
                                'kinds': {}}
                for key, kind in CAMOUFLAGE_KINDS.items():
                    if camouflage.get('kinds') is not None:
                        camoSettings['kinds'][key] = key in camouflage['kinds']
                    else:
                        camoSettings['kinds'][key] = kind == camouflageDesc['kind']
                settings[idx].append(camoSettings)
        self.flashObject.as_syncData({'texts': texts, 'settings': settings, 'ids': _config.backup})
        self.changeNation(self.getCurrentNation())

    @staticmethod
    def getCurrentNation():
        if g_currentPreviewVehicle.isPresent():
            vDesc = g_currentPreviewVehicle.item.descriptor
        elif g_currentVehicle.isPresent():
            vDesc = g_currentVehicle.item.descriptor
        else:
            raise AttributeError('g_currentVehicle.item.descriptor not found')
        return vDesc.type.customizationNationID

    def changeNation(self, nationID):
        _config.backupNationID = nationID
        if self._isDAAPIInited():
            self.flashObject.as_changeNation(nationID)

    def onWindowClose(self):
        _config.activePreviewCamo = None
        SystemMessages.pushMessage('PYmods_SM' + _config.i18n['UI_camouflageRestore'],
                                   SystemMessages.SM_TYPE.CustomizationForGold)
        g_currentPreviewVehicle.refreshModel()
        _config.UIProxy = None
        self.destroy()

    def as_isModalS(self):
        if self._isDAAPIInited():
            return False

    @staticmethod
    def py_onSettings(settings):
        for idx, nation in enumerate(nations.NAMES + ('modded', 'international')):
            nationID = min(idx, len(nations.NAMES) - 1)
            camouflages = items.vehicles.g_cache.customization(nationID)['camouflages']
            nationConf = _config.camouflages.setdefault(nation, {})
            camoNames = {camouflage['name']: camoID for camoID, camouflage in camouflages.items()}
            for camoName in camoNames.keys():
                if nation == 'modded':
                    if camoName not in _config.camouflages['modded']:
                        del camoNames[camoName]
                elif nation == 'international':
                    if camoName not in _config.origInterCamo:
                        del camoNames[camoName]
                elif camoName in _config.interCamo:
                    del camoNames[camoName]
            for camoNum, camoName in enumerate(sorted(camoNames.keys())):
                nationConf.setdefault(camoName, {})
                camoID = camoNames[camoName]
                camouflageDesc = camouflages[camoID]
                camoInShop = g_customizationController.dataAggregator._elementIsInShop(camoID, 0, nationID)
                isInter = camoName in _config.interCamo
                newSettings = settings[idx][camoNum]
                nationConf[camoName]['random_mode'] = newSettings.randomOption
                nationConf[camoName]['useForAlly'] = newSettings.useFor.ally
                nationConf[camoName]['useForEnemy'] = newSettings.useFor.enemy
                enabledKinds = []
                for key in ('winter', 'summer', 'desert'):
                    if getattr(newSettings.kinds, key):
                        enabledKinds.append(key)
                    nationConf[camoName]['kinds'] = ','.join(enabledKinds)
                for confFolderName in _config.configFolders:
                    if camoName in _config.configFolders[confFolderName]:
                        _config.loadJson('settings', dict(
                            (key, nationConf[key]) for key in _config.configFolders[confFolderName]),
                                         _config.configPath + confFolderName + '/', True, False)
                if nationConf[camoName]['random_mode'] == 2 or nationConf[camoName]['random_mode'] == 1 and not isInter:
                    del nationConf[camoName]['random_mode']
                kindNames = filter(None, nationConf[camoName]['kinds'].split(','))
                if len(kindNames) == 1 and kindNames[0] == CAMOUFLAGE_KIND_INDICES[camouflageDesc['kind']] or camoInShop:
                    del nationConf[camoName]['kinds']
                for team in ('Ally', 'Enemy'):
                    if nationConf[camoName]['useFor%s' % team]:
                        del nationConf[camoName]['useFor%s' % team]
                if not nationConf[camoName]:
                    del nationConf[camoName]
            if nation in _config.camouflages and not nationConf and nation != 'modded':
                del _config.camouflages[nation]
        newSettings = {}
        if _config.disable:
            newSettings['disable'] = _config.disable
        for nation in nations.NAMES:
            if nation in _config.camouflages:
                newSettings[nation] = _config.camouflages[nation]
        _config.loadJson('settings', newSettings, _config.configPath, True)

        SystemMessages.pushMessage('PYmods_SM' + _config.i18n['UI_camouflageSave'],
                                   SystemMessages.SM_TYPE.CustomizationForGold)
        g_currentPreviewVehicle.refreshModel()

    @staticmethod
    def py_printLog(*args):
        print (arg for arg in args)

    @staticmethod
    def py_onShowPreset(nationID, mode, camoID):
        nationName = ('modded', 'international', nations.NAMES[nationID])[mode]
        camouflages = items.vehicles.g_cache.customization(nationID)['camouflages']
        camoNames = {camouflage['name']: camoID for camoID, camouflage in camouflages.items()}
        for camoName in camoNames.keys():
            if nationName == 'modded':
                if camoName not in _config.camouflages['modded']:
                    del camoNames[camoName]
            elif nationName == 'international':
                if camoName not in _config.origInterCamo:
                    del camoNames[camoName]
            elif camoName in _config.interCamo:
                del camoNames[camoName]
        _config.activePreviewCamo = sorted(camoNames.keys())[int(camoID)]
        SystemMessages.pushMessage('PYmods_SM' + _config.i18n['UI_camouflagePreview'] +
                                   _config.activePreviewCamo.join(('<b>', '</b>')),
                                   SystemMessages.SM_TYPE.CustomizationForGold)
        _config.backup['mode'] = mode
        newIdx = nationID if mode == 2 else (len(nations.NAMES) + mode - 2)
        _config.backup['camoID'][newIdx] = camoID
        g_currentPreviewVehicle.refreshModel()

    @staticmethod
    def py_onApplyPreset():
        installSelectedCamo()


class _Config(PYmodsCore._Config):
    def __init__(self):
        super(_Config, self).__init__(__file__)
        self.version = '2.5.1 (%s)' % self.version
        self.author = '%s (thx to tratatank, Blither!)' % self.author
        self.defaultKeys = {'selectHotkey': [Keys.KEY_F5, [Keys.KEY_LCONTROL, Keys.KEY_RCONTROL]],
                            'selectHotKey': ['KEY_F5', ['KEY_LCONTROL', 'KEY_RCONTROL']]}
        self.data = {'enabled': True, 'doRandom': True, 'Debug': True, 'useBought': True, 'hangarCamoKind': 0,
                     'selectHotkey': self.defaultKeys['selectHotkey'], 'selectHotKey': self.defaultKeys['selectHotKey']}
        self.disable = []
        self.i18n = {
            'UI_description': 'Camouflage selector',
            'UI_flash_header': 'Camouflages setup',
            'UI_flash_header_tooltip': ('Advanced settings for camouflages added by CamoSelector by '
                                        '<font color=\'#DD7700\'><b>Polyacov_Yury</b></font>'),
            'UI_flash_camoMode_modded': 'Modded',
            'UI_flash_camoMode_international': 'International',
            'UI_flash_randomOptions_text': 'Random selection mode',
            'UI_flash_randomOptions_tooltip': (
                '{HEADER}Description:{/HEADER}{BODY} • <b>OFF</b>: camouflage is disabled.\n • <b>Override random '
                'selection</b>: this camouflage gets included into a list of camouflages which appear <b>instead of</b> '
                'default ones when a random option is being selected.\n • <b>Include in random selection</b>: this '
                'camouflage is included into a list of camouflages which may appear <b>along with</b> default ones when a '
                'random option is being selected. Please note that these camouflages get <b>overridden</b> by ones that '
                'have an option above selected.{/BODY}'),
            'UI_flash_randomOptions_OFF': 'OFF',
            'UI_flash_randomOptions_overrideRandom': 'Override random selection',
            'UI_flash_randomOptions_includeInRandom': 'Include in random selection',
            'UI_flash_useFor_header_label': 'Use this camouflage for:',
            'UI_flash_useFor_header_tooltip': (
                '{HEADER}Description:{/HEADER}{BODY}This camouflage will be used for these groups of tanks.\n'
                '<b>Attention</b>: a camouflage with no tick set will be considered disabled.{/BODY}'),
            'UI_flash_useFor_ally_label': 'Player and allies',
            'UI_flash_useFor_ally_tooltip': '',
            'UI_flash_useFor_enemy_label': 'Enemies',
            'UI_flash_useFor_enemy_tooltip': '',
            'UI_flash_kinds_header_label': 'Camouflage kinds:',
            'UI_flash_kinds_header_tooltip': (
                '{HEADER}Description:{/HEADER}{BODY}This camouflage will appear on these kinds of maps.\n'
                '<b>Attention</b>: a camouflage with no tick set will be considered disabled.{/BODY}'),
            'UI_flash_kinds_winter_label': 'Winter',
            'UI_flash_kinds_winter_tooltip': '',
            'UI_flash_kinds_summer_label': 'Summer',
            'UI_flash_kinds_summer_tooltip': '',
            'UI_flash_kinds_desert_label': 'Desert',
            'UI_flash_kinds_desert_tooltip': '',
            'UI_flash_installTooltip': '{HEADER}Install{/HEADER}{BODY}"Buy" this camouflage for selected tank.{/BODY}',
            'UI_flash_save': 'Save',
            'UI_setting_doRandom_text': 'Select random camouflages',
            'UI_setting_doRandom_tooltip': (
                '{HEADER}Description:{/HEADER}{BODY}If enabled, mod will select a random available camouflage if no '
                'other option is provided.{/BODY}'),
            'UI_setting_useBought_text': 'Use bought camouflages in battle',
            'UI_setting_useBought_tooltip': ('{HEADER}Description:{/HEADER}{BODY}If enabled, mod will preserve '
                                             "bought camouflages on other players' tanks.{/BODY}"),
            'UI_setting_select_text': 'Camouflage select hotkey',
            'UI_setting_select_tooltip': (
                '{HEADER}Description:{/HEADER}{BODY}This hotkey will permanently install currently selected '
                'preview camouflage to current tank.{/BODY}'),
            'UI_setting_hangarCamoKind_text': 'Hangar camouflage kind',
            'UI_setting_hangarCamoKind_tooltip': ('{HEADER}Description:{/HEADER}{BODY}This setting controls '
                                                  'a kind which is used in hangar.{/BODY}'),
            'UI_setting_hangarCamo_winter': 'Winter', 'UI_setting_hangarCamo_summer': 'Summer',
            'UI_setting_hangarCamo_desert': 'Desert', 'UI_setting_hangarCamo_random': 'Random',
            'UI_camouflagePreview': '<b>Camouflage Selector:</b>\nCamouflage previewing:\n',
            'UI_camouflagePreviewError': '<b>Camouflage Selector:</b>\nCamouflage not found:\n',
            'UI_camouflageRestore': '<b>Camouflage Selector:</b>\nLoading previous camouflage.',
            'UI_camouflageSave': '<b>Camouflage Selector:</b>\nSaving custom camouflage settings.',
            'UI_camouflageSelect': '<b>Camouflage Selector:</b>\nInstalling selected camouflages.',
            'UI_installCamouflage': ('<b>Camouflage Selector:</b>\nCamouflage installed: <b>{name}</b>, '
                                     'camouflage kind: <b>{kind}</b>'),
            'UI_installCamouflage_already': ('<b>Camouflage Selector:</b>\nCamouflage <b>already</b> installed: '
                                             '<b>{name}</b>, camouflage kind: <b>{kind}</b>'),
            'UI_customOrInvalid': ('<b>Camouflage Selector:</b>\nCustom or invalid camouflage detected for '
                                   '<b>{kind}</b> camouflages: <b>{name}</b>'),
            'UI_customOrInvalid_winter': 'winter', 'UI_customOrInvalid_summer': 'summer',
            'UI_customOrInvalid_desert': 'desert'}
        self.hangarCamoCache = {}
        self.camouflagesCache = {}
        self.camouflages = {}
        self.configFolders = {}
        self.currentOverriders = dict.fromkeys(('Ally', 'Enemy'))
        self.interCamo = []
        self.origInterCamo = []
        self.activePreviewCamo = None
        self.UIProxy = None
        self.backupNationID = None
        self.backup = {'mode': 0, 'camoID': (len(nations.NAMES) + 2) * [0]}
        self.loadLang()

    def template_settings(self):
        return {'modDisplayName': self.i18n['UI_description'],
                'settingsVersion': 200,
                'enabled': self.data['enabled'],
                'column1': [{'type': 'Dropdown',
                             'text': self.i18n['UI_setting_hangarCamoKind_text'],
                             'tooltip': self.i18n['UI_setting_hangarCamoKind_tooltip'],
                             'itemRenderer': 'DropDownListItemRendererSound',
                             'options': [{'label': self.i18n['UI_setting_hangarCamo_winter']},
                                         {'label': self.i18n['UI_setting_hangarCamo_summer']},
                                         {'label': self.i18n['UI_setting_hangarCamo_desert']},
                                         {'label': self.i18n['UI_setting_hangarCamo_random']}],
                             'width': 200,
                             'value': self.data['hangarCamoKind'],
                             'varName': 'hangarCamoKind'},
                            {'type': 'CheckBox',
                             'text': self.i18n['UI_setting_doRandom_text'],
                             'value': self.data['doRandom'],
                             'tooltip': self.i18n['UI_setting_doRandom_tooltip'],
                             'varName': 'doRandom'}],
                'column2': [{'type': 'HotKey',
                             'text': self.i18n['UI_setting_select_text'],
                             'tooltip': self.i18n['UI_setting_select_tooltip'],
                             'value': self.data['selectHotkey'],
                             'defaultValue': self.defaultKeys['selectHotkey'],
                             'varName': 'selectHotkey'},
                            {'type': 'CheckBox',
                             'text': self.i18n['UI_setting_useBought_text'],
                             'value': self.data['useBought'],
                             'tooltip': self.i18n['UI_setting_useBought_tooltip'],
                             'varName': 'useBought'}]}

    def onWindowClose(self):
        try:
            from gui.mods import mod_RemodEnabler
        except StandardError:
            g_currentPreviewVehicle.refreshModel()

    def apply_settings(self, settings):
        super(_Config, self).apply_settings(settings)
        BigWorld.g_modsListApi.updateMod('CamoSelectorUI', enabled=self.data['enabled'])

    def readCamouflages(self, doShopCheck):
        self.camouflages = {'modded': {}}
        self.camouflagesCache = self.loadJson('camouflagesCache', self.camouflagesCache, self.configPath)
        try:
            for dirName in glob.iglob(self.configPath + '*'):
                if os.path.isdir(dirName):
                    self.configFolders[os.path.basename(dirName)] = confFolder = set()
                    settings = self.loadJson('settings', {}, dirName + '/')
                    for key in settings:
                        confFolder.add(key)
                    self.camouflages['modded'].update(settings)
        except StandardError:
            traceback.print_exc()

        self.interCamo = map(lambda x: x['name'], items.vehicles.g_cache.customization(0)['camouflages'].itervalues())
        for nationID in xrange(1, len(nations.NAMES)):
            camouflages = items.vehicles.g_cache.customization(nationID)['camouflages']
            camoNames = map(lambda x: x['name'], camouflages.itervalues())
            self.interCamo = filter(lambda x: x in camoNames, self.interCamo)
        self.origInterCamo = filter(lambda x: x not in self.camouflages['modded'], self.interCamo)
        settings = self.loadJson('settings', {}, self.configPath)
        if 'disable' in settings:
            if not settings['disable']:
                del settings['disable']
            else:
                self.disable = settings['disable']
        for nation in settings.keys():
            if nation not in nations.NAMES + ('international',):
                continue
            camouflages = items.vehicles.g_cache.customization(nations.INDICES[nation])['camouflages']
            nationConf = settings[nation]
            camoNames = [camouflage['name'] for camouflage in camouflages.values()]
            for camoName in nationConf:
                if camoName not in camoNames:
                    del nationConf[camoName]
            for camoID, camouflage in camouflages.items():
                camoName = camouflage['name']
                if camoName not in nationConf:
                    continue
                camoInShop = not doShopCheck or g_customizationController.dataAggregator._elementIsInShop(
                    camoID, 0, nations.INDICES[nation])
                if nationConf[camoName].get('random_mode') == 2 or nationConf[camoName].get(
                        'random_mode') == 1 and camoName not in self.interCamo:
                    del nationConf[camoName]['random_mode']
                kinds = nationConf[camoName].get('kinds')
                if kinds is not None:
                    kindNames = filter(None, kinds.split(','))
                    if len(kindNames) == 1 and kindNames[0] == CAMOUFLAGE_KIND_INDICES[
                            camouflage['kind']] or camoInShop and doShopCheck:
                        del nationConf[camoName]['kinds']
                        if camoInShop:
                            print '%s: in-shop camouflage kind changing is disabled (name: %s)' % (self.ID, camoName)
                for team in ('Ally', 'Enemy'):
                    if nationConf[camoName].get('useFor%s' % team):
                        del nationConf[camoName]['useFor%s' % team]
                if not nationConf[camoName]:
                    del nationConf[camoName]
            if not nationConf:
                del settings[nation]
            else:
                self.camouflages[nation] = nationConf
        newSettings = {}
        if self.disable:
            newSettings['disable'] = self.disable
        for nation in settings:
            newSettings[nation] = settings[nation]
        self.loadJson('settings', newSettings, self.configPath, True)

    def do_config(self):
        super(_Config, self).do_config()
        BigWorld.g_modsListApi.addMod(
            id='CamoSelectorUI', name=self.i18n['UI_flash_header'],
            description=self.i18n['UI_flash_header_tooltip'],
            icon='gui/flash/CamoSelector.png',
            enabled=self.data['enabled'], login=False, lobby=True,
            callback=lambda: g_appLoader.getDefLobbyApp().loadView('CamoSelectorUI'))
        g_entitiesFactories.addSettings(
            ViewSettings('CamoSelectorUI', CamoSelectorUI, 'CamoSelector.swf', ViewTypes.WINDOW, None,
                         ScopeTemplates.GLOBAL_SCOPE, False))


# noinspection PyUnboundLocalVariable,PyUnboundLocalVariable
def new_vehicleValues(xmlCtx, section, sectionName, defNationID):
    section = section[sectionName]
    if section is None:
        return
    else:
        ctx = (xmlCtx, sectionName)
        for vehName, subsection in section.items():
            if 'all' not in vehName:
                if ':' not in vehName:
                    vehName = ':'.join((nations.NAMES[defNationID], vehName))
                try:
                    nationID, vehID = items.vehicles.g_list.getIDsByName(vehName)
                except StandardError:
                    _xml.raiseWrongXml(xmlCtx, sectionName, "unknown vehicle name '%s'" % vehName)

                yield items.vehicles.VehicleValue(vehName, items.makeIntCompactDescrByID('vehicle', nationID, vehID), ctx,
                                                  subsection)
            else:
                for vehNameAll in items.vehicles.g_list._VehicleList__ids.keys():
                    nationID, vehID = items.vehicles.g_list.getIDsByName(vehNameAll)
                    yield items.vehicles.VehicleValue(vehNameAll,
                                                      items.makeIntCompactDescrByID('vehicle', nationID, vehID),
                                                      ctx, subsection)


items.vehicles._vehicleValues = new_vehicleValues

_config = _Config()
_config.load()


def lobbyKeyControl(event):
    try:
        if event.isKeyDown() and not getattr(BigWorld, 'isMSAWPopulated', False):
            if PYmodsCore.checkKeys(_config.data['selectHotkey']):
                installSelectedCamo()
    except StandardError:
        traceback.print_exc()


def inj_hkKeyEvent(event):
    LobbyApp = g_appLoader.getDefLobbyApp()
    try:
        if LobbyApp and _config.data['enabled']:
            lobbyKeyControl(event)
    except StandardError:
        print 'CamoSelector: ERROR at inj_hkKeyEvent\n%s' % traceback.print_exc()


InputHandler.g_instance.onKeyDown += inj_hkKeyEvent
InputHandler.g_instance.onKeyUp += inj_hkKeyEvent


def new_customization(self, nationID):
    commonDescr = self._Cache__customization[nationID]
    if _config.data['enabled']:
        if commonDescr is None or not hasattr(self, 'changedNations') or nationID not in self.changedNations:
            self.changedNations = getattr(self, 'changedNations', [])
            self.changedNations.append(nationID)
            commonDescr = old_customization(self, nationID)
            for configDir in (dirName.replace(BigWorld.curCV + '/', '') for dirName in glob.iglob(_config.configPath + '*')
                              if os.path.isdir(dirName)):
                customDescr = items.vehicles._readCustomization(configDir + '/settings.xml', nationID, idsRange=(5001, 65535))
                if 'custom_camo' in commonDescr['camouflageGroups'] and 'custom_camo' in customDescr['camouflageGroups']:
                    del customDescr['camouflageGroups']['custom_camo']
                commonDescr = items.vehicles._joinCustomizationParams(nationID, commonDescr, customDescr)
            self._Cache__customization[nationID] = commonDescr
    return commonDescr


def new_elementIsInShop(self, criteria, cType, nationID):
    if cType == CUSTOMIZATION_TYPE.CAMOUFLAGE:
        customization = items.vehicles.g_cache.customization(nationID)
        if customization['camouflages'][criteria]['name'] in _config.camouflages['modded']:
            return False
    return old_elementIsInShop(self, criteria, cType, nationID)


def readInstalledCamouflages(self):
    if g_currentPreviewVehicle.isPresent():
        vDesc = g_currentPreviewVehicle.item.descriptor
    elif g_currentVehicle.isPresent():
        vDesc = g_currentVehicle.item.descriptor
    else:
        return
    nationName, vehName = vDesc.name.split(':')
    if _config.camouflagesCache.get(nationName, {}).get(vehName) is None:
        return
    for idx in xrange(3):
        self.showGroup(0, idx)
        if _config.camouflagesCache[nationName][vehName].get(CAMOUFLAGE_KIND_INDICES[idx]) is None:
            continue
        camoKindName = CAMOUFLAGE_KIND_INDICES[idx]
        camoName = _config.camouflagesCache[nationName][vehName][camoKindName]
        for itemIdx, item in enumerate(g_customizationController.carousel.items):
            if item['element']._rawData['name'] == camoName:
                self.installCustomizationElement(itemIdx)
                break
        else:
            SystemMessages.pushMessage('PYmods_SM' + _config.i18n['UI_customOrInvalid'].format(
                kind=_config.i18n['UI_customOrInvalid_%s' % CAMOUFLAGE_KIND_INDICES[idx]], name=camoName),
                                       SystemMessages.SM_TYPE.CustomizationForGold)
    g_customizationController._dataAggregator.start()
    try:
        self.backToSelectorGroup()
    except Exception as e:
        if False:
            print e


def installSelectedCamo():
    if g_currentPreviewVehicle.isPresent():
        vDesc = g_currentPreviewVehicle.item.descriptor
    elif g_currentVehicle.isPresent():
        vDesc = g_currentVehicle.item.descriptor
    else:
        return
    nationName, vehName = vDesc.name.split(':')
    nationID = vDesc.type.customizationNationID
    compDescr = vDesc.type.compactDescr
    assert nations.NAMES[nationID] == nationName, (nationName, nations.NAMES[nationID])
    if g_customizationController.slots.currentSlotsData is None:
        activeCamo = g_tankActiveCamouflage['historical'].get(vDesc.type.compactDescr)
        if activeCamo is None:
            activeCamo = g_tankActiveCamouflage.get(vDesc.type.compactDescr, 0)
        customization = items.vehicles.g_cache.customization(nationID)
        camoID = _config.hangarCamoCache[vDesc.type.compactDescr][activeCamo][0]
        if _config.activePreviewCamo is not None:
            camoNames = {camouflage['name']: camoID for camoID, camouflage in customization['camouflages'].items()}
            camoID = camoNames[_config.activePreviewCamo]
        camouflage = customization['camouflages'][camoID]
        camoName = camouflage['name']
        nationConf = _config.camouflages.get(nations.NAMES[nationID])
        interConf = _config.camouflages.get('international', {})
        camoKindNums = (camouflage['kind'],)
        if camoName in _config.camouflages['modded']:
            camoKindNames = filter(None, _config.camouflages['modded'].get(camoName, {}).get('kinds', '').split(','))
            camoKindNums = tuple(CAMOUFLAGE_KINDS[name] for name in camoKindNames)
        elif camoName in interConf:
            kindsStr = interConf.get(camoName, {}).get('kinds')
            if kindsStr is not None:
                camoKindNames = filter(None, kindsStr.split(','))
                camoKindNums = tuple(CAMOUFLAGE_KINDS[name] for name in camoKindNames)
        elif nationConf is not None:
            kindsStr = nationConf.get(camoName, {}).get('kinds')
            if kindsStr is not None:
                camoKindNames = filter(None, kindsStr.split(','))
                camoKindNums = tuple(CAMOUFLAGE_KINDS[name] for name in camoKindNames)
        for camoKindNum in camoKindNums:
            if _config.camouflagesCache.get(nationName, {}).get(vehName, {}).get(
                    CAMOUFLAGE_KIND_INDICES[camoKindNum]) == camoName:
                SystemMessages.pushMessage('PYmods_SM' + _config.i18n['UI_installCamouflage_already'].format(
                    name=camoName, kind=_config.i18n['UI_setting_hangarCamo_%s' % CAMOUFLAGE_KIND_INDICES[camoKindNum]]),
                                           SystemMessages.SM_TYPE.CustomizationForGold)
                continue
            _config.camouflagesCache.setdefault(nationName, {}).setdefault(vehName, {})[
                CAMOUFLAGE_KIND_INDICES[camoKindNum]] = camoName
            SystemMessages.pushMessage('PYmods_SM' + _config.i18n['UI_installCamouflage'].format(
                name=camoName, kind=_config.i18n['UI_setting_hangarCamo_%s' % CAMOUFLAGE_KIND_INDICES[camoKindNum]]),
                                       SystemMessages.SM_TYPE.CustomizationForGold)
            _config.loadJson('camouflagesCache', _config.camouflagesCache, _config.configPath, True)
        return
    camoCache = list(vDesc.camouflages)
    for item in g_customizationController.cart.items:
        if item['type'] != CUSTOMIZATION_TYPE.CAMOUFLAGE:
            continue
        camoKindNum = item['object']._rawData['kind']
        camoName = item['object']._rawData['name']
        _config.camouflagesCache.setdefault(nationName, {}).setdefault(vehName, {})[
            CAMOUFLAGE_KIND_INDICES[camoKindNum]] = camoName
        camoCache[camoKindNum] = (item['object'].getID(), int(time.time()), 7)
    selectedKinds = []
    for camoKind in _config.camouflagesCache.get(nationName, {}).get(vehName, {}):
        selectedKinds.append(CAMOUFLAGE_KINDS[camoKind])
    slotList = heapq.nsmallest(1, selectedKinds, key=lambda x: abs(x - g_customizationController.slots.currentSlotIdx))
    slotIdx = slotList[0] if slotList else 0
    g_tankActiveCamouflage[vDesc.type.compactDescr] = slotIdx
    vDesc.camouflages = tuple(camoCache)
    _config.hangarCamoCache[compDescr] = tuple(camoCache)
    if vehName in _config.camouflagesCache.get(nationName, {}) and not _config.camouflagesCache[nationName][vehName]:
        del _config.camouflagesCache[nationName][vehName]
    if nationName in _config.camouflagesCache and not _config.camouflagesCache[nationName]:
        del _config.camouflagesCache[nationName]
    _config.loadJson('camouflagesCache', _config.camouflagesCache, _config.configPath, True)
    g_currentPreviewVehicle.refreshModel()
    SystemMessages.pushMessage('PYmods_SM' + _config.i18n['UI_camouflageSelect'],
                               SystemMessages.SM_TYPE.CustomizationForGold)


def new_removeSlot(self, cType, slotIdx):
    if cType == CUSTOMIZATION_TYPE.CAMOUFLAGE:
        if g_currentPreviewVehicle.isPresent():
            vDesc = g_currentPreviewVehicle.item.descriptor
        else:
            vDesc = g_currentVehicle.item.getCustomizedDescriptor()
        nationName, vehName = vDesc.name.split(':')
        item = g_customizationController.cart.items[slotIdx]
        camoKind = CAMOUFLAGE_KIND_INDICES[slotIdx]
        camoName = item['object']._rawData['name']
        if _config.camouflagesCache.get(nationName, {}).get(vehName) is not None:
            vehDict = _config.camouflagesCache[nationName][vehName]
            if vehDict.get(camoKind) is not None and vehDict[camoKind] == camoName:
                del vehDict[camoKind]
            _config.loadJson('camouflagesCache', _config.camouflagesCache, _config.configPath, True)
    old_removeSlot(self, cType, slotIdx)


def new_subViewTransferStop(self, alias):
    if alias == VIEW_ALIAS.LOBBY_CUSTOMIZATION:
        BigWorld.callback(0.0, g_customizationController.events.onCartFilled)
    old_subViewTransferStop(self, alias)


def new_MV_populate(self):
    old_MV_populate(self)
    if _config.data['enabled']:
        readInstalledCamouflages(self)


def updateGUIState():
    if _config.UIProxy is None:
        return
    nationID = CamoSelectorUI.getCurrentNation()
    if nationID is not None and _config.backupNationID != nationID:
        _config.UIProxy.changeNation(nationID)


def new_selectVehicle(self, vehInvID=0):
    old_selectVehicle(self, vehInvID)
    updateGUIState()


def new_selectPreviewVehicle(self, vehicleCD):
    old_selectPreviewVehicle(self, vehicleCD)
    updateGUIState()


old_selectVehicle = CurrentVehicle._CurrentVehicle.selectVehicle
CurrentVehicle._CurrentVehicle.selectVehicle = new_selectVehicle
old_selectPreviewVehicle = CurrentVehicle._CurrentPreviewVehicle.selectVehicle
CurrentVehicle._CurrentPreviewVehicle.selectVehicle = new_selectPreviewVehicle
old_removeSlot = MainView.removeSlot
MainView.removeSlot = new_removeSlot
old_subViewTransferStop = LobbyView._LobbyView__subViewTransferStop
LobbyView._LobbyView__subViewTransferStop = new_subViewTransferStop
old_MV_populate = MainView._populate
MainView._populate = new_MV_populate
old_elementIsInShop = DataAggregator._elementIsInShop
DataAggregator._elementIsInShop = new_elementIsInShop
old_customization = items.vehicles.Cache.customization
items.vehicles.Cache.customization = new_customization


def new_onBecomeNonPlayer(self):
    old_onBecomeNonPlayer(self)
    _config.hangarCamoCache.clear()
    _config.currentOverriders = dict.fromkeys(('Ally', 'Enemy'))


def new_ca_getCamouflageParams(self, vDesc, vID):
    result = old_ca_getCamouflageParams(self, vDesc, vID)
    if not _config.data['enabled'] or result[0] is not None and _config.data['useBought']:
        return result
    if 'modded' not in _config.camouflages:
        _config.readCamouflages(False)
    if vDesc.name in _config.disable:
        return result
    nationName, vehName = vDesc.name.split(':')
    isPlayer = vID == BigWorld.player().playerVehicleID
    isAlly = BigWorld.player().arena.vehicles[vID]['team'] == BigWorld.player().team
    curTeam = 'Ally' if isAlly else 'Enemy'
    otherTeam = 'Ally' if not isAlly else 'Enemy'
    camoKind = BigWorld.player().arena.arenaType.vehicleCamouflageKind
    camoKindName = CAMOUFLAGE_KIND_INDICES[camoKind]
    nationID = vDesc.type.customizationNationID
    camouflages = items.vehicles.g_cache.customization(nationID)['camouflages']
    camoNames = {camouflage['name']: id for id, camouflage in camouflages.items()}
    if isPlayer and _config.camouflagesCache.get(nationName, {}).get(vehName, {}).get(camoKindName) is not None:
        for camoName in camoNames:
            if camoName == _config.camouflagesCache[nationName][vehName][camoKindName]:
                return camoNames[camoName], int(time.time()), 7
    selectedCamouflages = []
    overriders = []
    for key in ('modded', 'international', nationName):
        for camoName in _config.camouflages.get(key, {}):
            if camoName not in camoNames:
                continue
            camoConfig = _config.camouflages[key][camoName]
            camouflage = camouflages[camoNames[camoName]]
            if camoConfig.get('random_mode', 2) != 1:
                continue
            if camoKindName not in camoConfig.get('kinds', CAMOUFLAGE_KIND_INDICES[camouflage['kind']]):
                continue
            if not camoConfig.get('useFor%s' % curTeam, True):
                continue
            if camouflage['allow'] and vDesc.type.compactDescr not in camouflage['allow'] or \
                    vDesc.type.compactDescr in camouflage['deny']:
                continue
            if vDesc.type.compactDescr in camouflage['tiling']:
                overriders.append(camoNames[camoName])
            else:
                print 'CamoSelector: a vehicle was not whitelisted and (or) blacklisted, but is missing:', vehName
                print camouflage['tiling']
    if overriders:
        if _config.currentOverriders[curTeam] is None:
            otherOverrider = _config.currentOverriders[otherTeam]
            if len(overriders) > 1 and otherOverrider in overriders:
                overriders.remove(otherOverrider)
            _config.currentOverriders[curTeam] = overriders[vID % len(overriders)]
        selectedCamouflages = [_config.currentOverriders[curTeam]]
    if _config.data['doRandom'] and not selectedCamouflages:
        for camoID, camouflage in camouflages.items():
            camoName = camouflage['name']
            checked = {'modded': False, 'international': False, nationName: False}
            for key in checked:
                if camoName not in _config.camouflages.get(key, {}):
                    continue
                checked[key] = True
                camoConfig = _config.camouflages[key][camoName]
                if camoConfig.get('random_mode', 2) != 2:
                    continue
                if not camoConfig.get('useFor%s' % curTeam, True):
                    continue
                if camouflage['allow'] and vDesc.type.compactDescr not in camouflage['allow'] or \
                        vDesc.type.compactDescr in camouflage['deny']:
                    continue
                if vDesc.type.compactDescr not in camouflage['tiling']:
                    continue
                if camoKindName not in camoConfig.get('kinds', CAMOUFLAGE_KIND_INDICES[camouflage['kind']]):
                    continue
                selectedCamouflages.append(camoID)
            if not any(checked.values()):
                if camouflage['kind'] == CAMOUFLAGE_KINDS[camoKindName]:
                    selectedCamouflages.append(camoID)
    if not selectedCamouflages:
        selectedCamouflages.append(None)
    camouflageId = vID % len(selectedCamouflages)
    return selectedCamouflages[camouflageId], int(time.time()), 7


old_onBecomeNonPlayer = Account.onBecomeNonPlayer
Account.onBecomeNonPlayer = new_onBecomeNonPlayer
old_ca_getCamouflageParams = CompoundAppearance._CompoundAppearance__getCamouflageParams
CompoundAppearance._CompoundAppearance__getCamouflageParams = new_ca_getCamouflageParams


def new_cs_recreateVehicle(self, vDesc, vState, onVehicleLoadedCallback=None):
    if _config.data['enabled']:
        if 'modded' not in _config.camouflages:
            _config.readCamouflages(True)
        nationID = vDesc.type.customizationNationID
        customization = items.vehicles.g_cache.customization(nationID)
        if _config.activePreviewCamo is not None:
            for camoID, camouflage in customization['camouflages'].items():
                if camouflage['name'] == _config.activePreviewCamo:
                    vDesc.camouflages = tuple((camoID, time.time(), 7) for _ in xrange(3))
                    break
            else:
                SystemMessages.pushMessage('PYmods_SM' + _config.i18n['UI_camouflagePreviewError'] +
                                           _config.activePreviewCamo.join(('<b>', '</b>')),
                                           SystemMessages.SM_TYPE.CustomizationForGold)
                print 'CamoSelector: camouflage not found for nation %s: %s' % (nationID, _config.activePreviewCamo)
                _config.activePreviewCamo = None
        elif vDesc.type.compactDescr in _config.hangarCamoCache:
            vDesc.camouflages = _config.hangarCamoCache[vDesc.type.compactDescr]
        elif vDesc.name not in _config.disable:
            nationName, vehName = vDesc.name.split(':')
            selectedForVeh = _config.camouflagesCache.get(nationName, {}).get(vehName, {})
            selectedCamo = {}
            camoByKind = {0: [], 1: [], 2: []}
            for camoID, camouflage in customization['camouflages'].items():
                camoName = camouflage['name']
                nationConf = _config.camouflages.get(nationName)
                interConf = _config.camouflages.get('international', {})
                camoKindNames = (CAMOUFLAGE_KIND_INDICES[camouflage['kind']],)
                if camoName in _config.camouflages['modded']:
                    camoKindNames = filter(None, _config.camouflages['modded'].get(camoName, {}).get('kinds', '').split(','))
                elif camoName in interConf:
                    kindsStr = interConf.get(camoName, {}).get('kinds')
                    if kindsStr is not None:
                        camoKindNames = filter(None, kindsStr.split(','))
                elif nationConf is not None:
                    kindsStr = nationConf.get(camoName, {}).get('kinds')
                    if kindsStr is not None:
                        camoKindNames = filter(None, kindsStr.split(','))
                for camoKindName in camoKindNames:
                    if selectedForVeh.get(camoKindName) is not None:
                        if camouflage['name'] == selectedForVeh[camoKindName]:
                            selectedCamo[CAMOUFLAGE_KINDS[camoKindName]] = camoID
                    camoByKind[CAMOUFLAGE_KINDS[camoKindName]].append(camoID)
            for kind in camoByKind:
                if not camoByKind[kind]:
                    camoByKind[kind].append(None)
            tmpCamouflages = []
            for idx in xrange(3):
                if vDesc.camouflages[idx][0] is not None:
                    tmpCamouflages.append(vDesc.camouflages[idx])
                elif selectedCamo.get(idx) is not None:
                    tmpCamouflages.append((selectedCamo[idx], int(time.time()), 7))
                else:
                    tmpCamouflages.append((random.choice(camoByKind[idx]), int(time.time()), 7))
            vDesc.camouflages = tuple(tmpCamouflages)
            _config.hangarCamoCache[vDesc.type.compactDescr] = tuple(tmpCamouflages)
            if _config.data['hangarCamoKind'] < 3:
                idx = _config.data['hangarCamoKind']
            else:
                idx = random.randrange(3)
            g_tankActiveCamouflage[vDesc.type.compactDescr] = idx
    old_cs_recreateVehicle(self, vDesc, vState, onVehicleLoadedCallback)


old_cs_recreateVehicle = ClientHangarSpace.recreateVehicle
ClientHangarSpace.recreateVehicle = new_cs_recreateVehicle


class Analytics(PYmodsCore.Analytics):
    def __init__(self):
        super(Analytics, self).__init__()
        self.mod_description = _config.ID
        self.mod_version = _config.version.split(' ', 1)[0]
        self.mod_id_analytics = 'UA-76792179-7'


statistic_mod = Analytics()


def fini():
    try:
        statistic_mod.end()
    except StandardError:
        traceback.print_exc()


def new_LW_populate(self):
    old_LW_populate(self)
    try:
        statistic_mod.start()
    except StandardError:
        traceback.print_exc()


old_LW_populate = LobbyView._populate
LobbyView._populate = new_LW_populate
