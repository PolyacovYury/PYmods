# coding=utf-8
import math

import Keys
import Math
import PYmodsCore
import traceback
from gui import InputHandler
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
                     'cameraPositions': [{'target_pos': [0.0, 1.2, 0.0],
                                          'pivot_pos': [0.0, 1.0, 0.0],
                                          'angles': [20.0, -13.0],
                                          'dist': 10.0}],
                     'currentCamPos': 0}
        self.i18n = {
            'UI_description': 'Hangar screenshots',
            'UI_setting_togglekey_text': 'Mod activation hotkey',
            'UI_setting_togglekey_tooltip': 'Pressing this button in hangar turns hangar UI off and locks the camera.',
            'UI_setting_camkey_text': 'Camera angle change hotkey',
            'UI_setting_camkey_tooltip': 'Pressing this button in hangar while the mod is active changes the camera view '
                                         'point.'}
        self.loadLang()

    def template_settings(self):
        return {'modDisplayName': self.i18n['UI_description'],
                'settingsVersion': 200,
                'enabled': self.data['enabled'],
                'column1': [self.createHotKey('togglekey')],
                'column2': [self.createHotKey('camkey')]}


_config = _Config()
_config.load()


def toggleHangarUI(visible):
    lobby = g_appLoader.getApp()
    hangar = lobby.containerManager.getView(ViewTypes.LOBBY_SUB)
    hangar.flashObject.visible = not hangar.flashObject.visible


@PYmodsCore.overrideMethod(ClientHangarSpace, 'updateCameraByMouseMove')
def new_updateCameraByMouseMove(base, *args):
    if _config.data['UIVisible'] or not _config.data['cameraPositions']:
        base(*args)


def setCameraLocation(settings):
    g_hangarSpace.space.setCameraLocation(Math.Vector3(*settings['target_pos']), Math.Vector3(*settings['pivot_pos']),
                                          math.radians(settings['angles'][0]), math.radians(settings['angles'][1]),
                                          settings['dist'], True)


def inj_hkKeyEvent(event):
    LobbyApp = g_appLoader.getDefLobbyApp()
    try:
        if LobbyApp:
            if _config.data['enabled']:
                if event.isKeyDown():
                    if PYmodsCore.checkKeys(_config.data['togglekey']):
                        _config.data['UIVisible'] = not _config.data['UIVisible']
                        toggleHangarUI(_config.data['UIVisible'])
                        if not _config.data['UIVisible'] and _config.data['cameraPositions']:
                            setCameraLocation(_config.data['cameraPositions'][_config.data['currentCamPos']])
                    elif PYmodsCore.checkKeys(_config.data['camkey']):
                        if not _config.data['UIVisible'] and _config.data['cameraPositions']:
                            _config.data['currentCamPos'] += 1
                            if _config.data['currentCamPos'] >= len(_config.data['cameraPositions']):
                                _config.data['currentCamPos'] = 0
                            setCameraLocation(_config.data['cameraPositions'][_config.data['currentCamPos']])
            elif not _config.data['UIVisible']:
                _config.data['currentCamPos'] = 0
                _config.data['UIVisible'] = True
                toggleHangarUI(True)
    except StandardError:
        print '%s: ERROR at inj_hkKeyEvent' % _config.ID
        traceback.print_exc()


InputHandler.g_instance.onKeyDown += inj_hkKeyEvent
InputHandler.g_instance.onKeyUp += inj_hkKeyEvent
