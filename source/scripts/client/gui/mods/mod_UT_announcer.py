# -*- coding: utf-8 -*-
# noinspection SpellCheckingInspection
"""
for 0.9.12 fixed by webium, all credits goes to locastan
for 0.9.14 fixed by Oldskool & Budyx69, all credits goes to locastan
for 0.9.15.1.1 fixed by Budyx69 & Grumpelumpf thx to Krzysztof_Chodak for Textmessage Code
last change 2016-10-12 for 0.9.16 budyx69

russian version by Polyacov_Yury, multiple fixes by Andre_V/Ekspoint
final version by Polyacov_Yury
"""
import BigWorld
import ResMgr
import SoundGroups
import os
import traceback
from PYmodsCore import PYmodsConfigInterface, Analytics, overrideMethod, events
from collections import OrderedDict
from constants import ARENA_PERIOD, ARENA_GUI_TYPE
from debug_utils import LOG_ERROR
from functools import partial
from gui import IngameSoundNotifications
from gui.Scaleform.daapi.view.battle.classic.battle_end_warning_panel import BattleEndWarningPanel
from gui.Scaleform.daapi.view.meta import DamagePanelMeta
from gui.shared.personality import ServicesLocator
from string import Template


class ConfigInterface(PYmodsConfigInterface):
    def __init__(self):
        self.timerSounds = ('sndStart', 'snd5min', 'snd3min', 'snd2min', 'snd1min', 'snd30sec', 'snd10sec', 'snd5sec',
                            'sndFinish')
        self.colours = OrderedDict([
            ('UI_color_red', '#FF0000'), ('UI_color_nice_red', '#FA8072'), ('UI_color_chocolate', '#D3691E'),
            ('UI_color_orange', '#FFA500'), ('UI_color_gold', '#FFD700'), ('UI_color_cream', '#FCF5C8'),
            ('UI_color_yellow', '#FFFF00'), ('UI_color_green_yellow', '#ADFF2E'), ('UI_color_lime', '#00FF00'),
            ('UI_color_green', '#008000'), ('UI_color_aquamarine', '#2AB157'), ('UI_color_emerald', '#28F09C'),
            ('UI_color_cyan', '#00FFFF'), ('UI_color_cornflower_blue', '#6595EE'), ('UI_color_blue', '#0000FF'),
            ('UI_color_purple', '#800080'), ('UI_color_hot_pink', '#FF69B5'), ('UI_color_pink', '#FFC0CB'),
            ('UI_color_brown', '#A52A2B'),
            ('UI_color_wg_colorBlind', '#8378FC'), ('UI_color_wg_enemy', '#DB0400'), ('UI_color_wg_ally', '#80D639'),
            ('UI_color_wg_squadMan', '#FFB964'), ('UI_color_wg_player', '#FFE041')])
        self.sounds = {}
        super(ConfigInterface, self).__init__()

    def init(self):
        self.ID = '%(mod_ID)s'
        self.version = '2.4.2 (%(file_compile_date)s)'
        self.author += ' (orig by locastan)'
        # noinspection SpellCheckingInspection
        self.data = {'enabled': True, 'battleTimer': True, 'firstOption': 4, 'allKill': 2,
                     'checkMedals': 4, 'disStand': True, 'textLength': 3, 'textColour': 0, 'colourBlind': False,
                     'textLock': True, 'delay': 3, 'logging': True,
                     'sounds': {'firstBlood': 'firstblood', 'doubleKill': 'doublekill', 'tripleKill': 'triplekill',
                                'ultraKill': 'ultrakill', 'multiKill': 'multikill', 'monsterKill': 'monsterkill',
                                'killingSpree': 'killingspree', 'rampage': 'rampage', 'unstoppable': 'unstoppable',
                                'godlike': 'godlike', 'stormTech': 'massacre', 'jackHammer': 'megakill',
                                'combine': 'flakmaster', 'perforator': 'topgun', 'eagleEye': 'unreal',
                                'kamikaze': 'kamikaze', 'bia': 'eradication', 'crucial': 'extermination',
                                'ramKill': 'ramkill', 'payback': 'payback', 'denied': 'denied', 'sndStart': '',
                                'snd5min': 't5min', 'snd3min': 't3min', 'snd2min': '', 'snd1min': 't1min',
                                'snd30sec': 't30secs', 'snd10sec': '', 'snd5sec': 't5secs', 'sndFinish': ''},
                     'textStyle': {'colour': '#2AB157', 'size': 25, 'font': '$FieldFont'},
                     'textPosition': {'alignX': 'center', 'alignY': 'top', 'x': 0, 'y': 120},
                     'textBackground': {'enabled': True, 'width': 530, 'height': 32,
                                        'image': '../../scripts/client/gui/mods/mod_UT_announcer.png'},
                     'textShadow': {'enabled': True, 'alpha': 1, 'angle': 90, 'color': '#000000',
                                    'distance': 0, 'blurX': 2, 'blurY': 2, 'strength': 2, 'quality': 2}}
        self.i18n = {
            'UI_description': 'Time and frags announcer',
            'UI_setting_textColour_text': 'Battle text messages colour',
            'UI_setting_textColour_tooltip': 'This colour will be applied to all mod\'s text messages.\nText examples:\n',
            'UI_setting_textLength_text': 'Number of lines of in-battle text messages',
            'UI_setting_textLength_tooltip': (
                'This is the maximum number of lines of text messages you will see in battle simultaneously.\n'
                '<b>0</b> completely disables the text messages.'),
            'UI_setting_colourBlind_text': 'Enable "colour blindness" mode',
            'UI_setting_colourBlind_tooltip': 'This setting changes the enemy text colour from red to purple.',
            'UI_setting_textLock_text': 'Disable text mouse dragging',
            'UI_setting_textLock_tooltip': (
                'This setting controls whether you are able to move text window with a mouse or not.'),
            'UI_setting_logging_text': 'Enable full logging',
            'UI_setting_logging_tooltip': 'Allow the mod to overflow your python.log with debug information.',
            'UI_setting_battleTimer_text': 'Enable voice notifications about battle time',
            'UI_setting_battleTimer_tooltip': (
                'Enables voice notification about remaining time in battle:'
                '\n • 15 minutes remaining (battle start);\n • 5 minutes remaining;\n • 3 minutes remaining;'
                '\n • 2 minutes remaining;\n • 1 minute remaining;\n • 30 seconds remaining;\n • 10 seconds remaining;'
                '\n • 5 seconds countdown;\n • Battle is over.'),
            'UI_setting_firstOption_text': 'First Blood notification mode',
            'UI_setting_firstOption_tooltip': (
                ' • <b>First</b> - only the first First Blood on arena will be notified.\n • <b>Player</b> - text message '
                'only appears if you drew the First Blood.\n • <b>Ally</b> - only the First Blood drown by allies and '
                'player will be notified.\n • <b>Enemy</b> - only the First Blood drown by enemies will be notified.\n'
                ' • <b>All</b> - both ally and enemy First Bloods will be notified.'),
            'UI_setting_firstOption_first': 'First',
            'UI_setting_firstOption_player': 'Player',
            'UI_setting_firstOption_ally': 'Ally',
            'UI_setting_firstOption_enemy': 'Enemy',
            'UI_setting_firstOption_all': 'All',
            'UI_setting_checkMedals_text': 'Notify about frag-related medals like Pool or Radley-Walters',
            'UI_setting_checkMedals_tooltip': (
                ' • <b>OFF</b> - medal notification disabled.\n • <b>Player</b> - only '
                'medals received by player will be notified.\n • <b>Ally</b> - only medals received by allies and player '
                'will be notified.\n • <b>Enemy</b> - only medals received by enemies will be notified.\n • <b>All</b> - '
                'all frag-related medals on arena will be notified.'),
            'UI_setting_checkMedals_none': 'OFF',
            'UI_setting_checkMedals_player': 'Player',
            'UI_setting_checkMedals_ally': 'Ally',
            'UI_setting_checkMedals_enemy': 'Enemy',
            'UI_setting_checkMedals_all': 'All',
            'UI_setting_allKill_text': 'Other players\' frag sound notifying',
            'UI_setting_allKill_tooltip': (
                ' • <b>None</b> - only player frags are sounded.\n • <b>Bigger</b> - all frag capacities which are bigger '
                'than player\'s are sounded.\n • <b>All</b> - all frag capacities on arena are sounded.'),
            'UI_setting_allKill_none': 'None',
            'UI_setting_allKill_bigger': 'Bigger',
            'UI_setting_allKill_every': 'All',
            'UI_setting_disStand_text': 'Disable default frag sound notifications',
            'UI_setting_disStand_tooltip': (
                'Disable default notifications about frags so that they do not overlap on modded sounds.'),
            'UI_setting_delay_text': 'Time before text message disappears',
            'UI_setting_delay_tooltip': 'Text message remains on screen for this amount of seconds before fading out.',
            'UI_setting_delay_seconds': 'sec.',
            'UI_setting_ally': 'Ally', 'UI_setting_enemy': 'Enemy', 'UI_setting_player': 'Player',
            'UI_setting_squadMan': 'Squadman',
            'UI_message_vehicleDestroyed': 'Player vehicle destroyed!',
            'UI_message_firstBlood': '$attacker drew First Blood!',
            'UI_message_firstBlood_ally': '$attacker killed first enemy!',
            'UI_message_firstBlood_enemy': '$attacker killed first ally!',
            'UI_message_bia': '$attacker scored us Brothers in Arms!',
            'UI_message_denied': 'Brothers in Arms denied by $attacker ($target was drown)!',
            'UI_message_payback': '$attacker avenged $squadMan!',
            'UI_message_payback_own': '$squadMan avenged your death!',
            'UI_message_crucial': '$attacker scored us Crucial Contribution!',
            'UI_message_kamikaze': 'Kamikaze!',
            'UI_message_ramKill': 'Ram kill!',
            'UI_message_frags_5': '$attacker is about to get Warrior award!',
            'UI_message_frags_6': '$attacker just got Warrior award!',
            'UI_message_frags_7': '$attacker is about to get Radley-Walters award!',
            'UI_message_frags_8': '$attacker just got Radley-Walters award!',
            'UI_message_frags_9': '$attacker is about to get Pool award!',
            'UI_message_frags_10': '$attacker just got Pool award!',
            'UI_message_frags_13': '$attacker is about to get Raseiniai award!',
            'UI_message_frags_14': '$attacker just got Raseiniai award!',
            'UI_color_red': 'Red', 'UI_color_nice_red': 'Nice red', 'UI_color_chocolate': 'Chocolate',
            'UI_color_orange': 'Orange', 'UI_color_gold': 'Gold', 'UI_color_cream': 'Cream', 'UI_color_yellow': 'Yellow',
            'UI_color_green_yellow': 'Green yellow', 'UI_color_lime': 'Lime', 'UI_color_green': 'Green',
            'UI_color_aquamarine': 'Aquamarine', 'UI_color_emerald': 'Emerald', 'UI_color_cyan': 'Cyan',
            'UI_color_cornflower_blue': 'Cornflower blue', 'UI_color_blue': 'Blue', 'UI_color_purple': 'Purple',
            'UI_color_hot_pink': 'Hot pink', 'UI_color_pink': 'Pink', 'UI_color_brown': 'Brown',
            'UI_color_wg_colorBlind': 'WG Color blind', 'UI_color_wg_enemy': 'WG Enemy', 'UI_color_wg_ally': 'WG Ally',
            'UI_color_wg_squadMan': 'WG Squadman', 'UI_color_wg_player': 'WG Player'}
        super(ConfigInterface, self).init()

    def createTemplate(self):
        textExamples = []
        for key in ('UI_message_firstBlood_ally', 'UI_message_firstBlood_enemy', 'UI_message_payback'):
            isPlayer = {'attacker': 'firstBlood' not in key, 'target': False}
            isAlly = {'attacker': 'ally' in key, 'target': 'enemy' in key}
            names = dict((key, self.i18n['UI_setting_player'] if isPlayer[key] else self.i18n['UI_setting_ally'] if isAlly[
                key] else self.i18n['UI_setting_enemy']) for key in ('attacker', 'target'))
            names['squadMan'] = self.i18n['UI_setting_squadMan'] if 'firstBlood' not in key else ''
            textFormat = self.formatText(self.i18n[key], isPlayer, isAlly, {'attacker': False, 'target': False}, names)
            text = '<font size="%s" face="%s" color="%s"><p align="center">%s</p></font>' % (
                self.data['textStyle']['size'], self.data['textStyle']['font'],
                self.data['textStyle']['colour'], textFormat)
            textExamples.append(text)
        colourDropdown = self.tb.createOptions(
            'textColour', ('<font color="%s">%s</font>' % (x[1], self.i18n[x[0]]) for x in self.colours.iteritems()))
        colourDropdown['tooltip'] = colourDropdown['tooltip'].replace('{/BODY}', '\n'.join(textExamples) + '{/BODY}')
        firstKey = 'UI_setting_firstOption_'
        firstList = ('first', 'player', 'ally', 'enemy', 'all')
        medalsKey = 'UI_setting_checkMedals_'
        medalsList = ('none', 'player', 'ally', 'enemy', 'all')
        allKey = 'UI_setting_allKill_'
        allList = ('none', 'bigger', 'every')
        return {'modDisplayName': self.i18n['UI_description'],
                'enabled': self.data['enabled'],
                'column1': [self.tb.createStepper('textLength', 0, 5, 1),
                            colourDropdown,
                            self.tb.createControl('colourBlind'),
                            self.tb.createControl('textLock'),
                            self.tb.createSlider('delay', 0, 5, 0.1, '{{value}} ' + self.i18n['UI_setting_delay_seconds']),
                            self.tb.createControl('logging')],
                'column2': [self.tb.createOptions('firstOption', [self.i18n[firstKey + x] for x in firstList]),
                            self.tb.createOptions('checkMedals', [self.i18n[medalsKey + x] for x in medalsList]),
                            self.tb.createOptions('allKill', [self.i18n[allKey + x] for x in allList]),
                            self.tb.createControl('battleTimer'),
                            self.tb.createControl('disStand')]}

    def onApplySettings(self, settings):
        self.data['textStyle']['colour'] = self.colours.values()[settings['textColour']]
        super(ConfigInterface, self).onApplySettings(settings)
        if flashController is not None:
            flashController.onApplySettings()

    def readData(self, quiet=True):
        super(ConfigInterface, self).readData(quiet)
        colour = self.data['textStyle']['colour']
        colours = self.colours.values()
        self.data['textColour'] = colours.index(colour) if colour in colours else 10
        self.data['textStyle']['colour'] = self.colours.values()[self.data['textColour']]

    def formatText(self, newText, isPlayer, isAlly, isSquadMan, names):
        colors = dict(
            (key, 'player' if isPlayer[key] else 'squadMan' if isSquadMan[key] else 'ally' if isAlly[key] else 'colorBlind'
             if self.data['colourBlind'] else 'enemy') for key in ('attacker', 'target'))
        colors['squadMan'] = 'squadMan'
        try:
            assert names
            for role in names:
                name = names[role].decode('utf-8').split('[')[0]
                names[role] = (name[:13] + (name[13:] and '..')).encode('utf-8')
                if names[role]:
                    names[role] = "<font color='%s'>%s</font>" % (self.colours['UI_color_wg_' + colors[role]], names[role])
            result = Template(newText).safe_substitute(**names)
        except AssertionError:
            result = 'Welcome back!'
        except StandardError:
            result = 'Welcome back!'
            traceback.print_exc()
        return result


