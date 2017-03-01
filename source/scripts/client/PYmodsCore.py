# -*- coding: utf-8 -*-
import binascii
import codecs
import json
import os
import random
import re
import threading
import traceback
import urllib
import urllib2
import zlib
from functools import partial

import ResMgr

import BigWorld
import Event
import Keys
from PlayerEvents import g_playerEvents
from constants import AUTH_REALM, DEFAULT_LANGUAGE
from debug_utils import LOG_CURRENT_EXCEPTION

res = ResMgr.openSection('../paths.xml')
sb = res['Paths']
vl = sb.values()[0]
if vl is not None and not hasattr(BigWorld, 'curCV'):
    BigWorld.curCV = vl.asString
if not hasattr(BigWorld, 'PMC_wasPrint'):
    BigWorld.PMC_wasPrint = True
    print 'Current PYmodsCore version: 2.2.0 (%(file_compile_date)s)'
MAX_CHAT_MESSAGE_LENGTH = 220


def pickRandomPart(variantList, lastRandId, doNext=False):
    if not len(variantList):
        return ['', -1]
    if len(variantList) > 1:
        if doNext:
            newId = lastRandId + 1
            if newId >= len(variantList) or newId < 0:
                newId = 0
        else:
            bLoop = True
            newId = 0
            while bLoop:
                newId = random.randrange(len(variantList))
                bLoop = newId == lastRandId

        return variantList[newId], newId
    return variantList[0], 0


def __splitMsg(msg):
    if len(msg) <= MAX_CHAT_MESSAGE_LENGTH:
        return msg, ''
    strPart = msg[:MAX_CHAT_MESSAGE_LENGTH]
    splitPos = strPart.rfind(' ')
    if splitPos == -1:
        splitPos = MAX_CHAT_MESSAGE_LENGTH
    return msg[:splitPos], msg[splitPos:]


def __sendMessagePart(msg, chanId):
    class PYmods_chat(object):
        from messenger.m_constants import PROTO_TYPE
        from messenger.proto import proto_getter

        def __init__(self):
            pass

        @proto_getter(PROTO_TYPE.BW_CHAT2)
        def proto(self):
            return None

    msg = msg.encode('utf-8')
    import BattleReplay
    if PYmods_chat.proto is None or BattleReplay.isPlaying():
        from messenger import MessengerEntry
        MessengerEntry.g_instance.gui.addClientMessage('OFFLINE: %s' % msg, True)
        return
    else:
        if chanId == 0:
            PYmods_chat.proto.arenaChat.broadcast(msg, 1)
        if chanId == 1:
            PYmods_chat.proto.arenaChat.broadcast(msg, 0)
        if chanId == 2:
            PYmods_chat.proto.unitChat.broadcast(msg, 1)


def sendChatMessage(fullMsg, chanId, delay):
    currPart, remains = __splitMsg(fullMsg)
    __sendMessagePart(currPart, chanId)
    if len(remains) == 0:
        return
    BigWorld.callback(delay / 1000.0, partial(sendChatMessage, remains, chanId))


def new_addItem(self, item):
    if 'PYmods_SM' in item._vo['message']['message']:
        item._vo['message']['message'] = item._vo['message']['message'].replace('PYmods_SM', '')
        item._vo['notify'] = False
        if item._settings:
            item._settings.isNotify = False
        return True
    else:
        return old_addItem(self, item)


def new_handleAction(self, model, typeID, entityID, actionName):
    from notification.settings import NOTIFICATION_TYPE
    if typeID == NOTIFICATION_TYPE.MESSAGE and re.match('https?://', actionName, re.I):
        BigWorld.wg_openWebBrowser(actionName)
    else:
        old_handleAction(self, model, typeID, entityID, actionName)


# noinspection PyGlobalUndefined
def PMC_hooks():
    global old_addItem, old_handleAction
    from notification.NotificationsCollection import NotificationsCollection
    old_addItem = NotificationsCollection.addItem
    NotificationsCollection.addItem = new_addItem
    from notification.actions_handlers import NotificationsActionsHandlers
    old_handleAction = NotificationsActionsHandlers.handleAction
    # noinspection PyUnresolvedReferences
    NotificationsActionsHandlers.handleAction = new_handleAction


