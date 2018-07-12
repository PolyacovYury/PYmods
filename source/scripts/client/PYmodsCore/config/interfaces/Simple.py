from ..template_builders import TemplateBuilder, BlockTemplateBuilder
from ..utils import smart_update, processHotKeys
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
        self.loadJsonLang = lambda *args, **kwargs: {}
        self.writeJsonData = lambda *args, **kwargs: None
        self.configPath = ''
        self.langPath = ''
        super(ConfigInterface, self).__init__()

    def init(self):
        self.configPath = './mods/configs/%s/%s/' % (self.modsGroup, self.ID)
        self.langPath = '%si18n/' % self.configPath

    def loadLang(self):
        smart_update(self.i18n, self.loadJsonLang())

    def getData(self):
        return self.data

    def createTemplate(self):
        raise NotImplementedError

    def readCurrentSettings(self, quiet=True):
        smart_update(self.data, self.loadJsonData())
        processHotKeys(self.data, self.defaultKeys, 'read')

    def onApplySettings(self, settings):
        smart_update(self.data, settings)
        processHotKeys(self.data, self.defaultKeys, 'write')
        self.writeJsonData()
        processHotKeys(self.data, self.defaultKeys, 'read')
        self.updateMod()

    @property
    def tb(self):
        if self._tb is None:
            self._tb = TemplateBuilder(self.data, self.i18n, self.defaultKeys)
        return self._tb

    @property
    def containerClass(self):
        if self._containerClass is None:
            self._containerClass = SettingContainer
        return self._containerClass

    def message(self):
        return '%s v.%s %s' % (self.ID, self.version, self.author)

    def load(self):
        super(ConfigInterface, self).load()
        print self.message() + ': initialised.'


class ConfBlockInterface(DummyConfBlockInterface):
    def __init__(self):
        self.defaultKeys = {}
        self.data = {}
        self.author = ''
        self.version = ''
        self.modsGroup = ''
        self.loadJsonData = lambda *args, **kwargs: {}
        self.loadJsonLang = lambda *args, **kwargs: {}
        self.writeJsonData = lambda *args, **kwargs: None
        self.configPath = ''
        self.langPath = ''
        super(ConfBlockInterface, self).__init__()

    def init(self):
        self.configPath = './mods/configs/%s/%s/' % (self.modsGroup, self.ID)
        self.langPath = '%si18n/' % self.configPath

    def loadLang(self):
        smart_update(self.i18n, self.loadJsonLang())

    @property
    def blockIDs(self):
        return self.data

    def getDataBlock(self, blockID):
        return self.data[blockID]

    def createTemplate(self, blockID):
        raise NotImplementedError('Template for block %s is not created' % blockID)

    def readCurrentSettings(self, quiet=True):
        data = self.loadJsonData(quiet=quiet)
        for blockID in data:
            smart_update(self.data[blockID], data[blockID])
            processHotKeys(self.data[blockID], self.defaultKeys, 'read')

    def onApplySettings(self, blockID, settings):
        smart_update(self.data[blockID], settings)
        processHotKeys(self.data[blockID], self.defaultKeys, 'write')
        self.writeJsonData()
        processHotKeys(self.data[blockID], self.defaultKeys, 'read')
        self.updateMod(blockID)

    @property
    def tb(self):
        if self._tb is None:
            self._tb = BlockTemplateBuilder(self.data, self.i18n, self.defaultKeys)
        return self._tb

    @property
    def containerClass(self):
        if self._containerClass is None:
            self._containerClass = SettingContainer
        return self._containerClass

    def message(self):
        return '%s v.%s %s' % (self.ID, self.version, self.author)

    def load(self):
        super(ConfBlockInterface, self).load()
        print self.message() + ': initialised.'


class SettingContainer(DummySettingContainer):
    def __init__(self, ID, configPath):
        self.langPath = ''
        self.loadJsonLang = lambda *args, **kwargs: {}
        super(SettingContainer, self).__init__(ID, configPath)

    def loadLang(self):
        self.configPath = self.configPath.rsplit('/', 2)[0] + '/%s/' % self.ID
        self.langPath = '%si18n/' % self.configPath
        smart_update(self.i18n, self.loadJsonLang())
