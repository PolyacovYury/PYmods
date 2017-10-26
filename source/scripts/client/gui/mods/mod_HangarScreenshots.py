# coding=utf-8
import math

import Keys
import Math
import PYmodsCore
import traceback
from gui import InputHandler, SystemMessages
from gui.ClientHangarSpace import ClientHangarSpace
from gui.Scaleform.framework import ViewTypes
from gui.app_loader.loader import g_appLoader
from gui.shared.utils.HangarSpace import g_hangarSpace


class _Config(PYmodsCore.Config):
    def __init__(self):
        super(self.__class__, self).__init__('%(mod_ID)s')
        self.version = '1.0.0 (%(file_compile_date)s)'
        self.author += ' (thx to Chirimen, alphasave1)'
        self.defaultKeys = {'togglekey': [Keys.KEY_F11], 'toggleKey': ['KEY_F11'],
                            'camkey': [Keys.KEY_F12], 'camKey': ['KEY_F12'], }
        self.data = {'enabled': True,
                     'UIVisible': True,
                     'togglekey': self.defaultKeys['togglekey'],
                     'toggleKey': self.defaultKeys['toggleKey'],
                     'camkey': self.defaultKeys['camkey'],
                     'camKey': self.defaultKeys['camKey'],
                     'lockCamera': True,
                     'addUnlockMode': True,
                     'currentCamPos': 0}
        self.cameraPositions = [{'target_pos': [0.0, 1.2, 0.0],
                                 'pivot_pos': [0.0, 1.0, 0.0],
                                 'angles': [20.0, -13.0],
                                 'dist': 10.0}]
        self.i18n = {
            'UI_description': 'Hangar screenshots',
            'UI_message_cameraUnlocked': 'Camera unlocked.',
            'UI_setting_togglekey_text': 'Mod activation hotkey',
            'UI_setting_togglekey_tooltip': 'Pressing this button in hangar turns hangar UI off and locks the camera.',
            'UI_setting_camkey_text': 'Camera angle change hotkey',
            'UI_setting_camkey_tooltip': 'Pressing this button in hangar while the mod is active changes the camera view '
                                         'point.',
            'UI_setting_lockCamera_text': 'Lock camera when UI is disabled',
            'UI_setting_lockCamera_tooltip': 'This setting restricts you from moving your camera with a mouse when '
                                             'hangar UI is turned off.',
            'UI_setting_addUnlockMode_text': 'Add unlocked camera mode into the list of modes',
            'UI_setting_addUnlockMode_tooltip': 'This setting adds another camera view "point" into the list which lets '
                                                'you to move the camera with the mouse when hangar UI is turned off.'}
        self.loadLang()

    def template_settings(self):
        return {'modDisplayName': self.i18n['UI_description'],
                'settingsVersion': 200,
                'enabled': self.data['enabled'],
                'column1': [self.createHotKey('togglekey'),
                            self.createControl('lockCamera')],
                'column2': [self.createHotKey('camkey'),
                            self.createControl('addUnlockMode')]}

    def update_data(self, doPrint=False):
        super(self.__class__, self).update_data(doPrint)
        self.cameraPositions = self.loadJson('cameraPositions', self.cameraPositions, self.configPath, doPrint=doPrint)


_config = _Config()
_config.load()


def toggleHangarUI(visible):
    lobby = g_appLoader.getApp()
    hangar = lobby.containerManager.getView(ViewTypes.LOBBY_SUB)
    hangar.flashObject.visible = not hangar.flashObject.visible


@PYmodsCore.overrideMethod(ClientHangarSpace, 'updateCameraByMouseMove')
def new_updateCameraByMouseMove(base, *args):
    if _config.data['UIVisible'] or not _config.cameraPositions or _config.data['currentCamPos'] == len(
            _config.cameraPositions) or not _config.data['lockCamera']:
        base(*args)


def setCameraLocation(settings):
    g_hangarSpace.space.setCameraLocation(
        targetPos=Math.Vector3(*settings['target_pos']), pivotPos=Math.Vector3(*settings['pivot_pos']),
        yaw=math.radians(settings['angles'][0]), pitch=math.radians(settings['angles'][1]), dist=settings['dist'],
        ignoreConstraints=True)


def inj_hkKeyEvent(event):
    LobbyApp = g_appLoader.getDefLobbyApp()
    try:
        if LobbyApp:
            if _config.data['enabled']:
                if event.isKeyDown():
                    if PYmodsCore.checkKeys(_config.data['togglekey']):
                        _config.data['UIVisible'] = not _config.data['UIVisible']
                        toggleHangarUI(_config.data['UIVisible'])
                        if not _config.data['UIVisible'] and _config.cameraPositions and _config.data[
                                'currentCamPos'] < len(_config.cameraPositions):
                            setCameraLocation(_config.cameraPositions[_config.data['currentCamPos']])
                    elif PYmodsCore.checkKeys(_config.data['camkey']):
                        if not _config.data['UIVisible'] and _config.cameraPositions:
                            _config.data['currentCamPos'] += 1
                            if _config.data['currentCamPos'] == len(_config.cameraPositions) and _config.data[
                                    'addUnlockMode'] and _config.data['lockCamera']:
                                SystemMessages.pushMessage('PYmods_SM' + _config.i18n['UI_message_cameraUnlocked'],
                                                           SystemMessages.SM_TYPE.Warning)
                            else:
                                if _config.data['currentCamPos'] >= len(_config.cameraPositions) + (_config.data[
                                        'addUnlockMode'] and _config.data['lockCamera']):
                                    _config.data['currentCamPos'] = 0
                                setCameraLocation(_config.cameraPositions[_config.data['currentCamPos']])
            elif not _config.data['UIVisible']:
                _config.data['currentCamPos'] = 0
                _config.data['UIVisible'] = True
                toggleHangarUI(True)
    except StandardError:
        print '%s: ERROR at inj_hkKeyEvent' % _config.ID
        traceback.print_exc()


InputHandler.g_instance.onKeyDown += inj_hkKeyEvent
InputHandler.g_instance.onKeyUp += inj_hkKeyEvent