BigWorld.callback(0.0, PMC_hooks)


def remDups(seq):  # Dave Kirby
    # Order preserving
    seen = set()
    return [x for x in seq if x not in seen and not seen.add(x)]


def sendMessage(text='', colour='Green', panel='Player'):
    from gui.Scaleform.framework import ViewTypes
    from gui.app_loader import g_appLoader
    """
    panel = 'Player', 'Vehicle', 'VehicleError'
    colour = 'Red', 'Purple', 'Green', 'Gold', 'Yellow', 'Self'
    """
    battle = g_appLoader.getDefBattleApp()
    battle_page = battle.containerManager.getContainer(ViewTypes.VIEW).getView()
    getattr(battle_page.components['battle%sMessages' % panel], 'as_show%sMessageS' % colour, None)(None, text)


def checkKeys(keys):
    if not keys:
        return False
    for key in keys:
        if isinstance(key, int) and not BigWorld.isKeyDown(key):
            return False
        if isinstance(key, list) and not any(BigWorld.isKeyDown(x) for x in key):
            return False

    return True


class _Config(object):
    onMSAPopulate = Event.Event()
    onMSAWindowClose = Event.Event()
    isMSAWindowOpen = False
    onButtonPress = Event.Event()

    def __init__(self, ID):
        self.ID = ID
        self.version = ''
        self.configPath = './mods/configs/PYmods/%s/' % self.ID
        self.langPath = '%si18n/' % self.configPath
        self.author = 'by Polyacov_Yury'
        self.defaultKeys = {}
        self.data = {}
        self.i18n = {}
        self.conf_changed = False
        self.lang = DEFAULT_LANGUAGE
        self.onMSAPopulate += self.update_settings
        self.onMSAWindowClose += self.onWindowClose

    def loadLang(self):
        newConfig = self.loadJson(self.lang, self.i18n, self.langPath)
        for setting in newConfig:
            if setting in self.i18n:
                self.i18n[setting] = newConfig[setting]

    def template_settings(self):
        return {}

    def updateMod(self):
        # noinspection PyUnresolvedReferences
        from gui.mods.vxSettingsApi import vxSettingsApi
        vxSettingsApi.updateMod('PYmodsGUI', self.ID, self.template_settings)

    def getLabel(self, varName, ctx='setting'):
        return self.i18n['UI_%s_%s_text' % (ctx, varName)]

    def createTooltip(self, varName, ctx='setting'):
        return ('{HEADER}%s{/HEADER}{BODY}%s{/BODY}' % tuple(
            self.i18n['UI_%s_%s_%s' % (ctx, varName, strType)] for strType in ('text', 'tooltip'))) if self.i18n.get(
            'UI_%s_%s_tooltip' % (ctx, varName), '') else ''

    def createLabel(self, varName, ctx='setting'):
        return {'type': 'Label', 'text': self.getLabel(varName, ctx), 'tooltip': self.createTooltip(varName, ctx)}

    def createControl(self, varName, contType='CheckBox', empty=False, button=None):
        result = self.createLabel(varName) if not empty else {}
        result.update({'type': contType, 'value': self.data[varName], 'varName': varName})
        if button is not None:
            result['button'] = button
        return result

    def createOptions(self, varName, options, contType='Dropdown', empty=False, width=200, button=None):
        result = self.createControl(varName, contType, empty, button)
        result.update({'width': width, 'itemRenderer': 'DropDownListItemRendererSound',
                       'options': map(lambda x: {'label': x}, options)})
        return result

    def createHotKey(self, varName, empty=False):
        result = self.createControl(varName, 'HotKey', empty)
        result['defaultValue'] = self.defaultKeys[varName]
        return result

    def _createNumeric(self, varName, contType, vMin=0, vMax=0, empty=False, button=None):
        result = self.createControl(varName, contType, empty, button)
        result.update({'minimum': vMin, 'maximum': vMax})
        return result

    def createStepper(self, varName, vMin, vMax, step, manual=False, empty=False, button=None):
        result = self._createNumeric(varName, 'NumericStepper', vMin, vMax, empty, button)
        result.update({'stepSize': step, 'canManualInput': manual})
        return result

    def createSlider(self, varName, vMin, vMax, step, formatStr='{{value}}', empty=False, button=None):
        result = self._createNumeric(varName, 'Slider', vMin, vMax, empty, button)
        result.update({'snapInterval': step, 'format': formatStr})
        return result

    def apply_settings(self, settings):
        for setting in settings:
            if setting in self.data:
                self.data[setting] = settings[setting]

        self.writeHotKeys(self.data)
        self.loadJson(self.ID, self.data, self.configPath, True, False)
        self.updateMod()

    def update_settings(self):
        self.update_data()
        self.updateMod()

    def onWindowClose(self):
        pass

    def update_data(self, doPrint=False):
        data = self.loadJson(self.ID, self.data, self.configPath)
        for key in data:
            if key in self.data:
                self.data[key] = data[key]

        self.readHotKeys(self.data)

    @staticmethod
    def readHotKeys(data):
        for key in data:
            if 'key' not in key:
                continue
            data[key] = []
            for keySet in data.get(key.replace('key', 'Key'), []):
                if isinstance(keySet, list):
                    data[key].append([])
                    for hotKey in keySet:
                        hotKeyName = hotKey if 'KEY_' in hotKey else 'KEY_' + hotKey
                        data[key][-1].append(getattr(Keys, hotKeyName))
                else:
                    hotKeyName = keySet if 'KEY_' in keySet else 'KEY_' + keySet
                    data[key].append(getattr(Keys, hotKeyName))

    @staticmethod
    def writeHotKeys(data):
        for key in data:
            if 'Key' not in key:
                continue
            data[key] = []
            for keySet in data[key.replace('Key', 'key')]:
                if isinstance(keySet, list):
                    data[key].append([])
                    for hotKey in keySet:
                        hotKeyName = BigWorld.keyToString(hotKey)
                        data[key][-1].append(hotKeyName if 'KEY_' in hotKeyName else 'KEY_' + hotKeyName)
                else:
                    hotKeyName = BigWorld.keyToString(keySet)
                    data[key].append(hotKeyName if 'KEY_' in hotKeyName else 'KEY_' + hotKeyName)

    def byte_ify(self, inputs):
        if inputs:
            if isinstance(inputs, dict):
                return {self.byte_ify(key): self.byte_ify(value) for key, value in inputs.iteritems()}
            elif isinstance(inputs, list):
                return [self.byte_ify(element) for element in inputs]
            elif isinstance(inputs, tuple):
                return tuple(self.byte_ify(element) for element in inputs)
            elif isinstance(inputs, unicode):
                # noinspection PyArgumentEqualDefault
                return inputs.encode('utf-8')
            else:
                return inputs
        return inputs

    @staticmethod
    def json_comments(text):
        regex = r'\s*(\/{2}).*$'
        regex_inline = r'(:?(?:\s)*([A-Za-zА-Яа-я\d\.{}]*)|((?<=\").*\"),?)(?:\s)*((((\/{2})).*)|)$'
        lines = text.split('\n')
        excluded = []
        for index, line in enumerate(lines):
            if re.search(regex, line):
                if re.search(r'^' + regex, line, re.IGNORECASE):
                    excluded.append(lines[index])
                elif re.search(regex_inline, line):
                    lines[index] = re.sub(regex_inline, r'\1', line)
        for line in excluded:
            lines.remove(line)
        return '\n'.join(lines), excluded

    @staticmethod
    def json_dumps(conf):
        return json.dumps(conf, sort_keys=True, indent=4, ensure_ascii=False, encoding='utf-8-sig', separators=(',', ': '))

    def loadJson(self, name, oldConfig, path, save=False, rewrite=True, encrypted=False):
        config_new = oldConfig
        if not os.path.exists(path):
            os.makedirs(path)
        new_path = '%s%s.json' % (path, name)
        if save:
            if os.path.isfile(new_path):
                config_newS = ''
                config_oldS = self.json_dumps(oldConfig)
                try:
                    with codecs.open(new_path, 'r', encoding='utf-8-sig') as json_file:
                        config_newS = json_file.read()
                        try:
                            config_newS = config_newS.decode('base64').decode('zlib')
                            encrypted = True
                        except (binascii.Error, zlib.error):
                            encrypted = False
                        config_newExcl = self.byte_ify(self.json_comments(config_newS)[1])
                except StandardError:
                    traceback.print_exc()
                    print config_newS.replace('\r', '')
                    config_newS = config_oldS
                    config_newExcl = []
                config_newD = self.byte_ify(config_newS)
                conf_newL = config_newD.split('\n')
                self.conf_changed = False
                if not rewrite:
                    def checkSubDict(oldDict, start_idx, end_idx):
                        decer = json.JSONDecoder(encoding='utf-8-sig')
                        encer = json.JSONEncoder(encoding='utf-8-sig')
                        new_end_idx = None
                        subLevels = 0
                        for idx in xrange(start_idx, end_idx):
                            newLine = conf_newL[idx]
                            if newLine in config_newExcl:
                                continue
                            if new_end_idx >= idx:
                                continue
                            if ':' in newLine:
                                new_key, new_value = newLine.split(':', 1)
                                new_key = new_key.strip().replace('"', '')
                                new_value = self.json_comments(new_value)[0].strip()
                                if new_value.endswith(','):
                                    new_value = ''.join(new_value.rsplit(',', 1)).strip()
                                if new_key in oldDict:
                                    if new_value == '{':
                                        subKey = new_key
                                        new_start_idx = idx
                                        new_end_idx = idx
                                        while new_end_idx < end_idx:
                                            curNewLine = self.byte_ify(self.json_comments(conf_newL[new_end_idx])[0])
                                            if '{' in curNewLine and new_end_idx > new_start_idx:
                                                subLevels += 1
                                            if '}' not in curNewLine:
                                                new_end_idx += 1
                                                continue
                                            if '}' in self.json_comments(curNewLine)[0].strip():
                                                if subLevels:
                                                    subLevels -= 1
                                                else:
                                                    break
                                        checkSubDict(oldDict[subKey], new_start_idx + 1, new_end_idx - 1)
                                    elif oldDict[new_key] != decer.decode(new_value):
                                        conf_newL[idx] = ':'.join(
                                            (newLine.split(':', 1)[0], newLine.split(':', 1)[1].replace(
                                                new_value, '%s' % encer.encode(oldDict[new_key]), 1)))
                                        self.conf_changed = True
                    try:
                        checkSubDict(oldConfig, 0, len(conf_newL))
                    except StandardError:
                        print new_path
                        traceback.print_exc()

                else:
                    self.conf_changed = not config_oldS == \
                        self.json_dumps(self.byte_ify(json.loads(self.json_comments(config_newD)[0])))
                    if self.conf_changed:
                        conf_newL = self.byte_ify(config_oldS).split('\n')
                if self.conf_changed:
                    print '%s: updating config: %s' % (self.ID, new_path)
                    with codecs.open(new_path, 'w', encoding='utf-8-sig') as json_file:
                        writeToConf = self.byte_ify('\n'.join(conf_newL))
                        if encrypted:
                            writeToConf = writeToConf.encode('zlib').encode('base64')
                        json_file.write(writeToConf)
                        config_new = oldConfig
            else:
                with codecs.open(new_path, 'w', encoding='utf-8-sig') as json_file:
                    data = self.json_dumps(oldConfig)
                    writeToConf = self.byte_ify(data)
                    if encrypted:
                        writeToConf = writeToConf.encode('zlib').encode('base64')
                    json_file.write(writeToConf)
                    config_new = oldConfig
        elif os.path.isfile(new_path):
            data = ''
            excluded = []
            try:
                with codecs.open(new_path, 'r', encoding='utf-8-sig') as json_file:
                    confData = json_file.read()
                    try:
                        confData = confData.decode('base64').decode('zlib')
                        encrypted = True
                    except (binascii.Error, zlib.error):
                        encrypted = False
                    data, excluded = self.json_comments(confData)
                    config_new = self.byte_ify(json.loads(data))
            except StandardError:
                print new_path
                traceback.print_exc()
                if excluded and not encrypted:
                    print data
        else:
            with codecs.open(new_path, 'w', encoding='utf-8-sig') as json_file:
                data = self.json_dumps(oldConfig)
                writeToConf = self.byte_ify(data)
                if encrypted:
                    writeToConf = writeToConf.encode('zlib').encode('base64')
                json_file.write(writeToConf)
                config_new = oldConfig
                print '%s: ERROR: Config not found, creating default: %s' % (self.ID, new_path)
        return config_new

    def message(self):
        return '%s v.%s %s' % (self.ID, self.version, self.author)

    def load(self):
        self.update_data(True)
        print '%s: initialised.' % (self.message())
        BigWorld.callback(0.0, self.do_config_delayed)

    def do_config_delayed(self):
        BigWorld.callback(0.0, self.do_config)

    def do_config(self):
        try:
            from helpers import getClientLanguage
            newLang = str(getClientLanguage()).lower()
            if newLang != self.lang:
                self.lang = newLang
                self.loadLang()
        except StandardError:
            LOG_CURRENT_EXCEPTION()
        try:
            # noinspection PyUnresolvedReferences
            from gui.mods.vxSettingsApi import vxSettingsApi
            vxSettingsApi.addMod('PYmodsGUI', self.ID, self.template_settings, self.data, self.apply_settings,
                                 self.onButtonPress)
        except ImportError:
            print '%s: no-GUI mode activated' % self.ID
        except StandardError:
            LOG_CURRENT_EXCEPTION()


