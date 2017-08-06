# -*- coding: utf-8 -*-
import binascii
import zlib

import BigWorld
import Event
import Keys
import codecs
import json
import os
import re
import traceback
from constants import DEFAULT_LANGUAGE

__all__ = ['Config']


class MyJSONEncoder(json.JSONEncoder):
    def __init__(self, *args, **kwargs):
        super(MyJSONEncoder, self).__init__(*args, **kwargs)
        self.current_indent = 0
        self.current_indent_str = ""

    def encode(self, o):
        try:
            # Special Processing for lists
            if isinstance(o, (list, tuple)):
                primitives_only = True
                for item in o:
                    if isinstance(item, (list, tuple, dict)):
                        primitives_only = False
                        break
                output = []
                if primitives_only:
                    for item in o:
                        output.append(json.dumps(item))
                    return "[" + ", ".join(output) + "]"
                else:
                    self.current_indent += self.indent
                    self.current_indent_str = " " * self.current_indent
                    for item in o:
                        output.append(self.current_indent_str + self.encode(item))
                    self.current_indent -= self.indent
                    self.current_indent_str = " " * self.current_indent
                    return "[\n" + ",\n".join(output) + "\n" + self.current_indent_str + "]"
            elif isinstance(o, dict):
                output = []
                self.current_indent += self.indent
                self.current_indent_str = " " * self.current_indent
                keys = o.keys()
                if self.sort_keys:
                    keys = sorted(keys)
                for key in keys:
                    output.append(self.current_indent_str + json.dumps(key) + ": " + self.encode(o[key]))
                self.current_indent -= self.indent
                self.current_indent_str = " " * self.current_indent
                return "{\n" + ",\n".join(output) + "\n" + self.current_indent_str + "}"
            else:
                return super(self.__class__, self).encode(o)
        except StandardError:
            return str(o)


class Config(object):
    onMSAPopulate = Event.Event()
    onMSAWindowClose = Event.Event()
    isMSAWindowOpen = False
    onButtonPress = Event.Event()
    modSettingsConfigs = {}

    def __init__(self, ID):
        self.ID = ID
        self.version = ''
        self.configPath = './mods/configs/PYmods/%s/' % self.ID
        self.langPath = '%si18n/' % self.configPath
        self.author = 'by Polyacov_Yury'
        self.defaultKeys = {}
        self.data = {}
        self.i18n = {}
        self.modSettingsID = 'PYmodsGUI'
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
        from gui.vxSettingsApi import vxSettingsApi
        vxSettingsApi.updateMod(self.modSettingsID, self.ID, self.template_settings)

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
                       'options': [{'label': x} for x in options]})
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
            for keyType in ('key', 'button'):
                if keyType not in key:
                    continue
                data[key] = []
                for keySet in data.get(key.replace(keyType, keyType.capitalize()), []):
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
            for keyType in ('key', 'button'):
                if keyType.capitalize() not in key:
                    continue
                data[key] = []
                for keySet in data[key.replace(keyType.capitalize(), keyType)]:
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
    def encrypt(line):
        return line.encode('zlib').encode('base64')

    @staticmethod
    def decrypt(line, encrypted):
        if not line:
            return encrypted, line
        try:
            return True, line.decode('base64').decode('zlib')
        except (binascii.Error, zlib.error):
            return False, line

    @staticmethod
    def json_dumps(conf, sort_keys):
        return json.dumps(conf, sort_keys=sort_keys, indent=4, cls=MyJSONEncoder,
                          ensure_ascii=False, encoding='utf-8', separators=(',', ': '))

    def json_file_write(self, new_path, data, encrypted):
        kwargs = {'mode': 'w', 'encoding': 'utf-8-sig'} if not encrypted else {'mode': 'wb'}
        with codecs.open(new_path, **kwargs) as json_file:
            writeToConf = self.byte_ify(data)
            if encrypted:
                writeToConf = self.encrypt(writeToConf)
            json_file.write(writeToConf)

    def checkSubDict(self, oldDict, conf_newL, config_newExcl, start_idx, end_idx):
        conf_changed = False
        decer = json.JSONDecoder(encoding='utf-8')
        encer = json.JSONEncoder(encoding='utf-8')
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
                            else:
                                subLevels -= 1
                            if '}' in self.json_comments(curNewLine)[0].strip():
                                if subLevels > 0:
                                    subLevels -= 1
                                else:
                                    break
                        conf_changed = self.checkSubDict(
                            oldDict[subKey], conf_newL, config_newExcl, new_start_idx + 1, new_end_idx - 1)
                    elif oldDict[new_key] != decer.decode(new_value):
                        conf_newL[idx] = ':'.join(
                            (newLine.split(':', 1)[0], newLine.split(':', 1)[1].replace(
                                new_value, '%s' % encer.encode(oldDict[new_key]), 1)))
                        conf_changed = True
        return conf_changed

    def loadJson(self, name, oldConfig, path, save=False, rewrite=True, encrypted=False, sort_keys=True, doPrint=True):
        config_new = oldConfig
        if not os.path.exists(path):
            os.makedirs(path)
        new_path = '%s%s.json' % (path, name)
        if save:
            if os.path.isfile(new_path):
                config_newS = ''
                config_oldS = self.json_dumps(oldConfig, sort_keys)
                try:
                    kwargs = {'mode': 'r', 'encoding': 'utf-8-sig'} if not encrypted else {'mode': 'rb'}
                    with codecs.open(new_path, **kwargs) as json_file:
                        isEncrypted, config_newS = self.decrypt(json_file.read(), encrypted)
                        if not isEncrypted and encrypted:
                            config_newS = config_newS.decode('utf-8-sig')
                        config_newExcl = self.byte_ify(self.json_comments(config_newS)[1])
                except StandardError as e:
                    print new_path
                    print e
                    if not encrypted:
                        print config_newS.replace('\r', '')
                    config_newS = config_oldS
                    config_newExcl = []
                config_newD = self.byte_ify(config_newS)
                conf_newL = config_newD.split('\n')
                conf_changed = False
                if not rewrite:
                    try:
                        conf_changed = self.checkSubDict(oldConfig, conf_newL, config_newExcl, 0, len(conf_newL))
                    except StandardError as e:
                        print new_path
                        print e

                else:
                    conf_changed = not config_oldS == self.json_dumps(
                        self.byte_ify(json.loads(self.json_comments(config_newD)[0])), sort_keys)
                    if conf_changed:
                        conf_newL = self.byte_ify(config_oldS).split('\n')
                if conf_changed:
                    if doPrint:
                        print '%s: updating config: %s' % (self.ID, new_path)
                    self.json_file_write(new_path, '\n'.join(conf_newL), encrypted)
            else:
                self.json_file_write(new_path, self.json_dumps(oldConfig, sort_keys), encrypted)
        elif os.path.isfile(new_path):
            data = ''
            excluded = []
            try:
                kwargs = {'mode': 'r', 'encoding': 'utf-8-sig'} if not encrypted else {'mode': 'rb'}
                with codecs.open(new_path, **kwargs) as json_file:
                    isEncrypted, confData = self.decrypt(json_file.read(), encrypted)
                    if not isEncrypted and encrypted:
                        confData = confData.decode('utf-8-sig')
                    data, excluded = self.json_comments(confData)
                    config_new = self.byte_ify(json.loads(data))
            except StandardError:
                print new_path
                traceback.print_exc()
                if excluded and not encrypted:
                    print data
        else:
            self.json_file_write(new_path, self.json_dumps(oldConfig, sort_keys), encrypted)
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
            traceback.print_exc()
        try:
            # noinspection PyUnresolvedReferences
            from gui.vxSettingsApi import vxSettingsApi
            if self.modSettingsID not in self.modSettingsConfigs:
                msc = self.modSettingsConfigs[self.modSettingsID] = ModSettingsConfig(self.modSettingsID, self.configPath)
                msc.load()
            vxSettingsApi.addMod(self.modSettingsID, self.ID, self.template_settings, self.data, self.apply_settings,
                                 self.onButtonPress)
        except ImportError:
            print '%s: no-GUI mode activated' % self.ID
        except StandardError:
            traceback.print_exc()


