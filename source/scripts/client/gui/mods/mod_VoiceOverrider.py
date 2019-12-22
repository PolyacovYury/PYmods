import itertools

import BigWorld
import SoundGroups
import nations
from PYmodsCore import overrideMethod, PYmodsConfigInterface, Analytics
from Vehicle import Vehicle
from debug_utils import LOG_ERROR
from gui.battle_control import avatar_getter
from gui.game_control.special_sound_ctrl import SpecialSoundCtrl
from gui.shared.personality import ServicesLocator
from items.vehicles import VehicleDescr


class ConfigInterface(PYmodsConfigInterface):
    VOICE_PREVIEW = itertools.cycle(('wwsound_mode_preview01', 'wwsound_mode_preview02', 'wwsound_mode_preview03'))

    def __init__(self):
        self.__previewSound = None
        self.__previewNations = []
        self.voice_modes = [
            'default_male', 'default_female', 'national_male', 'national_female', 'valkyrie_male', 'valkyrie_female',
            'sabaton', 'buffon', 'offspring', 'racer_ru', 'racer_en']
        self.voice_params = [
            {}, {'female': True}, {'national': True}, {'national': True, 'female': True},
            {'languageMode': 'valkyrie2'}, {'languageMode': 'valkyrie1'},
            {'languageMode': 'sabaton'}, {'languageMode': 'buffon'}, {'languageMode': 'offspring'},
            {'languageMode': 'racer_ru'}, {'languageMode': 'racer_en'}]
        self.music_modes = ['default', 'offspring']
        self.music_params = [{'tag': 'default'}, {'tag': 'offspringArenaMusic'}]
        super(ConfigInterface, self).__init__()

    def init(self):
        self.ID = '%(mod_ID)s'
        self.version = '1.1.0 (%(file_compile_date)s)'
        self.data = {'enabled': True, 'voice': 0, 'music': 0}
        self.i18n = {
            'name': 'Ingame voice messages override',
            'UI_setting_music_text': 'Ingame music mode',
            'UI_setting_music_default': 'Default',
            'UI_setting_music_offspring': 'The Offspring',
            'UI_setting_voice_text': 'Ingame voice messages mode',
            'UI_setting_voice_default_male': 'Default: male',
            'UI_setting_voice_default_female': 'Default: female',
            'UI_setting_voice_national_male': 'National: male',
            'UI_setting_voice_national_female': 'National: female',
            'UI_setting_voice_valkyrie_male': 'Valkyrie Chronicles: male',
            'UI_setting_voice_valkyrie_female': 'Valkyrie Chronicles: female',
            'UI_setting_voice_sabaton': 'Sabaton',
            'UI_setting_voice_buffon': 'Buffon',
            'UI_setting_voice_offspring': 'The Offspring',
            'UI_setting_voice_racer_ru': 'Racer (RU)',
            'UI_setting_voice_racer_en': 'Racer (EN)',
        }
        super(ConfigInterface, self).init()

    def migrateConfigs(self):
        data = self.loadDataJson(quiet=False)
        if 'mode' in data:
            data['voice'] = data.pop('mode')
        self.writeDataJson()

    def createTemplate(self):
        return {'modDisplayName': self.i18n['name'],
                'enabled': self.data['enabled'],
                'column1': [self.tb.createOptions(
                    'voice', [self.i18n['UI_setting_voice_%s' % mode] for mode in self.voice_modes],
                    button={'iconSource': '../maps/icons/buttons/sound.png'})],
                'column2': [self.tb.createOptions(
                    'music', [self.i18n['UI_setting_music_%s' % mode] for mode in self.music_modes],
                    button={'iconSource': '../maps/icons/buttons/sound.png'})]}

    def onButtonPress(self, vName, value):
        if vName != 'voice':
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
        if self.voice_params[self.data['voice']].get('national', False):
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
        params = self.voice_params[self.data['voice']]
        soundModes = SoundGroups.g_instance.soundModes
        if params.get('languageMode', None) is not None:
            return soundModes.setMode(params['languageMode'])
        gender = SoundGroups.CREW_GENDER_SWITCHES.GENDER_ALL[self.voice_params[self.data['voice']].get('female', False)]
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


@overrideMethod(SpecialSoundCtrl, 'setPlayerVehicle')
def new_setPlayerVehicle(base, self, *a, **k):
    base(self, *a, **k)
    arena = avatar_getter.getArena()
    if arena is None:
        return
    self._SpecialSoundCtrl__arenaMusicSetup = musicSetup = arena.arenaType.wwmusicSetup.copy()
    tag = g_config.music_params[g_config.data['music']].get('tag')
    musicSetup.update(self._SpecialSoundCtrl__arenaMusicByStyle.get(tag, ()))
