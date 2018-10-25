# -*- coding: utf-8 -*-
import BigWorld
import Keys
import ResMgr
import traceback
from PYmodsCore import PYmodsConfigInterface, refreshCurrentVehicle, checkKeys, loadJson, remDups
from gui import InputHandler, SystemMessages
from gui.Scaleform.framework import ScopeTemplates, ViewSettings, ViewTypes, g_entitiesFactories
from gui.Scaleform.framework.entities.abstract.AbstractWindowView import AbstractWindowView
from gui.Scaleform.framework.managers.loaders import SFViewLoadParams
from gui.app_loader import g_appLoader
from helpers import dependency
from skeletons.gui.shared.utils import IHangarSpace
from . import __date__, __modID__


class ConfigInterface(PYmodsConfigInterface):
    hangarSpace = dependency.descriptor(IHangarSpace)

    def __init__(self):
        self.possibleModes = ['player', 'ally', 'enemy']
        self.defaultSkinConfig = {'static': {'enabled': True, 'swapPlayer': True, 'swapAlly': True, 'swapEnemy': True},
                                  'dynamic': {'enabled': True, 'swapPlayer': False, 'swapAlly': True, 'swapEnemy': True}}
        self.settings = {'skins': {}, 'skins_dynamic': {}}
        self.skinsCache = {'CRC32': '', 'version': ''}
        self.skinsData = {
            'enabled': True, 'found': False, 'models': {'static': {}, 'dynamic': {}},
            'priorities': {skinType: {'player': [], 'ally': [], 'enemy': []} for skinType in ('static', 'dynamic')}}
        self.loadingProxy = None
        self.isModAdded = False
        self.collisionEnabled = False
        self.collisionComparisonEnabled = False
        self.dynamicSkinEnabled = False
        self.currentMode = self.possibleModes[0]
        super(ConfigInterface, self).__init__()

    def init(self):
        self.ID = __modID__
        self.version = '1.0.0 (%s)' % __date__
        self.defaultKeys = {'DynamicSkinHotkey': [Keys.KEY_F1, [Keys.KEY_LCONTROL, Keys.KEY_RCONTROL]],
                            'ChangeViewHotkey': [Keys.KEY_F2, [Keys.KEY_LCONTROL, Keys.KEY_RCONTROL]]}
        self.data = {'enabled': True,
                     'isDebug': True,
                     'DynamicSkinHotkey': self.defaultKeys['DynamicSkinHotkey'],
                     'ChangeViewHotkey': self.defaultKeys['ChangeViewHotkey']}
        self.i18n = {
            'UI_description': 'Skinner',
            'UI_flash_header': 'Skins setup',
            'UI_flash_header_tooltip': "Setup for Skinner by "
                                       "<font color='#DD7700'><b>Polyacov_Yury</b></font>",
            'UI_flash_skinSetup': 'Skin setup',
            'UI_flash_skinPriority': 'Skin priorities',
            'UI_flash_skinSetupBtn': 'Setup',
            'UI_flash_skinPriorityBtn': 'Priorities',
            'UI_flash_skinType_static': 'Static',
            'UI_flash_skinType_dynamic': 'Dynamic',
            'UI_flash_team_player': 'Player',
            'UI_flash_team_ally': 'Ally',
            'UI_flash_team_enemy': 'Enemy',
            'UI_flash_useFor_header_text': 'Use this item for:',
            'UI_flash_useFor_player_text': 'Player',
            'UI_flash_useFor_ally_text': 'Allies',
            'UI_flash_useFor_enemy_text': 'Enemies',
            'UI_flash_WLVehDelete_header': 'Confirmation',
            'UI_flash_WLVehDelete_text': 'Are you sure you want to delete this vehicle from this whitelist?',
            'UI_flash_vehicleDelete_success': 'Vehicle deleted from whitelist: ',
            'UI_flash_vehicleAdd_success': 'Vehicle added to whitelist: ',
            'UI_flash_vehicleAdd_dupe': 'Vehicle already in whitelist: ',
            'UI_flash_saveBtn': 'Save',
            'UI_loading_autoLogin': 'Log in afterwards',
            'UI_loading_autoLogin_cancel': 'Cancel auto login',
            'UI_loading_done': ' Done!',
            'UI_loading_header_CRC32': 'Skinner: checking textures',
            'UI_loading_header_models_clean': 'Skinner: cleaning models',
            'UI_loading_header_models_unpack': 'Skinner: unpacking models',
            'UI_loading_package': 'Unpacking %s:',
            'UI_loading_skinPack': 'Checking %s:',
            'UI_loading_skinPack_clean': 'Cleaning %s:',
            'UI_loading_skins': 'Checking skins...',
            'UI_loading_skins_clean': 'Cleaning skin models...',
            'UI_restart_header': 'Skinner: restart',
            'UI_restart_text': (
                'Skin models have been re-unpacked. Client restart required to accept changes.\n'
                'Client proper behaviour <b>NOT GUARANTEED</b> until next client start. This will <b>not</b>'
                'be required later. Do you want to restart the game now?'),
            'UI_restart_button_restart': 'Restart',
            'UI_restart_button_shutdown': 'Shutdown',
            'UI_setting_isDebug_text': 'Enable extended log printing',
            'UI_setting_isDebug_tooltip': 'If enabled, your python.log will be harassed with mod\'s debug information.',
            'UI_setting_ChangeViewHotkey_text': 'View mode switch hotkey',
            'UI_setting_ChangeViewHotkey_tooltip': (
                'This hotkey will switch the preview mode in hangar.\n<b>Possible modes:</b>\n'
                ' • Player tank\n • Ally tank\n • Enemy tank'),
            'UI_setting_DynamicSkinHotkey_text': 'Dynamic skin display switch hotkey',
            'UI_setting_DynamicSkinHotkey_tooltip': (
                'This hotkey will switch dynamic skin preview mode in hangar.\n'
                '<b>Possible modes:</b>\n • OFF\n • Model add'),
            'UI_enableDynamicSkin': '<b>Skinner:</b>\nEnabling dynamic skins display.',
            'UI_disableDynamicSkin': '<b>Skinner:</b>\nDisabling dynamic skins display.',
            'UI_install_skin': '<b>Skinner:</b>\nSkin installed: ',
            'UI_install_skin_dynamic': '<b>Skinner:</b>\nDynamic skin installed: ',
            'UI_install_default': '<b>Skinner:</b>\nDefault model applied.',
            'UI_mode': '<b>Skinner:</b>\nCurrent display mode: ',
            'UI_mode_player': 'player tank preview',
            'UI_mode_ally': 'ally tank preview',
            'UI_mode_enemy': 'enemy tank preview'}
        super(ConfigInterface, self).init()

    def createTemplate(self):
        template = {'modDisplayName': self.i18n['UI_description'],
                    'settingsVersion': 200,
                    'enabled': self.data['enabled'],
                    'column1': [self.tb.createControl('isDebug')],
                    'column2': [self.tb.createHotKey('DynamicSkinHotkey'),
                                self.tb.createHotKey('ChangeViewHotkey')]}
        return template

    def onMSADestroy(self):
        refreshCurrentVehicle()

    def onApplySettings(self, settings):
        super(ConfigInterface, self).onApplySettings(settings)
        if self.isModAdded:
            kwargs = dict(id='SkinnerUI', enabled=self.data['enabled'])
            try:
                BigWorld.g_modsListApi.updateModification(**kwargs)
            except AttributeError:
                BigWorld.g_modsListApi.updateMod(**kwargs)

    def readCurrentSettings(self, quiet=True):
        super(ConfigInterface, self).readCurrentSettings()
        self.settings = loadJson(self.ID, 'settings', self.settings, self.configPath)
        self.skinsCache.update(loadJson(self.ID, 'skinsCache', self.skinsCache, self.configPath))
        self.skinsData['enabled'] = ResMgr.openSection('vehicles/skins/') is not None and ResMgr.isDir('vehicles/skins/')
        if self.skinsData['enabled']:
            self.skinsData['priorities'] = loadJson(self.ID, 'skinsPriority', self.skinsData['priorities'], self.configPath)
            skinDir = 'vehicles/skins/textures/'
            for skinTypeSuff in ('', '_dynamic'):
                skinType = 'static' if not skinTypeSuff else skinTypeSuff[1:]
                for key in self.skinsData['priorities'][skinType].keys():
                    if not key.islower():
                        self.skinsData['priorities'][skinType][key.lower()] = self.skinsData['priorities'][skinType].pop(key)
                skinsSettings = self.settings['skins' + skinTypeSuff]
                disabledSkins = []
                if self.data['isDebug']:
                    print self.ID + ': loading configs for', skinType, 'skins'
                skinDirSect = ResMgr.openSection(skinDir)
                for sname in [] if skinDirSect is None else remDups(skinDirSect.keys()):
                    confDict = skinsSettings.setdefault(sname, self.defaultSkinConfig[skinType])
                    if not confDict.get('enabled', True):
                        print self.ID + ':', sname, 'disabled, moving on'
                        disabledSkins.append(sname)
                        continue
                    self.skinsData['models'][skinType][sname] = pRecord = {'name': '', 'whitelist': set()}
                    pRecord['name'] = sname
                    priorities = self.skinsData['priorities'][skinType]
                    for tankType in priorities:
                        key = 'swap' + tankType.capitalize()
                        if not confDict.setdefault(key, self.defaultSkinConfig[skinType][key]):
                            if self.data['isDebug']:
                                print self.ID + ':', tankType, 'swapping in', sname, 'disabled.'
                            if sname in priorities[tankType]:
                                priorities[tankType].remove(sname)
                            continue
                        if sname not in priorities[tankType]:
                            priorities[tankType].append(sname)
                    pRecord['whitelist'].clear()
                    vehiclesDirPath = skinDir + sname + '/vehicles/'
                    vehiclesDirSect = ResMgr.openSection(vehiclesDirPath)
                    for curNation in [] if vehiclesDirSect is None else remDups(vehiclesDirSect.keys()):
                        nationDirPath = vehiclesDirPath + curNation + '/'
                        nationDirSect = ResMgr.openSection(nationDirPath)
                        for vehicleName in [] if nationDirSect is None else remDups(nationDirSect.keys()):
                            vehDirPath = nationDirPath + vehicleName + '/'
                            vehDirSect = ResMgr.openSection(vehDirPath)
                            tracksDirPath = vehDirPath + 'tracks/'
                            tracksDirSect = ResMgr.openSection(tracksDirPath)
                            if not any(texName.endswith('.dds') for texName in (
                                    ([] if vehDirSect is None else remDups(vehDirSect.keys())) +
                                    ([] if tracksDirSect is None else remDups(tracksDirSect.keys())))):
                                if self.data['isDebug']:
                                    print self.ID + ':', vehicleName, 'folder from', sname, 'pack is empty.'
                            else:
                                pRecord['whitelist'].add(vehicleName)

                    if self.data['isDebug']:
                        print self.ID + ': config for', sname, 'loaded.'
                snameList = self.skinsData['models'][skinType].keys() + disabledSkins
                for sname in skinsSettings.keys():
                    if sname not in snameList:
                        del skinsSettings[sname]
            if not any(self.skinsData['models'].values()):
                if not quiet:
                    print self.ID + ': no skin pack configs found, skin module standing down.'
                self.skinsData['enabled'] = False
                for skinType in self.skinsData['priorities']:
                    for key in self.skinsData['priorities'][skinType]:
                        self.skinsData['priorities'][skinType][key] = []
            else:
                for skinType in self.skinsData['priorities']:
                    for key in self.skinsData['priorities'][skinType]:
                        for sname in self.skinsData['priorities'][skinType][key]:
                            if sname not in self.skinsData['models'][skinType]:
                                self.skinsData['priorities'][skinType][key].remove(sname)
        else:
            if not quiet:
                print self.ID + ': no skin packs found, skin module standing down.'
            for skinType in self.skinsData['priorities']:
                for key in self.skinsData['priorities'][skinType]:
                    self.skinsData['priorities'][skinType][key] = []
        loadJson(self.ID, 'skinsPriority', self.skinsData['priorities'], self.configPath, True, quiet=quiet)
        loadJson(self.ID, 'settings', self.settings, self.configPath, True, quiet=quiet)

    def registerSettings(self):
        super(ConfigInterface, self).registerSettings()
        if not hasattr(BigWorld, 'g_modsListApi'):
            return
        # noinspection PyArgumentList
        g_entitiesFactories.addSettings(
            ViewSettings('SkinnerUI', SkinnerUI, 'Skinner.swf', ViewTypes.WINDOW, None,
                         ScopeTemplates.GLOBAL_SCOPE, False))
        kwargs = dict(
            id='SkinnerUI', name=self.i18n['UI_flash_header'], description=self.i18n['UI_flash_header_tooltip'],
            icon='gui/flash/Skinner.png', enabled=self.data['enabled'] and self.skinsData['enabled'], login=True, lobby=True,
            callback=lambda:
                g_appLoader.getDefLobbyApp().containerManager.getContainer(ViewTypes.TOP_WINDOW).getViewCount()
                or g_appLoader.getDefLobbyApp().loadView(SFViewLoadParams('SkinnerUI')))
        try:
            BigWorld.g_modsListApi.addModification(**kwargs)
        except AttributeError:
            BigWorld.g_modsListApi.addMod(**kwargs)
        self.isModAdded = True


