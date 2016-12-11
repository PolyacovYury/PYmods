# -*- coding: utf-8 -*-
import traceback
from functools import partial

import BigWorld
import Keys
import ResMgr

import Vehicle
from gui import InputHandler
from gui.Scaleform.daapi.view.lobby.LobbyView import LobbyView
from gui.app_loader.loader import g_appLoader
from gui.mods import PYmodsCore
from gui.mods.PYmodsCore import Sound

try:
    from gui.mods import mod_PYmodsGUI
except ImportError:
    mod_PYmodsGUI = None
    print 'Horns: no-GUI mode activated'
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
        self.version = '2.2.0 (%s)' % self.version
        self.defaultKeys = {'hotkey': [Keys.KEY_G], 'hotKey': ['KEY_G']}
        self.data = {'enabled': True,
                     'event': 4,
                     'playTime': 1.0,
                     'chatEnable': True,
                     'hotkey': self.defaultKeys['hotkey'],
                     'hotKey': self.defaultKeys['hotKey']}
        self.i18n = {
            'UI_description': 'Horns',
            'UI_setting_hornEvent_text': 'Number of horn sound',
            'UI_setting_hornEvent_tooltip': (
                '{HEADER}Description:{/HEADER}{BODY}This setting changes the number of horn sound event.\nSound will '
                'be previewed upon pressing "Apply" button.{/BODY}'),
            'UI_setting_hotkey_text': 'Horn activation hotkey',
            'UI_setting_hotkey_tooltip': (
                '{HEADER}Description:{/HEADER}{BODY}Pressing this button in-battle creates a horn sound.{/BODY}'),
            'UI_setting_chatEnable_text': 'Enable chat writing module',
            'UI_setting_chatEnable_tooltip': (
                '{HEADER}Description:{/HEADER}{BODY}If toggled on, pressing a hotkey causes the mod to send a '
                'message in chat.\n<b>Current message variants:</b>\nWhen an ally tank is a target:\n{ally}\n'
                'When an enemy tank is a target:\n{enemy}\nWhen no tank is a target:\n{default}{/BODY}'),
            'UI_setting_chatEnable_tooltip_empty': ' • No text will be sent.',
            'UI_setting_playTime_text': 'Time of event playback (cycle period)',
            'UI_setting_playTime_tooltip': (
                '{HEADER}Description:{/HEADER}{BODY}This setting changes time between starting a horn playback '
                'and rolling back to the beginning if a key is still pressed.{/BODY}'),
            'allyText': ['{name}, what are you doing, man?'],
            'enemyText': ['{name}, ahoy!'],
            'defaultText': ['Hello everyone!']}
        self.lastRandID = {'ally': -1,
                           'enemy': -1,
                           'default': -1}
        self.doSoundPlay = False
        self.hornSoundEvent = None
        self.soundCallback = None
        self.count = 0
        self.loadLang()

    def template_settings(self):
        tooltipStr = self.i18n['UI_setting_chatEnable_tooltip']
        tooltipVariants = self.tooltipSubs
        for chatID in ('ally', 'enemy', 'default'):
            if self.i18n['%sText' % chatID]:
                tooltipVariants[chatID] = ' • ' + '\n • '.join(self.i18n['%sText' % chatID])
            else:
                tooltipVariants[chatID] = self.i18n['UI_setting_chatEnable_tooltip_empty']
        tooltipStr = tooltipStr.format(**tooltipVariants)
        return {'modDisplayName': self.i18n['UI_description'],
                'settingsVersion': 200,
                'enabled': self.data['enabled'],
                'column1': [{'type': 'CheckBox',
                             'text': self.i18n['UI_setting_chatEnable_text'],
                             'value': self.data['chatEnable'],
                             'tooltip': tooltipStr,
                             'varName': 'chatEnable'},
                            {'type': 'Slider',
                             'text': self.i18n['UI_setting_hornEvent_text'],
                             'tooltip': self.i18n['UI_setting_hornEvent_tooltip'],
                             'minimum': 1,
                             'maximum': 8,
                             'snapInterval': 1,
                             'value': self.data['event'],
                             'format': '{{value}}',
                             'varName': 'event'}],
                'column2': [{'type': 'HotKey',
                             'text': self.i18n['UI_setting_hotkey_text'],
                             'tooltip': self.i18n['UI_setting_hotkey_tooltip'],
                             'value': self.data['hotkey'],
                             'defaultValue': self.defaultKeys['hotkey'],
                             'varName': 'hotkey'},
                            {'type': 'Slider',
                             'text': self.i18n['UI_setting_playTime_text'],
                             'tooltip': self.i18n['UI_setting_playTime_tooltip'],
                             'minimum': 0.1,
                             'maximum': 6.0,
                             'snapInterval': 0.1,
                             'value': self.data['playTime'],
                             'format': '{{value}}',
                             'varName': 'playTime'}]}

    def apply_settings(self, settings):
        for setting in settings:
            if setting in self.data:
                if setting in ('playTime', 'event') and self.data[setting] != settings[setting]:
                    self.doSoundPlay = True

        super(_Config, self).apply_settings(settings)
        _gui_config.update_template('%s' % self.ID, self.template_settings)

    def update_settings(self, doPrint=False):
        super(_Config, self).update_settings()
        _gui_config.updateFile('%s' % self.ID, self.data, self.template_settings)

    def onApply(self):
        self.hornSoundEvent = Sound('event_%shorn' % self.data['event'])
        self.count = self.data['playTime']
        SoundLoop(self.doSoundPlay)
        self.doSoundPlay = False
        BigWorld.callback(self.data['playTime'] + 0.1, partial(SoundLoop, False))

    def onWindowClose(self):
        SoundLoop(False)


