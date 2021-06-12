import BigWorld
import SoundGroups
import itertools
import nations
from PYmodsCore import overrideMethod, PYmodsConfigInterface, Analytics
from collections import namedtuple
from debug_utils import LOG_ERROR
from gui.battle_control import avatar_getter
from gui.game_control.special_sound_ctrl import SpecialSoundCtrl
from gui.shared.personality import ServicesLocator
from items.vehicles import VehicleDescr

VoiceMode = namedtuple('VoiceMode', 'name, languageMode, national, female')
VoiceMode.__new__.__defaults__ = (None, False, False)
MusicMode = namedtuple('MusicMode', 'name, tag')


class ConfigInterface(PYmodsConfigInterface):
    VOICE_PREVIEW = itertools.cycle(('wwsound_mode_preview01', 'wwsound_mode_preview02', 'wwsound_mode_preview03'))

    def __init__(self):
        self.__previewSound = None
        self.__previewNations = []
        # noinspection PyArgumentList,SpellCheckingInspection
        self.voice_modes = [
            VoiceMode('default_male'), VoiceMode('default_female', female=True), VoiceMode('national_male', national=True),
            VoiceMode('national_female', national=True, female=True),
            VoiceMode('valkyrie_male', 'valkyrie2'), VoiceMode('valkyrie_female', 'valkyrie1'),
            VoiceMode('sabaton', 'sabaton'), VoiceMode('buffon', 'buffon'), VoiceMode('offspring', 'offspring'),
            VoiceMode('celebrity2021_ru', 'celebrity2021_ru'), VoiceMode('celebrity2021_en', 'celebrity2021_en'),
            VoiceMode('racer_ru', 'racer_ru'), VoiceMode('racer_en', 'racer_en'),
            VoiceMode('20_LeBwa', 'ru1_Lebwa'), VoiceMode('20_Yusha', 'ru2_Yusha'),
            VoiceMode('20_Amway921', 'ru3_Amway921'), VoiceMode('20_KorbenDallas', 'ru4_KorbenDallas'),
            VoiceMode('20_Mailand', 'eu1_Mailand'), VoiceMode('20_Skill4ltu', 'eu2_Skill4ltu'),
            VoiceMode('20_Dezgamez', 'eu3_Dezgamez'), VoiceMode('20_AwesomeEpicGuys', 'eu4_AwesomeEpicGuys'),
            VoiceMode('21_Yusha', 'bb21_ru1_Yusha'), VoiceMode('21_Vspishka', 'bb21_ru1_Vspishka'),
            VoiceMode('21_Amway921', 'bb21_ru2_Amway921'), VoiceMode('21_KorbenDallas', 'bb21_ru2_Korbendailas'),
            VoiceMode('21_LeBwa', 'bb21_ru3_Lebwa'), VoiceMode('21_Inspirer', 'bb21_ru3_Inspirer'),
            VoiceMode('21_Evil_Granny', 'bb21_ru4_Evilgranny'), VoiceMode('21_Near_You', 'bb21_ru4_Nearyou'),
            VoiceMode('21_Circon', 'bb21_eu1_Circon'), VoiceMode('21_Dakillzor', 'bb21_eu2_Dakillzor'),
            VoiceMode('21_Newmulti2k', 'bb21_eu3_Newmulti2k'), VoiceMode('21_Orzanel', 'bb21_eu4_Orzanel'),
            VoiceMode('21_CabMech', 'bb21_na1_Cabbagemechanic'), VoiceMode('21_TragicLoss', 'bb21_na2_Tragicloss'),
            VoiceMode('21_Cmdr_AF', 'bb21_na3_Cmdraf'), VoiceMode('21_MasterTortoise', 'bb21_asia1_Mastertortoise'),
            VoiceMode('21_SummerTiger', 'bb21_asia2_Summertiger'), VoiceMode('21_Maharlika', 'bb21_asia3_Maharlika'),
            VoiceMode('gup_jp_commander', 'gup_jp_commander'), VoiceMode('gup_jp_crew', 'gup_jp_crew'),
            VoiceMode('duke', 'duke'), VoiceMode('cobra', 'cobra'), VoiceMode('gagarin21', 'gagarin21'),
        ]
        self.music_modes = [MusicMode('default', 'default'), MusicMode('offspring', 'offspringArenaMusic')]
        super(ConfigInterface, self).__init__()

    def init(self):
        self.ID = '%(mod_ID)s'
        self.version = '1.1.2 (%(file_compile_date)s)'
        self.data = {'enabled': True, 'voice': 0, 'music': 0}
        # noinspection SpellCheckingInspection
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
            'UI_setting_voice_celebrity2021_ru': 'Chuck Norris (RU)',
            'UI_setting_voice_celebrity2021_en': 'Chuck Norris (EN)',
            'UI_setting_voice_racer_ru': 'Racer (RU)',
            'UI_setting_voice_racer_en': 'Racer (EN)',
            'UI_setting_voice_gup_jp_commander': 'GUP: Commander',
            'UI_setting_voice_gup_jp_crew': 'GUP: Full crew',
            'UI_setting_voice_duke': 'G.I.Joe: Duke',
            'UI_setting_voice_cobra': 'G.I.Joe: Cobra',
            'UI_setting_voice_gagarin21': 'Space-21: Gagarin',
            'UI_setting_voice_20_LeBwa': 'RU-20: LeBwa',
            'UI_setting_voice_20_Yusha': 'RU-20: Yusha',
            'UI_setting_voice_20_Amway921': 'RU-20: Amway921',
            'UI_setting_voice_20_KorbenDallas': 'RU-20: KorbenDallas',
            'UI_setting_voice_20_Mailand': 'EU-20: Mailand',
            'UI_setting_voice_20_Skill4ltu': 'EU-20: Skill4ltu',
            'UI_setting_voice_20_Dezgamez': 'EU-20: Dezgamez',
            'UI_setting_voice_20_AwesomeEpicGuys': 'EU-20: AwesomeEpicGuys',
            'UI_setting_voice_21_Yusha': 'RU-21: Yusha',
            'UI_setting_voice_21_Vspishka': 'RU-21: Vspishka',
            'UI_setting_voice_21_Amway921': 'RU-21: Amway921',
            'UI_setting_voice_21_KorbenDallas': 'RU-21: KorbenDallas',
            'UI_setting_voice_21_LeBwa': 'RU-21: LeBwa',
            'UI_setting_voice_21_Inspirer': 'RU-21: Inspirer',
            'UI_setting_voice_21_Evil_Granny': 'RU-21: Evil_Granny',
            'UI_setting_voice_21_Near_You': 'RU-21: Near_You',
            'UI_setting_voice_21_Circon': 'EU-21: Circon',
            'UI_setting_voice_21_Dakillzor': 'EU-21: Dakillzor',
            'UI_setting_voice_21_Newmulti2k': 'EU-21: Newmulti2k',
            'UI_setting_voice_21_Orzanel': 'EU-21: Orzanel',
            'UI_setting_voice_21_CabMech': 'NA-21: CabMech',
            'UI_setting_voice_21_TragicLoss': 'NA-21: TragicVeLOSSiraptor',
            'UI_setting_voice_21_Cmdr_AF': 'NA-21: Cmdr_AF',
            'UI_setting_voice_21_MasterTortoise': 'ASIA-21: MasterTortoise: Kame',
            'UI_setting_voice_21_SummerTiger': 'ASIA-21: SummerTiger: Summer',
            'UI_setting_voice_21_Maharlika': 'ASIA-21: Maharlika: Conan',
        }
        super(ConfigInterface, self).init()

    def createTemplate(self):
        return {
            'modDisplayName': self.i18n['name'],
            'enabled': self.data['enabled'],
            'column1': [
                self.tb.createOptions(
                    'voice', [self.i18n['UI_setting_voice_%s' % mode.name] for mode in self.voice_modes],
                    button={'iconSource': '../maps/icons/buttons/sound.png'}),
            ],
            'column2': [
                self.tb.createOptions(
                    'music', [self.i18n['UI_setting_music_%s' % mode.name] for mode in self.music_modes]),
            ]}

    def onButtonPress(self, vName, value):
        if vName != 'voice':
            return
        self.data[vName] = int(value)
        self.playPreviewSound()

    def onMSADestroy(self):
        self.readData()
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
        if self.voice_modes[self.data['voice']].national:
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
        mode = self.voice_modes[self.data['voice']]
        soundModes = SoundGroups.g_instance.soundModes
        if mode.languageMode is not None:
            return soundModes.setMode(mode.languageMode)
        gender = SoundGroups.CREW_GENDER_SWITCHES.GENDER_ALL[mode.female]
        soundModes.setCurrentNation(nation or soundModes.DEFAULT_NATION, gender)
        if mode.national:
            return soundModes.setNationalMappingByPreset('NationalDefault')
        return soundModes.setNationalMappingByMode('default')


g_config = ConfigInterface()
analytics = Analytics(g_config.ID, g_config.version, 'UA-76792179-22')


@overrideMethod(SpecialSoundCtrl, 'setPlayerVehicle')
def new_setPlayerVehicle(base, self, vehiclePublicInfo, isPlayerVehicle):
    base(self, vehiclePublicInfo, isPlayerVehicle)
    arena = avatar_getter.getArena()
    if not g_config.data['enabled'] or arena is None:
        return
    g_config.setSystemValue(nations.NAMES[VehicleDescr(vehiclePublicInfo.compDescr).type.id[0]])
    self._SpecialSoundCtrl__arenaMusicSetup = musicSetup = arena.arenaType.wwmusicSetup.copy()
    tag = g_config.music_modes[g_config.data['music']].tag
    musicSetup.update(self._SpecialSoundCtrl__arenaMusicByStyle.get(tag, ()))