class SkinnerUI(AbstractWindowView):
    def py_onRequestSettings(self):
        g_config.readCurrentSettings(not g_config.data['isDebug'])
        texts = {
            'header': {
                'skinSetup': g_config.i18n['UI_flash_skinSetup'],
                'priorities': g_config.i18n['UI_flash_skinPriority']},
            'skinsSetupBtn': g_config.i18n['UI_flash_skinSetupBtn'],
            'skinsPriorityBtn': g_config.i18n['UI_flash_skinPriorityBtn'],
            'skinTypes': [g_config.i18n['UI_flash_skinType_' + skinType] for skinType in ('static', 'dynamic')],
            'teams': [g_config.i18n['UI_flash_team_' + team] for team in ('player', 'ally', 'enemy')],
            'skinNames': [[], []],
            'useFor': {'header': g_config.tb.createLabel('useFor_header', 'flash'),
                       'ally': g_config.tb.createLabel('useFor_ally', 'flash'),
                       'enemy': g_config.tb.createLabel('useFor_enemy', 'flash'),
                       'player': g_config.tb.createLabel('useFor_player', 'flash')},
            'saveBtn': g_config.i18n['UI_flash_saveBtn']
        }
        settings = {
            'skins': [[], []],
            'priorities': [[g_config.skinsData['priorities'][sType][team] for team in ('player', 'ally', 'enemy')] for
                           sType in ('static', 'dynamic')]
        }
        for idx, skinType in enumerate(('', '_dynamic')):
            skins = g_config.settings['skins' + skinType]
            for sname in sorted(g_config.skinsData['models']['static' if not skinType else 'dynamic']):
                sDesc = skins[sname]
                texts['skinNames'][idx].append(sname)
                settings['skins'][idx].append(
                    {'useFor': {k: sDesc['swap' + k.capitalize()] for k in ('player', 'ally', 'enemy')}})
        self.flashObject.as_updateData(texts, settings)

    @staticmethod
    def py_getCurrentVehicleName():
        vDesc = g_config.hangarSpace.space.getVehicleEntity().appearance._HangarVehicleAppearance__vDesc
        return vDesc.name.split(':')[1].lower()

    @staticmethod
    def py_onSaveSettings(settings):
        for idx, settingsArray in enumerate(settings.skins):
            for nameIdx, setObj in enumerate(settingsArray):
                for key in ('player', 'ally', 'enemy'):
                    g_config.settings['skins' + ('', '_dynamic')[idx]][
                        sorted(g_config.skinsData['models'][('static', 'dynamic')[idx]])[nameIdx]][
                        'swap' + key.capitalize()] = getattr(setObj.useFor, key)
        for idx, prioritiesArray in enumerate(settings.priorities):
            for teamIdx, team in enumerate(('player', 'ally', 'enemy')):
                g_config.skinsData['priorities'][('static', 'dynamic')[idx]][team] = prioritiesArray[teamIdx]
        loadJson(g_config.ID, 'skinsPriority', g_config.skinsData['priorities'], g_config.configPath, True,
                 quiet=not g_config.data['isDebug'])
        loadJson(g_config.ID, 'settings', g_config.settings, g_config.configPath, True, quiet=not g_config.data['isDebug'])
        g_config.readCurrentSettings(not g_config.data['isDebug'])
        refreshCurrentVehicle()

    @staticmethod
    def py_sendMessage(xmlName, action, status):
        SystemMessages.pushMessage(
            'temp_SM%s<b>%s</b>.' % (g_config.i18n['UI_flash_vehicle%s_%s' % (action, status)], xmlName),
            SystemMessages.SM_TYPE.CustomizationForGold)

    def onWindowClose(self):
        self.destroy()

    @staticmethod
    def py_printLog(*args):
        for arg in args:
            print arg