_gui_config = getattr(mod_PYmodsGUI, 'g_gui', None)
_config = _Config()
_config.load()


def __getBattleOn():
    return hasattr(BigWorld.player(), 'arena')


def __getIsLive(entityID):
    return __getBattleOn() and entityID in BigWorld.player().arena.vehicles and \
           BigWorld.player().arena.vehicles.get(entityID)['isAlive']


def __getIsFriendly(entityID):
    return __getBattleOn() and BigWorld.player().arena.vehicles[BigWorld.player().playerVehicleID]['team'] == \
                               BigWorld.player().arena.vehicles[entityID]['team']


def getCrosshairType():
    target = BigWorld.target()
    if type(target) is Vehicle.Vehicle and __getIsLive(target.id):
        if not __getIsFriendly(target.id):
            return 'enemy'
        else:
            return 'ally'
    return 'default'


def calltext():
    try:
        chatType = getCrosshairType()
        target = BigWorld.target()
        player = BigWorld.player()
        if target is None:
            target = BigWorld.entities.get(player.playerVehicleID)
        curVariantList = _config.i18n[chatType + 'Text']
        msg, _config.lastRandID[chatType] = PYmodsCore.pickRandomPart(curVariantList, _config.lastRandID[chatType])
        if '{name}' in msg:
            msg = msg.format(name=target.publicInfo.name)
        if msg:
            PYmodsCore.sendChatMessage(msg, 1, 1.0)
    except StandardError:
        traceback.print_exc()


def SoundLoop(start):
    if start:
        if _config.count >= _config.data['playTime']:
            if _config.hornSoundEvent.isPlaying:
                _config.hornSoundEvent.stop()
            _config.hornSoundEvent = Sound('event_%shorn' % _config.data['event'])
            _config.hornSoundEvent.play()
            _config.count = 0.1
        else:
            _config.count += 0.1
        _config.soundCallback = BigWorld.callback(0.1, partial(SoundLoop, True))
    elif getattr(_config, 'hornSoundEvent', None) is not None:
        _config.hornSoundEvent.stop()
        if _config.soundCallback is not None:
            BigWorld.cancelCallback(_config.soundCallback)
            _config.soundCallback = None


def inj_hkKeyEvent(event):
    BattleApp = g_appLoader.getDefBattleApp()
    try:
        if BattleApp and _config.data['enabled']:
            if not (len(_config.data['hotkey']) == 1 and BigWorld.player()._PlayerAvatar__forcedGuiCtrlModeFlags):
                if PYmodsCore.checkKeys(_config.data['hotkey']) and event.isKeyDown():
                    _config.hornSoundEvent = Sound('event_%shorn' % _config.data['event'])
                    _config.count = _config.data['playTime']
                    SoundLoop(True)
                    if _config.data['chatEnable']:
                        calltext()
                else:
                    SoundLoop(False)
    except StandardError:
        print 'Horns: ERROR at inj_hkKeyEvent\n%s' % traceback.print_exc()


InputHandler.g_instance.onKeyDown += inj_hkKeyEvent
InputHandler.g_instance.onKeyUp += inj_hkKeyEvent


class Analytics(PYmodsCore.Analytics):
    def __init__(self):
        super(Analytics, self).__init__()
        self.mod_description = 'Horns'
        self.mod_id_analytics = 'UA-76792179-5'
        self.mod_version = '2.2.0'


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
