import itertools

import BigWorld
import SoundGroups
import nations
from PYmodsCore import overrideMethod, PYmodsConfigInterface, Analytics
from Vehicle import Vehicle
from debug_utils import LOG_ERROR
from gui.shared.personality import ServicesLocator
from items.vehicles import VehicleDescr


class ConfigInterface(PYmodsConfigInterface):
    VOICE_PREVIEW = itertools.cycle(('wwsound_mode_preview01', 'wwsound_mode_preview02', 'wwsound_mode_preview03'))

    def __init__(self):
        self.__previewSound = None
        self.__previewNations = []
        self.modes = [
            'default_male', 'default_female', 'national_male', 'national_female', 'valkyrie_male', 'valkyrie_female',
            'sabaton', 'buffon', 'offspring']
        self.params = [
            {}, {'female': True}, {'national': True}, {'national': True, 'female': True},
            {'languageMode': 'valkyrie2'}, {'languageMode': 'valkyrie1'},
            {'languageMode': 'sabaton'}, {'languageMode': 'buffon'}, {'languageMode': 'offspring'}]
        super(ConfigInterface, self).__init__()

    def init(self):
        self.ID = '%(mod_ID)s'
        self.version = '1.1.0 (%(file_compile_date)s)'
        self.data = {'enabled': True, 'mode': 0}
        self.i18n = {
            'name': 'Ingame voice messages mode override',
            'UI_setting_mode_text': 'Ingame voice messages mode',
            'UI_setting_mode_default_male': 'Default: male',
            'UI_setting_mode_default_female': 'Default: female',
            'UI_setting_mode_national_male': 'National: male',
            'UI_setting_mode_national_female': 'National: female',
            'UI_setting_mode_valkyrie_male': 'Valkyrie Chronicles: male',
            'UI_setting_mode_valkyrie_female': 'Valkyrie Chronicles: female',
            'UI_setting_mode_sabaton': 'Sabaton',
            'UI_setting_mode_buffon': 'Buffon',
            'UI_setting_mode_offspring': 'The Offspring'}
        super(ConfigInterface, self).init()

    def createTemplate(self):
        return {'modDisplayName': self.i18n['name'],
                'enabled': self.data['enabled'],
                'column1': [self.tb.createOptions(
                    'mode', [self.i18n['UI_setting_mode_%s' % mode] for mode in self.modes],
                    button={'iconSource': '../maps/icons/buttons/sound.png'})],
                'column2': []}

    def onButtonPress(self, vName, value):
        if vName != 'mode':
            return
        self.data[vName] = int(value)
        self.playPreviewSound()

    def onMSADestroy(self):
        self.readCurrentSettings()
        self.clearPreviewSound()

    def playPreviewSound(self):
        self.clearPreviewSound()
        sndMgr = ServicesLocator.appLoader.getApp().soundManager
        if sndMgr is None:
            LOG_ERROR('GUI sound manager is not found')
            return
        sndPath = sndMgr.sounds.getEffectSound(next(self.VOICE_PREVIEW))
        self.__previewSound = SoundGroups.g_instance.getSound2D(sndPath)
        if self.__previewSound is None:
            return
        if self.params[self.data['mode']].get('national', False):
            self.__previewNations = list(nations.AVAILABLE_NAMES)
            self.__previewSound.setCallback(self.playPreview)
            self.playPreview(self.__previewSound)
        else:
            self.__previewSound.play()
        return True

    def clearPreviewSound(self):
        if self.__previewSound is not None:
            self.__previewSound.stop()
            self.__previewSound = None
        self.setSystemValue()
        vehicle = getattr(BigWorld.player(), 'vehicle', None)
        if vehicle is not None:
            vehicle.refreshNationalVoice()

    def playPreview(self, sound):
        if self.__previewNations and sound == self.__previewSound:
            self.setSystemValue(self.__previewNations.pop())
            sound.play()

    def setSystemValue(self, nation=None):
        params = self.params[self.data['mode']]
        soundModes = SoundGroups.g_instance.soundModes
        if params.get('languageMode', None) is not None:
            return soundModes.setMode(params['languageMode'])
        gender = SoundGroups.CREW_GENDER_SWITCHES.GENDER_ALL[self.params[self.data['mode']].get('female', False)]
        soundModes.setCurrentNation(nation or soundModes.DEFAULT_NATION, gender)
        if params.get('national', False):
            return soundModes.setNationalMappingByPreset('NationalDefault')
        return soundModes.setNationalMappingByMode('default')


g_config = ConfigInterface()
analytics = Analytics(g_config.ID, g_config.version, 'UA-76792179-22')


@overrideMethod(Vehicle, 'refreshNationalVoice')
def new_refreshNationalVoice(base, self, *a, **kw):
    base(self, *a, **kw)
    player = BigWorld.player()
    if not g_config.data['enabled'] or self.id not in (player.playerVehicleID, player.observedVehicleID):
        return
    g_config.setSystemValue(nations.NAMES[VehicleDescr(self.publicInfo.compDescr).type.id[0]])