class FlashController(object):
    def __init__(self, ID):
        self.ID = ID
        self.texts = []
        self.callbacks = []
        self.isTextAdding = False
        self.isTextRemoving = False
        self.setup()
        COMPONENT_EVENT.UPDATED += self.__updatePosition

    def __updatePosition(self, alias, data):
        if alias != self.ID:
            return
        _config.onApplySettings({'textPosition': data, 'textColour': _config.data['textColour']})

    def onApplySettings(self):
        g_guiFlash.updateComponent(self.ID, dict(
            _config.data['textPosition'], drag=not _config.data['textLock'], border=not _config.data['textLock']))

    def setup(self):
        bgPath = _config.data['textBackground']['image']
        bgNormPath = os.path.normpath('gui/flash/' + bgPath).replace(os.sep, '/')
        bgSect = ResMgr.openSection(bgNormPath)
        if bgSect is None:
            LOG_ERROR('Battle text background file not found: ' + bgNormPath)
        self.texts = []
        g_guiFlash.createComponent(self.ID, COMPONENT_TYPE.PANEL, dict(
            _config.data['textPosition'], drag=not _config.data['textLock'], border=not _config.data['textLock'], limit=True))
        self.createBox(0)

    def createBox(self, idx):
        bgConf = _config.data['textBackground']
        bgAltPath = '../maps/bg.png'
        bgPath = bgConf['image']
        width, height = bgConf['width'], bgConf['height']
        y = height * idx
        g_guiFlash.createComponent(self.ID + '.text%s' % idx, COMPONENT_TYPE.LABEL, {
            'text': '', 'width': width, 'height': height, 'alpha': 0.0, 'x': 0, 'y': y,
            'alignX': COMPONENT_ALIGN.CENTER, 'alignY': COMPONENT_ALIGN.TOP})
        shadow = _config.data['textShadow']
        if shadow['enabled']:
            g_guiFlash.updateComponent(self.ID + '.text%s' % idx, {'shadow': shadow})
        g_guiFlash.createComponent(self.ID + '.image%s' % idx, COMPONENT_TYPE.IMAGE, {
            'image': bgPath, 'imageAlt': bgAltPath, 'width': width, 'height': height, 'alpha': 0.0,
            'x': 0, 'y': y + 2, 'alignX': COMPONENT_ALIGN.CENTER, 'alignY': COMPONENT_ALIGN.TOP})

    def removeBox(self, idx):
        g_guiFlash.deleteComponent(self.ID + '.text%s' % idx)
        g_guiFlash.deleteComponent(self.ID + '.image%s' % idx)

    def addText(self, text):
        if not (_config.data['enabled'] and _config.data['textLength']):
            return
        if self.isTextAdding:
            BigWorld.callback(0.1, partial(self.addText, text))
            return
        LOG_NOTE('adding text: ' + text)
        styleConf = _config.data['textStyle']
        text = '<font size="%s" face="%s" color="%s"><p align="center">%s</p></font>' % (
            styleConf['size'], styleConf['font'], styleConf['colour'], text)
        if len(self.texts) == _config.data['textLength']:
            self.removeFirstText()
        idx = len(self.texts)
        self.texts.append(text)
        if idx:
            self.createBox(idx)
        g_guiFlash.updateComponent(self.ID + '.text%s' % idx, {'text': text})
        g_guiFlash.updateComponent(self.ID + '.text%s' % idx, {'alpha': 1.0}, {'duration': 0.5})
        if _config.data['textBackground']['enabled']:
            g_guiFlash.updateComponent(self.ID + '.image%s' % idx, {'alpha': 1.0}, {'duration': 0.5})
        self.isTextAdding = True
        BigWorld.callback(0.5, self.onTextAddingComplete)
        self.callbacks.append(BigWorld.callback(_config.data['delay'] + 0.5, self.removeFirstText))

    def onTextAddingComplete(self):
        self.isTextAdding = False

    def onTextRemovalComplete(self):
        self.isTextRemoving = False
        bgConf = _config.data['textBackground']
        height = bgConf['height']
        for idx in xrange(len(self.texts)):
            y = height * idx
            g_guiFlash.updateComponent(self.ID + '.text%s' % idx, {'text': self.texts[idx], 'alpha': 1.0, 'y': y})
            if bgConf['enabled']:
                g_guiFlash.updateComponent(self.ID + '.image%s' % idx, {'alpha': 1.0, 'y': y + 2})
        idx = len(self.texts)
        if idx:
            self.removeBox(idx)

    def removeFirstText(self):
        if self.isTextRemoving:
            BigWorld.callback(0.1, self.removeFirstText)
            return
        if self.texts:
            LOG_NOTE('removing first text')
            del self.texts[0]
        if self.callbacks:
            try:
                BigWorld.cancelCallback(self.callbacks[0])
            except ValueError:
                pass
            except StandardError:
                traceback.print_exc()
            del self.callbacks[0]
        self.isTextRemoving = True
        bgConf = _config.data['textBackground']
        g_guiFlash.updateComponent(self.ID + '.text0', {'alpha': 0.0}, {'duration': 0.5})
        g_guiFlash.updateComponent(self.ID + '.image0', {'alpha': 0.0}, {'duration': 0.5})
        for idx in xrange(1, len(self.texts) + 1):
            g_guiFlash.updateComponent(self.ID + '.text%s' % idx, {'y': bgConf['height'] * (idx - 1)}, {'duration': 0.5})
            if bgConf['enabled']:
                g_guiFlash.updateComponent(self.ID + '.image%s' % idx, {'y': bgConf['height'] * (idx - 1)}, {'duration': 0.5})
        BigWorld.callback(0.5, self.onTextRemovalComplete)


