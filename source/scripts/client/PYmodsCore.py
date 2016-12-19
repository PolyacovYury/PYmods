# -*- coding: utf-8 -*-
import codecs
import json
import os
import random
import re
import threading
import time
import traceback
import urllib
import urllib2
from functools import partial

import BigWorld
import ResMgr

import Event
import Keys
from constants import AUTH_REALM, DEFAULT_LANGUAGE
from debug_utils import LOG_CURRENT_EXCEPTION

res = ResMgr.openSection('../paths.xml')
sb = res['Paths']
vl = sb.values()[0]
if vl is not None and not hasattr(BigWorld, 'curCV'):
    BigWorld.curCV = vl.asString
if not hasattr(BigWorld, 'PMC_wasPrint'):
    BigWorld.PMC_wasPrint = True
    print 'Current PYmodsCore version: 2.1.0 (%s)' % time.strftime('%d.%m.%Y', time.localtime(
        os.stat('%s/scripts/client/PYmodsCore.pyc' % BigWorld.curCV).st_mtime))
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
    onButtonPress = Event.Event()

    def __init__(self, filePath=''):
        self.filePath = filePath
        self.ID = os.path.basename(self.filePath).split('.')[0].replace('mod_', '')
        self.version = time.strftime('%d.%m.%Y', time.localtime(
            os.stat('%s/%s' % (BigWorld.curCV, self.filePath)).st_mtime))
        self.fileDir = '%s/%s/' % (BigWorld.curCV, os.path.dirname(self.filePath))
        self.configPath = '%s%s/' % (self.fileDir, self.ID)
        self.langPath = './res_mods/configs/PYmods/i18n/%s/' % self.ID
        self.author = 'by Polyacov_Yury'
        self.data = {}
        self.i18n = {}
        self.conf_changed = False
        self.tooltipSubs = {'HEADER': '{HEADER}', '/HEADER': '{/HEADER}', 'BODY': '{BODY}', '/BODY': '{/BODY}'}
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

    def makeTooltip(self, varName, ctx='setting'):
        return '{HEADER}%s{/HEADER}{BODY}%s{/BODY}' % tuple(
            self.i18n['UI_%s_%s_%s' % (ctx, varName, strType)] for strType in ('text', 'tooltip'))

    def getLabel(self, varName, ctx='setting'):
        return self.i18n['UI_%s_%s_text' % (ctx, varName)]

    def createLabel(self, varName, ctx='setting'):
        return {'type': 'Label', 'text': self.getLabel(varName, ctx), 'tooltip': self.makeTooltip(varName, ctx)}

    def createCheckbox(self, varName, ctx='setting'):
        result = self.createLabel(varName, ctx)
        result.update({'type': 'CheckBox', 'value': self.data[varName], 'varName': varName})
        return result

    def apply_settings(self, settings):
        for setting in settings:
            if setting in self.data:
                self.data[setting] = settings[setting]

        self.writeHotKeys(self.data)
        self.loadJson(os.path.basename(self.filePath).split('.')[0], self.data, self.fileDir, True, False)
        self.updateMod()

    def update_settings(self):
        self.update_data()
        self.updateMod()

    def onWindowClose(self):
        pass

    def update_data(self, doPrint=False):
        data = self.loadJson(os.path.basename(self.filePath).split('.')[0], self.data, self.fileDir)
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

    def loadJson(self, name, oldConfig, path, save=False, rewrite=True):
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
                        json_file.write(self.byte_ify('\n'.join(conf_newL)))
                        config_new = oldConfig
            else:
                with codecs.open(new_path, 'w', encoding='utf-8-sig') as json_file:
                    data = self.json_dumps(oldConfig)
                    json_file.write(self.byte_ify(data))
                    config_new = oldConfig
        elif os.path.isfile(new_path):
            data = ''
            excluded = []
            try:
                with codecs.open(new_path, 'r', encoding='utf-8-sig') as json_file:
                    data, excluded = self.json_comments(json_file.read())
                    config_new = self.byte_ify(json.loads(data))
            except StandardError:
                print new_path
                traceback.print_exc()
                if excluded:
                    print data
        else:
            with codecs.open(new_path, 'w', encoding='utf-8-sig') as json_file:
                data = self.json_dumps(oldConfig)
                json_file.write(self.byte_ify(data))
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
        super(self.__class__, self).__init__(__file__)
        self.ID = 'PYmodsGUI'
        self.version = '2.0.0 (%s)' % self.version
        self.author = 'by spoter, satel1te (fork %s)' % self.author
        self.configPath = './res_mods/configs/PYmods/'
        self.langPath = '%si18n/GUI/' % self.configPath
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
            self.onMSAWindowClose()

    def MSAPopulate(self):
        # noinspection PyUnresolvedReferences
        from gui.mods.vxSettingsApi import vxSettingsApi
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
    def __init__(self):
        self.analytics_started = False
        self.analytics_ended = False
        self._thread_analytics = None
        self.mod_description = ''
        self.mod_id_analytics = ''
        self.mod_version = ''
        self.playerName = ''
        self.old_playerName = ''
        self.lang = ''
        self.user = None
        self.old_user = None

    def analytics_start(self):
        if not self.analytics_started:
            from helpers import getClientLanguage
            self.lang = str(getClientLanguage()).upper()
            param = urllib.urlencode({
                'v': 1,  # Version.
                'tid': '%s' % self.mod_id_analytics,  # Код мода для сбора статистики
                'cid': '%s' % self.user,  # ID пользователя
                't': 'screenview',  # Screenview hit type.
                'an': '%s' % self.mod_description,  # Имя мода
                'av': '%s %s' % (self.mod_description, self.mod_version),  # App version.
                'cd': '%s (Cluster: [%s], lang: [%s])' % (self.playerName, AUTH_REALM, self.lang),
                'ul': '%s' % self.lang,
                'sc': 'start'
            })
            urllib2.urlopen(url='http://www.google-analytics.com/collect?', data=param).read()
            self.analytics_started = True
            self.old_user = BigWorld.player().databaseID
            self.old_playerName = BigWorld.player().name

    def start(self):
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
