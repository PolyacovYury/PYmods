# -*- coding: utf-8 -*-
import time
import traceback

import ResMgr

import BigWorld
import Keys
import PYmodsCore
from Avatar import PlayerAvatar
from gui import InputHandler, SystemMessages
from gui.Scaleform.daapi.view.lobby.LobbyView import LobbyView
from gui.app_loader.loader import g_appLoader

res = ResMgr.openSection('../paths.xml')
sb = res['Paths']
vl = sb.values()[0]
if vl is not None and not hasattr(BigWorld, 'curCV'):
    BigWorld.curCV = vl.asString


class _Config(PYmodsCore._Config):
    def __init__(self):
        super(_Config, self).__init__('%(mod_ID)s')
        self.version = '2.2.1 (%(file_compile_date)s)'
        self.author = '%s (orig by Lp()rtii/Dellux) (thx to LSD_MAX/Delysid :P)' % self.author
        self.defaultKeys = {'hotkey': [Keys.KEY_F12], 'hotKey': ['KEY_F12']}
        self.data = {'enabled': True,
                     'time': 0,
                     'enableAtStartup': True,
                     'hotkey': self.defaultKeys['hotkey'],
                     'hotKey': self.defaultKeys['hotKey'],
                     'enableMessage': True}
        self.i18n = {
            'UI_description': 'Sun Controller',
            'UI_activSunMod': 'SunController ENABLED',
            'UI_deactivSunMod': 'SunController DISABLED',
            'UI_setting_time_text': 'Time set by Controller',
            'UI_setting_time_tooltip': (
                'This time of day will be applied to all battle maps.\n'
                ' • 0:00 - old behaviour.\n • 24:00 - current local time.'),
            'UI_setting_enableAtStartup_text': 'Sun is controlled by default',
            'UI_setting_enableAtStartup_tooltip': 'Sun position will be changed automatically after battle begins.',
            'UI_setting_hotkey_text': 'SunController hotkey',
            'UI_setting_hotkey_tooltip': 'Pressing this button in-battle toggles sun control on/off.',
            'UI_setting_enableMessage_text': 'Enable service channel message',
            'UI_setting_enableMessage_tooltip': (
                'This allows the mod to send a notification to service channel in no-GUI mode.'),
            'UI_serviceChannelPopUpAll': '<b>{author}<font color="#cc9933"> turned the Earth!</font></b>',
            'UI_serviceChannelPopUpAnd': '<b><font color="#cc9933">And turned the Earth!</font></b>'}
        self.loadLang()

    def template_settings(self):
        return {'modDisplayName': self.i18n['UI_description'],
                'settingsVersion': 200,
                'enabled': self.data['enabled'],
                'column1': [self.createSlider('time', 0, 24, 1, '{{value}}:00'),
                            self.createControl('enableMessage')],
                'column2': [self.createHotKey('hotkey'),
                            self.createControl('enableAtStartup')]}

    def apply_settings(self, settings):
        global isSunControlled
        super(_Config, self).apply_settings(settings)
        isSunControlled = _config.data['enableAtStartup']


_config = _Config()
_config.load()
if _config.data['enableMessage']:
    isLogin = True

    def new_populate(self):
        LOGIN_TEXT_MESSAGE = _config.i18n['UI_serviceChannelPopUpAll'].format(
            author='<font color="#DD7700">Polyacov_Yury</font>')
        try:
            # noinspection PyUnresolvedReferences
            from gui.vxSettingsApi import vxSettingsApi
            isRegistered = vxSettingsApi.isRegistered('PYmodsGUI')
        except ImportError:
            isRegistered = False
        try:
            from gui.mods import mod_lamplights
            if not isRegistered and mod_lamplights._config.data['enableMessage']:
                LOGIN_TEXT_MESSAGE = _config.i18n['UI_serviceChannelPopUpAnd']
        except StandardError:
            pass
        global isLogin
        old_populate(self)
        if isLogin and not isRegistered:
            SystemMessages.pushMessage(LOGIN_TEXT_MESSAGE, type=SystemMessages.SM_TYPE.Information)
            isLogin = False

    old_populate = LobbyView._populate
    LobbyView._populate = new_populate
isSunControlled = _config.data['enableAtStartup']
wasSunControlled = False
timeBackup = '12:00'


def sun_controller(isControlled=True):
    global timeBackup
    global wasSunControlled
    if isControlled:
        timeBackup = BigWorld.timeOfDay('GetTime')
        if _config.data['time'] != 24:
            BigWorld.timeOfDay('%s:0' % _config.data['time'])
        else:
            BigWorld.timeOfDay(time.strftime('%H:%M'))
            _config.sunCallback = BigWorld.callback(60.0, sun_controller)
        wasSunControlled = True
    elif wasSunControlled:
        BigWorld.timeOfDay(timeBackup)
        try:
            _config.sunCallback = BigWorld.cancelCallback(getattr(_config, 'sunCallback', None))
        except StandardError:
            pass


old_startGUI = PlayerAvatar._PlayerAvatar__startGUI


def new_startGUI(self):
    old_startGUI(self)
    temp_t = BigWorld.time()

    def _clear_loop():
        global wasSunControlled
        if BigWorld.time() - temp_t < 5:
            BigWorld.callback(0.2, _clear_loop)
        else:
            wasSunControlled = False
            sun_controller(isSunControlled)

    if _config.data['enabled']:
        _clear_loop()


PlayerAvatar._PlayerAvatar__startGUI = new_startGUI


def battleKeyControl(event):
    global isSunControlled
    try:
        if PYmodsCore.checkKeys(_config.data['hotkey']) and event.isKeyDown():
            isSunControlled = not isSunControlled
            sun_controller(isSunControlled)
            if isSunControlled:
                PYmodsCore.sendMessage(_config.i18n['UI_activSunMod'])
            else:
                PYmodsCore.sendMessage(_config.i18n['UI_deactivSunMod'], 'Red')
    except StandardError:
        traceback.print_exc()


def inj_hkKeyEvent(event):
    BattleApp = g_appLoader.getDefBattleApp()
    try:
        if BattleApp and _config.data['enabled']:
            battleKeyControl(event)
    except StandardError:
        print '%s: ERROR at inj_hkKeyEvent\n%s' % (_config.ID, traceback.print_exc())


InputHandler.g_instance.onKeyDown += inj_hkKeyEvent
InputHandler.g_instance.onKeyUp += inj_hkKeyEvent
statistic_mod = PYmodsCore.Analytics(_config.ID, _config.version.split(' ', 1)[0], 'UA-76792179-3')