class ModSettingsConfig(_Config):
    def __init__(self):
        super(self.__class__, self).__init__('PYmodsGUI')
        self.version = '2.0.1 (%(file_compile_date)s)'
        self.author = 'by spoter, satel1te (fork %s)' % self.author
        self.i18n = {'gui_name': "PY's mods settings",
                     'gui_description': "<font color='#DD7700'><b>Polyacov_Yury</b></font>'s modifications enabling and "
                                        "settings",
                     'gui_windowTitle': "Polyacov_Yury's mods settings",
                     'gui_buttonOK': 'OK',
                     'gui_buttonCancel': 'Cancel',
                     'gui_buttonApply': 'Apply',
                     'gui_enableButtonTooltip': '{HEADER}ON/OFF{/HEADER}{BODY}Enable/disable this mod{/BODY}'}
        self.loadLang()

    def update_settings(self):
        pass

    def feedbackHandler(self, container, eventType, *_):
        if container != self.ID:
            return
        # noinspection PyUnresolvedReferences
        from gui.mods.vxSettingsApi import vxSettingsApiEvents
        if eventType == vxSettingsApiEvents.WINDOW_CLOSED:
            self.isMSAWindowOpen = False
            self.onMSAWindowClose()

    def MSAPopulate(self):
        # noinspection PyUnresolvedReferences
        from gui.mods.vxSettingsApi import vxSettingsApi
        self.isMSAWindowOpen = True
        self.onMSAPopulate()
        vxSettingsApi.loadWindow(self.ID)

    def modsListRegister(self):
        BigWorld.g_modsListApi.addMod(id=self.ID, name=self.i18n['gui_name'],
                                      description=self.i18n['gui_description'], icon='scripts/client/PYmodsLogo.png',
                                      enabled=True, login=True, lobby=True, callback=self.MSAPopulate)

    def load(self):
        BigWorld.callback(0.0, self.do_config_delayed)

    def do_config(self):
        try:
            from helpers import getClientLanguage
            newLang = str(getClientLanguage()).lower()
            if newLang != self.lang:
                self.lang = newLang
                self.loadLang()
        except StandardError:
            LOG_CURRENT_EXCEPTION()
        try:
            # noinspection PyUnresolvedReferences
            from gui.mods.modsListApi import g_modsListApi
            if not hasattr(BigWorld, 'g_modsListApi'):
                BigWorld.g_modsListApi = g_modsListApi
            # noinspection PyUnresolvedReferences
            from gui.mods.vxSettingsApi import vxSettingsApi
            keys = ('windowTitle', 'buttonOK', 'buttonCancel', 'buttonApply', 'enableButtonTooltip')
            userSettings = {key: self.i18n['gui_%s' % key] for key in keys}
            vxSettingsApi.addContainer(self.ID, userSettings)
            vxSettingsApi.onFeedbackReceived += self.feedbackHandler
            BigWorld.callback(0.0, self.modsListRegister)
        except ImportError:
            print '%s: no-GUI mode activated' % self.ID
        except StandardError:
            LOG_CURRENT_EXCEPTION()