class ModSettingsConfig(Config):
    def __init__(self, ID, configPath):
        super(self.__class__, self).__init__(ID)
        self.configPath = configPath.rsplit('/', 2)[0] + '/%s/' % self.ID
        self.langPath = '%si18n/' % self.configPath
        self.version = '2.0.3 (%(file_compile_date)s)'
        self.author = 'by spoter, satel1te (fork by Polyacov_Yury)'
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
        from gui.vxSettingsApi import vxSettingsApiEvents
        if eventType == vxSettingsApiEvents.WINDOW_CLOSED:
            self.isMSAWindowOpen = False
            self.onMSAWindowClose()

    def MSAPopulate(self):
        # noinspection PyUnresolvedReferences
        from gui.vxSettingsApi import vxSettingsApi
        self.isMSAWindowOpen = True
        self.onMSAPopulate()
        vxSettingsApi.loadWindow(self.ID)

    def modsListRegister(self):
        kwargs = dict(
            id=self.ID, name=self.i18n['gui_name'], description=self.i18n['gui_description'],
            icon='scripts/client/%s.png' % self.ID, enabled=True, login=True, lobby=True, callback=self.MSAPopulate)
        try:
            BigWorld.g_modsListApi.addModification(**kwargs)
        except AttributeError:
            BigWorld.g_modsListApi.addMod(**kwargs)

    def load(self):
        self.do_config()

    def do_config(self):
        try:
            from helpers import getClientLanguage
            newLang = str(getClientLanguage()).lower()
            if newLang != self.lang:
                self.lang = newLang
                self.loadLang()
        except StandardError:
            traceback.print_exc()
        try:
            # noinspection PyUnresolvedReferences
            from gui.modsListApi import g_modsListApi
            if not hasattr(BigWorld, 'g_modsListApi'):
                BigWorld.g_modsListApi = g_modsListApi
            # noinspection PyUnresolvedReferences
            from gui.vxSettingsApi import vxSettingsApi
            keys = ('windowTitle', 'buttonOK', 'buttonCancel', 'buttonApply', 'enableButtonTooltip')
            userSettings = {key: self.i18n['gui_%s' % key] for key in keys}
            vxSettingsApi.addContainer(self.ID, userSettings)
            vxSettingsApi.onFeedbackReceived += self.feedbackHandler
            BigWorld.callback(0.0, self.modsListRegister)
        except ImportError:
            print '%s: no-GUI mode activated' % self.ID
        except StandardError:
            traceback.print_exc()