def lobbyKeyControl(event):
    if not event.isKeyDown() or g_config.isMSAWindowOpen or not g_config.skinsData['enabled']:
        return
    if checkKeys(g_config.data['ChangeViewHotkey']):
        try:
            from gui.mods.mod_remodenabler import g_config as re_config
        except ImportError:
            re_config = None
        if re_config is None:
            newModeNum = (g_config.possibleModes.index(g_config.currentMode) + 1) % len(g_config.possibleModes)
            g_config.currentMode = g_config.possibleModes[newModeNum]
        elif re_config.currentMode != 'remod':
            g_config.currentMode = re_config.currentMode
        if g_config.data['isDebug']:
            print g_config.ID + ': changing display mode to', g_config.currentMode
        if re_config is None:
            SystemMessages.pushMessage(
                'temp_SM%s<b>%s</b>' % (g_config.i18n['UI_mode'], g_config.i18n['UI_mode_' + g_config.currentMode]),
                SystemMessages.SM_TYPE.Warning)
        refreshCurrentVehicle()
    if checkKeys(g_config.data['DynamicSkinHotkey']):
        enabled = g_config.dynamicSkinEnabled
        g_config.dynamicSkinEnabled = not enabled
        SystemMessages.pushMessage(
            'temp_SM' + g_config.i18n['UI_%sableDynamicSkin' % ('en' if not enabled else 'dis')],
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