_modSettingsConfig = ModSettingsConfig()
_modSettingsConfig.load()


class Analytics(object):
    def __init__(self, description, version, ID, confList=None):
        self.mod_description = description
        self.mod_id_analytics = ID
        self.mod_version = version
        self.analytics_started = False
        self.analytics_ended = False
        self._thread_analytics = None
        self.confList = confList if confList else ['(not set)']
        self.playerName = ''
        self.old_playerName = ''
        self.lang = ''
        self.user = None
        self.old_user = None
        g_playerEvents.onAccountShowGUI += self.start
        BigWorld.callback(0.0, self.game_fini_hook)

    def game_fini_hook(self):
        import game
        old_fini = game.fini
        game.fini = lambda: (self.end(), old_fini())

    def analytics_start(self):
        if not self.analytics_started:
            from helpers import getClientLanguage
            self.lang = str(getClientLanguage()).upper()
            paramDict = {
                'v': 1,  # Version.
                'tid': '%s' % self.mod_id_analytics,  # Код мода для сбора статистики
                'cid': '%s' % self.user,  # ID пользователя
                't': 'screenview',  # Screenview hit type.
                'an': '%s' % self.mod_description,  # Имя мода
                'av': '%s %s' % (self.mod_description, self.mod_version),  # App version.
                'cd': '%s (Cluster: [%s], lang: [%s])' % (self.playerName, AUTH_REALM, self.lang),
                'ul': '%s' % self.lang,
                'sc': 'start'}
            for confName in self.confList:
                paramDict['aid'] = confName.split('.')[0]
                param = urllib.urlencode(paramDict)
                urllib2.urlopen(url='http://www.google-analytics.com/collect?', data=param).read()
            self.analytics_started = True
            self.old_user = BigWorld.player().databaseID
            self.old_playerName = BigWorld.player().name

    # noinspection PyUnusedLocal
    def start(self, ctx):
        player = BigWorld.player()
        if self.user is not None and self.user != player.databaseID:
            self.old_user = player.databaseID
            self.old_playerName = player.name
            self._thread_analytics = threading.Thread(target=self.end, name='Thread')
            self._thread_analytics.start()
        self.user = player.databaseID
        self.playerName = player.name
        self._thread_analytics = threading.Thread(target=self.analytics_start, name='Thread')
        self._thread_analytics.start()

    def end(self):
        g_playerEvents.onAccountShowGUI -= self.start
        if self.analytics_started:
            from helpers import getClientLanguage
            self.lang = str(getClientLanguage()).upper()
            param = urllib.urlencode({
                'v': 1,  # Version.
                'tid': '%s' % self.mod_id_analytics,  # Код мода для сбора статистики
                'cid': self.old_user,  # Anonymous Client ID.
                't': 'event',  # event hit type.
                'an': '%s' % self.mod_description,  # Имя мода
                'av': '%s %s' % (self.mod_description, self.mod_version),  # App version.
                'cd': '%s (Cluster: [%s], lang: [%s])' % (self.old_playerName, AUTH_REALM, self.lang),
                'ul': '%s' % self.lang,
                'sc': 'end'
            })
            urllib2.urlopen(url='http://www.google-analytics.com/collect?', data=param).read()
            self.analytics_started = False


class Sound(object):
    def __init__(self, soundPath):
        import SoundGroups
        self.__sndPath = soundPath
        self.__sndTick = SoundGroups.g_instance.getSound2D(self.__sndPath)
        self.__isPlaying = True
        self.stop()
        return

    @property
    def isPlaying(self):
        return self.__isPlaying

    @property
    def sound(self):
        return self.__sndTick

    def play(self):
        self.stop()
        if self.__sndTick:
            self.__sndTick.play()
        self.__isPlaying = True

    def stop(self):
        if self.__sndTick:
            self.__sndTick.stop()
        self.__isPlaying = False
