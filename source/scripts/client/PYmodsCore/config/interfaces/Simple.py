from functools import partial

import BigWorld
import Keys
import traceback

from ..template_builders import TemplateBuilder, BlockTemplateBuilder
from .. import modSettingsContainers
from .Dummy import DummyConfigInterface, DummyConfBlockInterface, DummySettingContainer


__all__ = ['ConfigInterface', 'ConfBlockInterface', 'SettingContainer']


class ConfigInterface(DummyConfigInterface):
    def __init__(self):
        self.defaultKeys = {}
        self.data = {}
        self.author = ''
        self.version = ''
        self.modsGroup = ''
        self.loadJsonData = lambda *args, **kwargs: {}
        self.loadLangJson = lambda *args, **kwargs: {}
        self.writeJsonData = lambda *args, **kwargs: None
        self.configPath = ''
        self.langPath = ''
        super(ConfigInterface, self).__init__()

    def init(self):
        self.configPath = './mods/configs/%s/%s/' % (self.modsGroup, self.ID)
        self.langPath = '%si18n/' % self.configPath

    def loadLang(self):
        newConfig = self.loadLangJson()
        for setting in newConfig:
            if setting in self.i18n:
                self.i18n[setting] = newConfig[setting]

    def getData(self):
        pass

    def createTemplate(self):
        raise NotImplementedError

    def readCurrentSettings(self, quiet=True):
        data = self.loadJsonData()
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

    def onApplySettings(self, settings):
        for setting in settings:
            if setting in self.data:
                value = settings[setting]
                if isinstance(value, unicode):
                    value.encode('utf-8')
                self.data[setting] = value

        self.writeHotKeys(self.data)
        self.writeJsonData()
        self.updateMod()

    def registerSettings(self):
        """
        Register a settings block in this mod's settings window.
        """
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
            if self.modSettingsID not in modSettingsContainers:
                msc = modSettingsContainers[self.modSettingsID] = SettingContainer(self.modSettingsID, self.configPath)
                msc.onMSAPopulate += self.onMSAPopulate
                msc.onMSADestroy += self.onMSADestroy
            vxSettingsApi.addMod(self.modSettingsID, self.ID, self.createTemplate, self.data, self.onApplySettings,
                                 self.onButtonPress)
        except ImportError:
            print '%s: no-GUI mode activated' % self.ID
        except StandardError:
            traceback.print_exc()

    def message(self):
        return '%s v.%s %s' % (self.ID, self.version, self.author)

    def load(self):
        self.tb = TemplateBuilder(self.data, self.i18n, self.defaultKeys)
        super(ConfigInterface, self).load()
        print '%s: initialised.' % (self.message())


# noinspection PyMethodOverriding
class ConfBlockInterface(DummyConfBlockInterface, ConfigInterface):
    def __init__(self):
        self.defaultKeys = {}
        self.data = {}
        self.author = ''
        self.version = ''
        self.modsGroup = ''
        self.loadJsonData = lambda *args, **kwargs: {}
        self.loadLangJson = lambda *args, **kwargs: {}
        self.writeJsonData = lambda *args, **kwargs: None
        self.configPath = ''
        self.langPath = ''
        super(ConfBlockInterface, self).__init__()

    def init(self):
        self.configPath = './mods/configs/%s/%s/' % (self.modsGroup, self.ID)
        self.langPath = '%si18n/' % self.configPath

    def loadLang(self):
        newConfig = self.loadLangJson()
        for setting in newConfig:
            if setting in self.i18n:
                self.i18n[setting] = newConfig[setting]

    def getDataBlock(self, blockID):
        return self.data[blockID]

    def createTemplate(self, blockID):
        super(ConfBlockInterface, self).createTemplate(blockID)

    def readCurrentSettings(self, quiet=True):
        data = self.loadJsonData(quiet=quiet)
        for blockID in data:
            for key in data[blockID]:
                if key in self.data[blockID]:
                    self.data[blockID][key] = data[blockID][key]

            self.readHotKeys(self.data[blockID])

    def onApplySettings(self, blockID, settings):
        for setting in settings:
            if setting in self.data[blockID]:
                self.data[blockID][setting] = settings[setting]

        self.writeHotKeys(self.data[blockID])
        self.writeJsonData()
        self.updateMod(blockID)

    def load(self):
        self.tb = BlockTemplateBuilder(self.data, self.i18n, self.defaultKeys)
        super(ConfBlockInterface, self).load()

    def registerSettings(self):
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
            if self.modSettingsID not in modSettingsContainers:
                msc = modSettingsContainers[self.modSettingsID] = SettingContainer(self.modSettingsID, self.configPath)
                msc.load()
            for blockID in self.data:
                vxSettingsApi.addMod(self.modSettingsID, self.ID + blockID, partial(self.createTemplate, blockID),
                                     self.data[blockID], partial(self.onApplySettings, blockID), self.onButtonPress)
        except ImportError:
            print '%s: no-GUI mode activated' % self.ID
        except StandardError:
            traceback.print_exc()


class SettingContainer(DummySettingContainer):
    def __init__(self, ID, configPath):
        self.configPath = configPath
        self.langPath = ''
        super(SettingContainer, self).__init__(ID)
        self.loadJsonData = lambda *args, **kwargs: {}

    def loadLang(self):
        newConfig = self.loadJsonData()
        for setting in newConfig:
            if setting in self.i18n:
                self.i18n[setting] = newConfig[setting]

    def load(self):
        self.configPath = self.configPath.rsplit('/', 2)[0] + '/%s/' % self.ID
        self.langPath = '%si18n/' % self.configPath
        super(SettingContainer, self).load()