flashController = None
_config = ConfigInterface()
statistic_mod = Analytics(_config.ID, _config.version, 'UA-76792179-8')
try:
    from gambiter import g_guiFlash
    from gambiter.flash import COMPONENT_TYPE, COMPONENT_ALIGN, COMPONENT_EVENT

    flashController = FlashController(_config.ID)
except ImportError:
    g_guiFlash = COMPONENT_TYPE = COMPONENT_ALIGN = COMPONENT_EVENT = None
    LOG_ERROR('gambiter.GUIFlash not found. Text viewing disabled.')
except StandardError:
    g_guiFlash = COMPONENT_TYPE = COMPONENT_ALIGN = COMPONENT_EVENT = None
    traceback.print_exc()


class SoundManager(object):
    def __init__(self):
        self.isPlayingSound = False
        self.queue = []

    def addToQueue(self, event):
        self.queue.append(event)
        self.playFirstEvent()

    def playFirstEvent(self):
        if not self.queue:
            return
        if self.isPlayingSound:
            BigWorld.callback(0.1, self.playFirstEvent)
            return
        eventName = self.queue.pop(0)
        if eventName not in _config.sounds:
            self.playFirstEvent()
            return
        if _config.sounds[eventName].isPlaying:
            _config.sounds[eventName].stop()
        LOG_NOTE(eventName + ' playing')
        _config.sounds[eventName].play()
        self.isPlayingSound = True
        BigWorld.callback(0.6, self.onSoundPlayed)

    def onSoundPlayed(self):
        self.isPlayingSound = False
        self.playFirstEvent()


