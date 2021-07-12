# -*- coding: utf-8 -*-
import BigWorld
import Keys
import Vehicle
import traceback
from PYmodsCore import BigWorld_callback, Sound, PYmodsConfigInterface, pickRandomPart, sendChatMessage, checkKeys, Analytics
from gui.battle_control import avatar_getter


class ConfigInterface(PYmodsConfigInterface):
    def __init__(self):
        self.lastRandID = {'ally': -1, 'enemy': -1, 'default': -1}
        self.hornSoundEvent = None
        self.soundCallback = None
        super(ConfigInterface, self).__init__()

    def init(self):
        self.ID = '%(mod_ID)s'
        self.version = '2.4.1 (%(file_compile_date)s)'
        self.defaultKeys = {'hotkey': [Keys.KEY_G]}
        self.data = {'enabled': True,
                     'event': 4,
                     'chatEnable': True,
                     'hotkey': self.defaultKeys['hotkey']}
        self.i18n = {
            'UI_description': 'Horns',
            'UI_setting_event_text': 'Number of horn sound',
            'UI_setting_event_tooltip': 'This setting changes the number of horn sound event.\n\n'
                                        'The playback button simulates the hotkey being pressed for 3 seconds.',
            'UI_setting_hotkey_text': 'Horn activation hotkey',
            'UI_setting_hotkey_tooltip': 'Pressing this button in-battle plays a horn sound.',
            'UI_setting_chatEnable_text': 'Enable chat writing module',
            'UI_setting_chatEnable_tooltip': (
                'If toggled on, pressing a hotkey causes the mod to send a message in chat.\n<b>Current message '
                'variants:</b>\nWhen an ally tank is a target:\n%(ally)s\nWhen an enemy tank is a target:\n%(enemy)s\n'
                'When no tank is a target:\n%(default)s'),
            'UI_setting_chatEnable_tooltip_empty': ' • No text will be sent.',
            'allyText': ['{name}, what are you doing, man?'],
            'enemyText': ['{name}, ahoy!'],
            'defaultText': ['Hello everyone!']}
        super(ConfigInterface, self).init()

    def createTemplate(self):
        tooltipVariants = {}
        for chatID in ('ally', 'enemy', 'default'):
            if self.i18n['%sText' % chatID]:
                tooltipVariants[chatID] = ' • ' + '\n • '.join(self.i18n['%sText' % chatID])
            else:
                tooltipVariants[chatID] = self.i18n['UI_setting_chatEnable_tooltip_empty']
        chatCB = self.tb.createControl('chatEnable')
        chatCB['tooltip'] %= tooltipVariants
        return {'modDisplayName': self.i18n['UI_description'],
                'enabled': self.data['enabled'],
                'column1': [self.tb.createSlider('event', 1, 8, 1, button={'iconSource': '../maps/icons/buttons/sound.png'})],
                'column2': [self.tb.createHotKey('hotkey'),
                            chatCB]}

    def onButtonPress(self, vName, value):
        if vName != 'event':
            return
        self.data[vName] = int(value)
        SoundLoop(False)
        SoundLoop(True)
        self.soundCallback = BigWorld_callback(3, SoundLoop, False)

    def onMSADestroy(self):
        SoundLoop(False)
        self.readData()

    def onHotkeyPressed(self, event):
        if (not hasattr(BigWorld.player(), 'arena') or not self.data['enabled'] or (
                len(self.data['hotkey']) == 1 and BigWorld.player().getForcedGuiControlModeFlags())):
            return
        if avatar_getter.isVehicleAlive() and event.isKeyDown() and checkKeys(self.data['hotkey']):
            if not getattr(self.hornSoundEvent, 'isPlaying', False):
                SoundLoop(True)
                if self.data['chatEnable']:
                    calltext()
        else:
            SoundLoop(False)


_config = ConfigInterface()


def __getBattleOn(player):
    return hasattr(player, 'arena')


def __getIsLive(player, entityID):
    return __getBattleOn(player) and entityID in player.arena.vehicles and player.arena.vehicles.get(entityID)['isAlive']


def __getIsFriendly(player, entityID):
    return __getBattleOn(player) and player.arena.vehicles[player.playerVehicleID]['team'] == \
           player.arena.vehicles[entityID]['team']


def getCrosshairType():
    target = BigWorld.target()
    player = BigWorld.player()
    if type(target) is Vehicle.Vehicle and __getIsLive(player, target.id):
        if not __getIsFriendly(player, target.id):
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
        msg, _config.lastRandID[chatType] = pickRandomPart(curVariantList, _config.lastRandID[chatType])
        if '{name}' in msg:
            msg = msg.format(name=target.publicInfo.name)
        if msg:
            sendChatMessage(msg, 1, 1.0)
    except StandardError:
        traceback.print_exc()


def SoundLoop(start):
    if start:
        if getattr(_config.hornSoundEvent, 'isPlaying', False):
            _config.hornSoundEvent.stop()
        _config.hornSoundEvent = Sound('event_%shorn' % _config.data['event'])
        _config.hornSoundEvent.play()
    elif getattr(_config, 'hornSoundEvent', None) is not None:
        _config.hornSoundEvent.stop()
        if _config.soundCallback is not None:
            BigWorld.cancelCallback(_config.soundCallback)
            _config.soundCallback = None


statistic_mod = Analytics(_config.ID, _config.version, 'UA-76792179-5')
