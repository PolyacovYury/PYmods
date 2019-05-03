# coding=utf-8
import math

import BigWorld
import Keys
import Math
import traceback
from PYmodsCore import PYmodsConfigInterface, loadJson, overrideMethod, checkKeys, Analytics
from gui import InputHandler, SystemMessages
from gui.ClientHangarSpace import hangarCFG
from gui.Scaleform.framework import ViewTypes
from gui.hangar_cameras.hangar_camera_manager import HangarCameraManager
from gui.shared.personality import ServicesLocator
from helpers import dependency
from skeletons.gui.shared.utils import IHangarSpace


class ConfigInterface(PYmodsConfigInterface):
    def __init__(self):
        self.cameraPos = []
        super(ConfigInterface, self).__init__()

    def init(self):
        self.ID = '%(mod_ID)s'
        self.version = '1.1.1 (%(file_compile_date)s)'
        self.author += ' (thx to Chirimen, alphasave1)'
        self.defaultKeys = {'togglekey': [Keys.KEY_F11], 'camkey': [Keys.KEY_F12]}
        self.data = {'enabled': True,
                     'UIVisible': True,
                     'togglekey': self.defaultKeys['togglekey'],
                     'camkey': self.defaultKeys['camkey'],
                     'lockCamera': True,
                     'addUnlockMode': True,
                     'currentCamPos': 0}
        self.cameraPos = [{'target_pos': "", 'pivot_pos': "", 'angles': [20.0, -13.0], 'dist': 10.0}]
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
        super(ConfigInterface, self).init()

    def createTemplate(self):
        return {'modDisplayName': self.i18n['UI_description'],
                'enabled': self.data['enabled'],
                'column1': [self.tb.createHotKey('togglekey'),
                            self.tb.createControl('lockCamera')],
                'column2': [self.tb.createHotKey('camkey'),
                            self.tb.createControl('addUnlockMode')]}

    def readCurrentSettings(self, quiet=True):
        super(ConfigInterface, self).readCurrentSettings(quiet)
        self.cameraPos = loadJson(self.ID, 'cameraPositions', self.cameraPos, self.configPath, quiet=quiet)


config = ConfigInterface()


def toggleHangarUI(visible):
    lobby = ServicesLocator.appLoader.getApp()
    hangar = lobby.containerManager.getView(ViewTypes.LOBBY_SUB)
    hangar.as_setVisibleS(visible)
    lobby.graphicsOptimizationManager.switchOptimizationEnabled(visible)


@overrideMethod(HangarCameraManager, '_HangarCameraManager__updateCameraByMouseMove')
def new_updateCameraByMouseMove(base, *args, **kwargs):
    if config.data['UIVisible'] or not config.cameraPos or config.data['currentCamPos'] == len(
            config.cameraPos) or not config.data['lockCamera']:
        base(*args, **kwargs)


def setCameraLocation(settings):
    cfg = hangarCFG()
    dependency.instance(IHangarSpace).space.setCameraLocation(
        cfg[settings['target_pos'] + 'cam_start_target_pos'], Math.Vector3(*settings['pivot_pos']) if isinstance(
            settings['pivot_pos'], list) else cfg[settings['pivot_pos'] + 'cam_pivot_pos'],
        math.radians(settings['angles'][0]), math.radians(settings['angles'][1]), settings['dist'],
        None, True)


def inj_hkKeyEvent(event):
    if not hasattr(BigWorld.player(), 'databaseID'):
        return
    try:
        if config.data['enabled']:
            if event.isKeyDown() and checkKeys(config.data['togglekey'], event.key):
                config.data['UIVisible'] = not config.data['UIVisible']
                toggleHangarUI(config.data['UIVisible'])
                if not config.data['UIVisible'] and config.cameraPos and config.data['currentCamPos'] < len(config.cameraPos):
                    setCameraLocation(config.cameraPos[config.data['currentCamPos']])
            elif event.isKeyDown() and checkKeys(config.data['camkey'], event.key) and not config.data['UIVisible'] and config.cameraPos:
                config.data['currentCamPos'] += 1
                if config.data['currentCamPos'] == len(config.cameraPos) and config.data[
                        'addUnlockMode'] and config.data['lockCamera']:
                    SystemMessages.pushMessage(
                        'temp_SM' + config.i18n['UI_message_cameraUnlocked'], SystemMessages.SM_TYPE.Warning)
                else:
                    if config.data['currentCamPos'] >= len(config.cameraPos) + (config.data[
                            'addUnlockMode'] and config.data['lockCamera']):
                        config.data['currentCamPos'] = 0
                    setCameraLocation(config.cameraPos[config.data['currentCamPos']])
        elif not config.data['UIVisible']:
            config.data['currentCamPos'] = 0
            config.data['UIVisible'] = True
            toggleHangarUI(True)
    except StandardError:
        print config.ID + ': ERROR at inj_hkKeyEvent'
        traceback.print_exc()


InputHandler.g_instance.onKeyDown += inj_hkKeyEvent
InputHandler.g_instance.onKeyUp += inj_hkKeyEvent
analytics = Analytics(config.ID, config.version, 'UA-76792179-14')