soundMgr = SoundManager()


def LOG_NOTE(msg, *args):
    if _config.data['logging']:
        print _config.ID + ':', msg, (('(%s)' % ', '.join('%s' % arg for arg in args)) if args else '')


def killCheck(frags):
    # noinspection SpellCheckingInspection
    options = {2: 'doubleKill', 3: 'tripleKill', 4: 'ultraKill', 5: 'multiKill', 6: 'monsterKill', 7: 'killingSpree',
               8: 'rampage', 9: 'unstoppable', 10: 'godlike', 11: 'stormTech', 12: 'jackHammer', 13: 'combine',
               14: 'perforator', 15: 'eagleEye',
               20: 'ramKill', 30: 'kamikaze', 40: 'bia', 50: 'crucial', 60: 'denied', 70: 'payback'}
    if frags in options:
        soundMgr.addToQueue(options[frags])


def initial():
    BigWorld.player().arena.UT = {
        'squadMan': [0, 0], 'killer': [0, 0], 'ownKiller': 0, 'BiA': False, 'Crucial': False, 'BiAFail': False}


def checkSquadMan():
    if 'opponents' in BigWorld.player().arena.extraData:
        return
    ownID = BigWorld.player().playerVehicleID
    ownSquadID = BigWorld.player().arena.vehicles[ownID]['prebattleID']
    if ownSquadID and not all(BigWorld.player().arena.UT['squadMan']):
        for vehicleID, vehicle in BigWorld.player().arena.vehicles.iteritems():
            if vehicle['prebattleID'] == ownSquadID and vehicleID != ownID:
                if not BigWorld.player().arena.UT['squadMan'][0]:
                    BigWorld.player().arena.UT['squadMan'][0] = vehicleID
                elif not BigWorld.player().arena.UT['squadMan'][1]:
                    BigWorld.player().arena.UT['squadMan'][1] = vehicleID


