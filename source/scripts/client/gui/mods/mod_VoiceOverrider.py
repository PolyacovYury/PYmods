import itertools

import BigWorld
import SoundGroups
import nations
from PYmodsCore import overrideMethod, PYmodsConfigInterface, Analytics
from Vehicle import Vehicle
from debug_utils import LOG_ERROR
from gui.app_loader import g_appLoader
from gui.shared.utils import functions


class ConfigInterface(PYmodsConfigInterface):
    ALT_VOICES_PREVIEW = itertools.cycle(('wwsound_mode_preview01', 'wwsound_mode_preview02', 'wwsound_mode_preview03'))

    def __init__(self):
        self.__previewSound = None
        self.__previewNations = []
        self.modes = [
            'default_male', 'default_female', 'national_male', 'national_female', 'valkyire_male', 'valkyire_female',
            'sabaton', 'buffon']
        self.params = [
            {}, {'female': True}, {'national': True}, {'national': True, 'female': True}, {'param': 'valkyire2'},
            {'param': 'valkyire1'}, {'param': 'sabaton'}, {'param': 'buffon'}]
        super(ConfigInterface, self).__init__()

    def init(self):
        self.ID = '%(mod_ID)s'
        self.version = '1.0.0 (%(file_compile_date)s)'
        self.data = {'enabled': True, 'mode': 0}
        self.i18n = {
            'name': 'Ingame voice messages mode override',
            'UI_setting_mode_text': 'Ingame voice messages mode',
            'UI_setting_mode_default_male': 'Default: male',
            'UI_setting_mode_default_female': 'Default: female',
            'UI_setting_mode_national_male': 'National: male',
            'UI_setting_mode_national_female': 'National: female',
            'UI_setting_mode_valkyire_male': 'Valkyire Chronicles: male',
            'UI_setting_mode_valkyire_female': 'Valkyire Chronicles: female',
            'UI_setting_mode_sabaton': 'Sabaton',
            'UI_setting_mode_buffon': 'Buffon'}
        super(ConfigInterface, self).init()

    def createTemplate(self):
        return {'modDisplayName': self.i18n['name'],
                'settingsVersion': 1,
                'enabled': self.data['enabled'],
                'column1': [self.tb.createOptions(
                    'mode', [self.i18n['UI_setting_mode_%s' % mode] for mode in self.modes],
                    button={'iconSource': '../maps/icons/buttons/sound.png'})],
                'column2': []}

    def onButtonPress(self, container, linkage, vName, value):
        if container != self.modSettingsID or linkage != self.ID or vName != 'mode':
            return
        self.data[vName] = int(value)
        self.playPreviewSound()

    def onMSADestroy(self):
        self.clearPreviewSound()
        self.readCurrentSettings()

    def playPreviewSound(self):
        if not self.setSystemValue():
            return
        self.clearPreviewSound()
        sndMgr = g_appLoader.getDefLobbyApp().soundManager
        if sndMgr is None:
            LOG_ERROR('GUI sound manager is not found')
            return
        sndPath = sndMgr.sounds.getEffectSound(next(self.ALT_VOICES_PREVIEW))
        if self.params[self.data['mode']].get('national', False):
            self.__previewNations = list(nations.AVAILABLE_NAMES)
            self.__previewSound = SoundGroups.g_instance.getSound2D(sndPath)
            if self.__previewSound is not None:
                self.__previewSound.setCallback(self.playPreview)
                self.playPreview(self.__previewSound)
            return True
        genderSwitch = SoundGroups.CREW_GENDER_SWITCHES.GENDER_ALL[self.params[self.data['mode']].get('female', False)]
        SoundGroups.g_instance.setSwitch(SoundGroups.CREW_GENDER_SWITCHES.GROUP, genderSwitch)
        self.__previewSound = SoundGroups.g_instance.getSound2D(sndPath)
        if self.__previewSound is not None:
            self.__previewSound.play()

    def clearPreviewSound(self):
        if self.__previewSound is not None:
            self.__previewSound.stop()
            self.__previewSound = None
        player = BigWorld.player()
        if hasattr(player, 'vehicle'):
            vehicle = player.vehicle
            if vehicle is not None:
                player.vehicle.refreshNationalVoice()

    def playPreview(self, sound):
        if self.__previewNations and self.__previewSound == sound:
            nation = self.__previewNations.pop()
            genderSwitch = SoundGroups.CREW_GENDER_SWITCHES.GENDER_ALL[self.params[self.data['mode']].get('female', False)]
            SoundGroups.g_instance.soundModes.setCurrentNation(nation, genderSwitch)
            sound.play()

    def setSystemValue(self):
        mode = self.params[self.data['mode']]
        soundModes = SoundGroups.g_instance.soundModes
        if mode.get('param', None) is not None:
            return soundModes.setMode(mode['param'])
        soundModes.setCurrentNation(SoundGroups.g_instance.soundModes.DEFAULT_NATION)
        if mode.get('national', False):
            return soundModes.setNationalMappingByPreset('NationalDefault')
        return soundModes.setNationalMappingByMode('default')


g_config = ConfigInterface()
analytics = Analytics(g_config.ID, g_config.version, 'UA-76792179-22')


@overrideMethod(Vehicle, 'refreshNationalVoice')
def new_refreshNationalVoice(base, self, *a, **kw):
    base(self, *a, **kw)
    if not g_config.data['enabled'] or self is not BigWorld.player().getVehicleAttached():
        return
    soundModes = SoundGroups.g_instance.soundModes
    soundModes.setCurrentNation(SoundGroups.g_instance.soundModes.DEFAULT_NATION)
    g_config.setSystemValue()
    nationID = self.typeDescriptor.type.id[0]
    genderSwitch = SoundGroups.CREW_GENDER_SWITCHES.GENDER_ALL[g_config.params[g_config.data['mode']].get('female', False)]
    soundModes.setCurrentNation(nations.NAMES[nationID], genderSwitch)
