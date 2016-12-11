# -*- coding: utf-8 -*-
import os
import time
import traceback

import BigWorld
import Keys
import ResMgr

from Avatar import PlayerAvatar
from gui import InputHandler, SystemMessages
from gui.Scaleform.daapi.view.lobby.LobbyView import LobbyView
from gui.app_loader.loader import g_appLoader
from gui.mods import PYmodsCore

try:
    from gui.mods import mod_PYmodsGUI
except ImportError:
    mod_PYmodsGUI = None
    print 'SunController: no-GUI mode activated'
except StandardError:
    mod_PYmodsGUI = None
    traceback.print_exc()

res = ResMgr.openSection('../paths.xml')
sb = res['Paths']
vl = sb.values()[0]
if vl is not None and not hasattr(BigWorld, 'curCV'):
    BigWorld.curCV = vl.asString


class _Config(PYmodsCore._Config):
    def __init__(self):
        super(_Config, self).__init__(__file__)
        self.version = '2.1.0 (%s)' % self.version
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
                '{HEADER}Description:{/HEADER}{BODY}This time of day will be applied to all battle maps.\n'
                ' • 0:00 - old behaviour.\n • 24:00 - current local time.{/BODY}'),
            'UI_setting_enableAtStart_text': 'Sun is controlled by default',
            'UI_setting_enableAtStart_tooltip': ('{HEADER}Description:{/HEADER}{BODY}Sun position will be '
                                                 'changed automatically after battle begins.{/BODY}'),
            'UI_setting_hotkey_text': 'SunController hotkey',
            'UI_setting_hotkey_tooltip': ('{HEADER}Description:{/HEADER}{BODY}Pressing this button in-battle '
                                          'toggles sun control on/off.{/BODY}'),
            'UI_setting_enableMessage_text': 'Enable service channel message',
            'UI_setting_enableMessage_tooltip': (
                '{HEADER}Description:{/HEADER}{BODY}This allows the mod to send a notification to service channel in '
                'no-GUI mode.{/BODY}'),
            'UI_serviceChannelPopUpAll': '<b>{author}<font color="#cc9933"> turned the Earth!</font></b>',
            'UI_serviceChannelPopUpAnd': '<b><font color="#cc9933">And turned the Earth!</font></b>'}
        self.loadLang()

    def template_settings(self):
        return {'modDisplayName': self.i18n['UI_description'],
                'settingsVersion': 200,
                'enabled': self.data['enabled'],
                'column1': [{'type': 'Slider',
                             'text': self.i18n['UI_setting_time_text'],
                             'tooltip': self.i18n['UI_setting_time_tooltip'],
                             'minimum': 0,
                             'maximum': 24,
                             'snapInterval': 1,
                             'value': self.data['time'],
                             'format': '{{value}}:00',
                             'varName': 'time'},
                            {'type': 'CheckBox',
                             'text': self.i18n['UI_setting_enableMessage_text'],
                             'value': self.data['enableMessage'],
                             'tooltip': self.i18n['UI_setting_enableMessage_tooltip'],
                             'varName': 'enableMessage'}],
                'column2': [{'type': 'HotKey',
                             'text': self.i18n['UI_setting_hotkey_text'],
                             'tooltip': self.i18n['UI_setting_hotkey_tooltip'],
                             'value': self.data['hotkey'],
                             'defaultValue': self.defaultKeys['hotkey'],
                             'varName': 'hotkey'},
                            {'type': 'CheckBox',
                             'text': self.i18n['UI_setting_enableAtStart_text'],
                             'value': self.data['enableAtStartup'],
                             'tooltip': self.i18n['UI_setting_enableAtStart_tooltip'],
                             'varName': 'enableAtStartup'}]}

    def apply_settings(self, settings):
        global isSunControlled
        super(_Config, self).apply_settings(settings)
        isSunControlled = _config.data['enableAtStartup']
        _gui_config.update_template('%s' % self.ID, self.template_settings)

    def update_settings(self, doPrint=False):
        super(_Config, self).update_settings()
        _gui_config.updateFile('%s' % self.ID, self.data, self.template_settings)


_gui_config = getattr(mod_PYmodsGUI, 'g_gui', None)
_config = _Config()
_config.load()
if _config.data['enableMessage']:
    isLogin = True
    LOGIN_TEXT_MESSAGE = _config.i18n['UI_serviceChannelPopUpAll'].format(
        author='<font color="#DD7700">Polyacov_Yury</font>')
    if os.path.isfile('%s/%s/mod_LampLights.pyc' % (BigWorld.curCV, os.path.dirname(__file__))):
        try:
            from gui.mods import mod_LampLights

            if mod_LampLights._config.ID not in getattr(_gui_config, 'gui', {}) and \
                    mod_LampLights._config.data['enableMessage']:
                LOGIN_TEXT_MESSAGE = _config.i18n['UI_serviceChannelPopUpAnd']
        except StandardError:
            pass


    def new_populate(self):
        global isLogin
        old_populate(self)
        if isLogin and _config.ID not in getattr(_gui_config, 'gui', {}):
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


class Analytics(PYmodsCore.Analytics):
    def __init__(self):
        super(Analytics, self).__init__()
        self.mod_description = 'SunController'
        self.mod_id_analytics = 'UA-76792179-3'
        self.mod_version = '2.1.0'


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