def callTextInit(newText, targetID, attackerID, squadManID):
    arena = BigWorld.player().arena
    LOG_NOTE('text init:', newText, targetID, attackerID, squadManID)
    isPlayer = {'attacker': attackerID == BigWorld.player().playerVehicleID,
                'target': targetID == BigWorld.player().playerVehicleID}
    isAlly = {'attacker': arena.vehicles[attackerID]['team'] == BigWorld.player().team,
              'target': arena.vehicles[targetID]['team'] == BigWorld.player().team}
    isSquadMan = {'attacker': attackerID in arena.UT['squadMan'],
                  'target': targetID in arena.UT['squadMan']}
    try:
        names = {'attacker': arena.vehicles[attackerID]['name'],
                 'target': arena.vehicles[targetID]['name'],
                 'squadMan': arena.vehicles[squadManID]['name'] if squadManID else ''}
    except StandardError:
        names = {}
        traceback.print_exc()
    text = _config.formatText(newText, isPlayer, isAlly, isSquadMan, names)
    battle = ServicesLocator.appLoader.getDefBattleApp()
    if battle is not None and flashController is not None:
        flashController.addText(text)


def checkSquadKills(targetID, attackerID, reason):
    arena = BigWorld.player().arena
    LOG_NOTE('Check Squad Kills:', targetID, attackerID, reason)
    cStats = arena._ClientArena__statistics
    if not arena.vehicles[BigWorld.player().playerVehicleID]['prebattleID'] or 'opponents' in arena.extraData or not \
            arena.UT['squadMan'][0]:
        LOG_NOTE('Player not in a Platoon. Returning.')
        firstCheck(targetID, attackerID, reason, True, None)
        return
    else:
        squadFrags = cStats[BigWorld.player().playerVehicleID]['frags'] + cStats[arena.UT['squadMan'][0]]['frags']
        if arena.UT['squadMan'][1]:
            squadFrags += cStats[arena.UT['squadMan'][1]]['frags']
        LOG_NOTE('Squad frags:', squadFrags)
        if squadFrags >= 12:
            LOG_NOTE('Squad frags >= 12')
            if not arena.UT['Crucial']:
                callTextInit(_config.i18n['UI_message_crucial'], targetID, attackerID, None)
                LOG_NOTE('Crucial detected!')
                arena.UT['Crucial'] = True
                killCheck(50)
            else:
                LOG_NOTE('Crucial already achieved.')
        if not arena.UT['BiA'] and not arena.UT['BiAFail']:
            if cStats[BigWorld.player().playerVehicleID]['frags'] >= 3 and cStats[arena.UT['squadMan'][0]]['frags'] >= 3:
                LOG_NOTE('Two Platoon mates have each minimum 3 kills.')
                if not arena.UT['squadMan'][1] or cStats[arena.UT['squadMan'][1]]['frags'] >= 3:
                    callTextInit(_config.i18n['UI_message_bia'], targetID, attackerID, None)
                    LOG_NOTE('BiA detected (%s Man platoon).' % (len(filter(None, arena.UT['squadMan'])) + 1))
                    arena.UT['BiA'] = True
                    killCheck(40)
                else:
                    LOG_NOTE('SquadMan 2 not 3 kills.')
            else:
                LOG_NOTE('Player or SquadMan 1 not 3 kills.')
        else:
            LOG_NOTE('Squad check complete.')
        firstCheck(targetID, attackerID, reason, True, None)


