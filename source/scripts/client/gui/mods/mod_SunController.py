# -*- coding: utf-8 -*-
import time

import BigWorld
import Keys
import traceback
from PYmodsCore import PYmodsConfigInterface, checkKeys, sendMessage, Analytics, events
from gui import InputHandler, SystemMessages


class ConfigInterface(PYmodsConfigInterface):
    def __init__(self):
        super(ConfigInterface, self).__init__()

    def init(self):
        self.ID = '%(mod_ID)s'
        self.version = '2.2.2 (%(file_compile_date)s)'
        self.author += ' (orig by Lp()rtii/Dellux) (thx to LSD_MAX/Delysid :P)'
        self.defaultKeys = {'hotkey': [Keys.KEY_F12]}
        self.data = {'enabled': True,
                     'time': 0,
                     'enableAtStartup': True,
                     'hotkey': self.defaultKeys['hotkey'],
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
        super(ConfigInterface, self).init()

    def createTemplate(self):
        return {'modDisplayName': self.i18n['UI_description'],
                'enabled': self.data['enabled'],
                'column1': [self.tb.createSlider('time', 0, 24, 1, '{{value}}:00'),
                            self.tb.createControl('enableMessage')],
                'column2': [self.tb.createHotKey('hotkey'),
                            self.tb.createControl('enableAtStartup')]}

    def onApplySettings(self, settings):
        global isSunControlled
        super(self.__class__, self).onApplySettings(settings)
        isSunControlled = self.data['enableAtStartup']


_config = ConfigInterface()
if _config.data['enableMessage']:
    isLogin = True


    @events.LobbyView.populate.after
    def new_Lobby_populate(*_, **__):
        LOGIN_TEXT_MESSAGE = _config.i18n['UI_serviceChannelPopUpAll'].format(
            author='<font color="#DD7700">Polyacov_Yury</font>')
        isRegistered = _config.ID in getattr(_config.MSAInstance, 'activeMods', ())
        try:
            from gui.mods import mod_lamplights
            if not isRegistered and mod_lamplights._config.data['enableMessage']:
                LOGIN_TEXT_MESSAGE = _config.i18n['UI_serviceChannelPopUpAnd']
        except StandardError:
            pass
        global isLogin
        if isLogin and not isRegistered:
            SystemMessages.pushMessage(LOGIN_TEXT_MESSAGE, type=SystemMessages.SM_TYPE.Information)
            isLogin = False

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


@events.PlayerAvatar.startGUI.after
def new_startGUI(*_, **__):
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


def battleKeyControl(event):
    global isSunControlled
    if checkKeys(_config.data['hotkey'], event.key) and event.isKeyDown():
        isSunControlled = not isSunControlled
        sun_controller(isSunControlled)
        if isSunControlled:
            sendMessage(_config.i18n['UI_activSunMod'])
        else:
            sendMessage(_config.i18n['UI_deactivSunMod'], 'Red')


def inj_hkKeyEvent(event):
    try:
        if hasattr(BigWorld.player(), 'arena') and _config.data['enabled']:
            battleKeyControl(event)
    except StandardError:
        print '%s: ERROR at inj_hkKeyEvent' % _config.ID
        traceback.print_exc()


InputHandler.g_instance.onKeyDown += inj_hkKeyEvent
InputHandler.g_instance.onKeyUp += inj_hkKeyEvent
statistic_mod = Analytics(_config.ID, _config.version, 'UA-76792179-3')