def firstCheck(targetID, attackerID, reason, squadChecked, killerID):
    player = BigWorld.player()
    arena = player.arena
    if not hasattr(arena, 'firstBloods'):
        arena.firstBloods = {'notFirst': False, 'player': False, 'ally': False, 'enemy': False}
    if attackerID not in arena.vehicles:
        if targetID == player.playerVehicleID and flashController is not None:
            flashController.addText(_config.i18n['UI_message_vehicleDestroyed'])
        return
    attacker = {'vehicle': arena.vehicles[attackerID], 'isPlayer': attackerID == player.playerVehicleID,
                'isSquadMan': attackerID in arena.UT['squadMan']}
    attacker['isAlly'] = attacker['vehicle']['team'] == player.team
    target = {'vehicle': arena.vehicles[targetID]}
    target['isAlly'] = target['vehicle']['team'] == player.team
    if attackerID != targetID and attacker['isAlly'] != target['isAlly'] and not all(arena.firstBloods.values()):
        if not _config.data['firstOption']:
            if not arena.firstBloods['notFirst']:
                arena.firstBloods['ally'] = arena.firstBloods['enemy'] = True
                arena.firstBloods['player'] = attacker['isPlayer']
                callTextInit(_config.i18n['UI_message_firstBlood'], targetID, attackerID, None)
                soundMgr.addToQueue('firstBlood')
            elif not arena.firstBloods['player'] and attacker['isPlayer']:
                arena.firstBloods['player'] = True
                soundMgr.addToQueue('firstBlood')
        elif _config.data['firstOption'] == 1:
            arena.firstBloods['ally'] = arena.firstBloods['enemy'] = True
            if not arena.firstBloods['player'] and attacker['isPlayer']:
                arena.firstBloods['player'] = True
                if not arena.firstBloods['notFirst']:
                    callTextInit(_config.i18n['UI_message_firstBlood'], targetID, attackerID, None)
                soundMgr.addToQueue('firstBlood')
        elif _config.data['firstOption'] >= 2:
            if not attacker['isAlly']:
                if _config.data['firstOption'] != 2:
                    if not arena.firstBloods['enemy']:
                        arena.firstBloods['enemy'] = True
                        callTextInit(_config.i18n['UI_message_firstBlood_enemy'], targetID, attackerID, None)
                        soundMgr.addToQueue('firstBlood')
                else:
                    arena.firstBloods['enemy'] = True
            if attacker['isAlly'] and not attacker['isPlayer']:
                if _config.data['firstOption'] != 3:
                    if not arena.firstBloods['ally']:
                        arena.firstBloods['ally'] = True
                        callTextInit(_config.i18n['UI_message_firstBlood_ally'], targetID, attackerID, None)
                        soundMgr.addToQueue('firstBlood')
                else:
                    arena.firstBloods['ally'] = True
            if attacker['isPlayer'] and not arena.firstBloods['player']:
                if not arena.firstBloods['ally']:
                    callTextInit(_config.i18n['UI_message_firstBlood'], targetID, attackerID, None)
                arena.firstBloods['player'] = arena.firstBloods['ally'] = True
                soundMgr.addToQueue('firstBlood')
        arena.firstBloods['notFirst'] = True
    if killerID is not None:
        LOG_NOTE('Player died to:', killerID)
        arena.UT['BiAFail'] = True
        if arena.UT['BiA']:
            callTextInit(_config.i18n['UI_message_denied'], targetID, killerID, None)
            LOG_NOTE('BiA denied: Player died.')
            arena.UT['BiA'] = False
            killCheck(60)
    if targetID in arena.UT['squadMan']:
        squadManIdx = arena.UT['squadMan'].index(targetID)
        arena.UT['killer'][squadManIdx] = attackerID
        LOG_NOTE('SquadMan %s died. Killer ID: %s' % (squadManIdx + 1, attackerID))
        arena.UT['BiAFail'] = True
        if arena.UT['BiA']:
            callTextInit(_config.i18n['UI_message_denied'], targetID, attackerID, None)
            LOG_NOTE('BiA denied: SquadMan %s died.' % (squadManIdx + 1))
            arena.UT['BiA'] = False
            killCheck(60)
    if attacker['isAlly'] == target['isAlly']:
        LOG_NOTE('Team kill. No need to do more.')
        return
    if (attacker['isPlayer'] or attacker['isSquadMan']) and not squadChecked:
        LOG_NOTE('Calling checkSquadKills function.')
        checkSquadKills(targetID, attackerID, reason)
        return
    if (attacker['isPlayer'] or attacker['isSquadMan']) and targetID in arena.UT['killer']:
        killerIdx = arena.UT['killer'].index(targetID)
        callTextInit(_config.i18n['UI_message_payback'], targetID, attackerID, arena.UT['squadMan'][killerIdx])
        LOG_NOTE('Payback detected for SquadMan %s!' % (killerIdx + 1), targetID, attackerID)
        killCheck(70)
    if attacker['isSquadMan'] and targetID == arena.UT['ownKiller']:
        squadManIdx = arena.UT['squadMan'].index(attackerID)
        callTextInit(_config.i18n['UI_message_payback_own'], targetID, attackerID, arena.UT['squadMan'][squadManIdx])
        LOG_NOTE('Payback for dead player detected from SquadMan %s!' % (squadManIdx + 1), targetID, attackerID)
        killCheck(70)
    if attacker['isPlayer'] and reason == 2:
        isKamikaze = attacker['vehicle']['vehicleType'].type.level < target['vehicle']['vehicleType'].type.level
        callTextInit(_config.i18n['UI_message_%s' % ('kamikaze' if isKamikaze else 'ramKill')], targetID, attackerID, None)
        LOG_NOTE(('Kamikaze' if isKamikaze else 'Ram kill') + ' detected!', targetID, attackerID)
        killCheck(30 if isKamikaze else 20)
    cStats = arena._ClientArena__statistics
    origFrags = frags = cStats.get(attackerID)['frags']
    if frags > 1:
        checkMedals = True
        if arena.guiType in (ARENA_GUI_TYPE.EPIC_RANDOM, ARENA_GUI_TYPE.EPIC_RANDOM_TRAINING):
            if frags in (7, 8, 9, 10):
                frags -= 2
            elif frags in (12, 13):
                frags -= 3
            elif frags in (20, 21):
                frags -= 7
            else:
                checkMedals = False
        if (_config.data['checkMedals'] and (
                attacker['isPlayer'] and _config.data['checkMedals'] != 3 or
                attacker['isAlly'] and not attacker['isPlayer'] and _config.data['checkMedals'] in (2, 4) or
                not attacker['isAlly'] and _config.data['checkMedals'] >= 3) and checkMedals and (
                    frags in (5, 6, 13, 14) or attacker['vehicle']['vehicleType'].level >= 5 and frags in (7, 8, 9, 10))):
            callTextInit(_config.i18n['UI_message_frags_%s' % frags], targetID, attackerID, None)
            LOG_NOTE('Calling Medal killCheck function.', targetID, attackerID)
            LOG_NOTE('Medal checked frags:', frags)
            killCheck(origFrags)
        elif attacker['isPlayer'] or _config.data['allKill'] and (
                _config.data['allKill'] == 2 or cStats[player.playerVehicleID]['frags'] <= origFrags):
            LOG_NOTE('Calling normal killCheck function.', targetID, attackerID)
            LOG_NOTE('frags:', origFrags)
            killCheck(origFrags)


def checkOwnKiller():
    if BigWorld.player().arena.killerCallBackId is not None:
        BigWorld.cancelCallback(BigWorld.player().arena.killerCallBackId)
    killerID = BigWorld.player().inputHandler.getKillerVehicleID()
    BigWorld.player().arena.UT['ownKiller'] = killerID
    targetID = BigWorld.player().playerVehicleID
    LOG_NOTE('Player died. Calling firstCheck with following:', targetID, killerID, 0, True, killerID)
    firstCheck(targetID, killerID, 0, True, killerID)


@events.PlayerAvatar.startGUI.after
def startBattle(self, *_, **__):
    self.arena.onVehicleKilled += onArenaVehicleKilled
    if not _config.data['enabled']:
        return
    LOG_NOTE('startBattle')
    for soundName in _config.sounds.keys():
        _config.sounds[soundName].stop()
        del _config.sounds[soundName]
    for soundName in _config.data['sounds'].keys():
        if _config.data['sounds'][soundName] and (soundName not in _config.timerSounds or _config.data['battleTimer']):
            _config.sounds[soundName] = SoundGroups.g_instance.getSound2D(_config.data['sounds'][soundName])


@events.PlayerAvatar.destroyGUI.before
def destroyBattle(self, *_, **__):
    self.arena.onVehicleKilled -= onArenaVehicleKilled


@overrideMethod(BattleEndWarningPanel, 'setTotalTime')
def new_setCurrentTimeLeft(base, self, totalTime):
    base(self, totalTime)
    if not _config.data['enabled']:
        return
    period = BigWorld.player().arena.period
    events_by_time = {897: 'sndStart', 300: 'snd5min', 180: 'snd3min', 120: 'snd2min', 60: 'snd1min',
                      30: 'snd30sec', 10: 'snd10sec', 5: 'snd5sec', 0: 'sndFinish'}
    if period == ARENA_PERIOD.BATTLE and totalTime in events_by_time and _config.data['battleTimer']:
        soundMgr.addToQueue(events_by_time[totalTime])


def onArenaVehicleKilled(victimID, killerID, _, reason):
    if not _config.data['enabled']:
        return
    if not hasattr(BigWorld.player().arena, 'UT'):
        initial()
    LOG_NOTE('A Vehicle got Killed (targetID, attackerID, reason):', victimID, killerID, reason)
    checkSquadMan()
    firstCheck(victimID, killerID, reason, False, None)


@overrideMethod(DamagePanelMeta.DamagePanelMeta, 'as_setVehicleDestroyedS')
def new_onVehicleDestroyed(base, self):
    if _config.data['enabled'] and not hasattr(BigWorld.player().arena, 'UT'):
        initial()
        checkSquadMan()
        BigWorld.player().arena.killerCallBackId = BigWorld.callback(0.5, checkOwnKiller)
    base(self)


@overrideMethod(IngameSoundNotifications.IngameSoundNotifications, '__readConfig')
def new_readConfig(base, self):
    base(self)
    if _config.data['enabled'] and _config.data['disStand']:
        eventsData = self._IngameSoundNotifications__events
        for eventName, event in eventsData.iteritems():
            if eventName in ('enemy_killed_by_player', 'enemy_killed'):
                for category in event:
                    event[category]['sound'] = ''

        self._IngameSoundNotifications__events = eventsData
