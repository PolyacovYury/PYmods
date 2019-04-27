from .Dummy import DummyConfigInterface, DummyConfBlockInterface, DummySettingContainer
from ..json_reader import loadJson
from ..template_builders import TemplateBuilder
from ..utils import smart_update, processHotKeys

__all__ = ['ConfigInterface', 'ConfBlockInterface', 'SettingContainer']


class Base(object):
    def __init__(self):
        self.containerClass = None
        self.ID = ''
        self.defaultKeys = {}
        self.i18n = {}
        self.data = {}
        self.author = ''
        self.version = ''
        self.modsGroup = ''
        self.configPath = ''
        self.langPath = ''

    loadDataJson = lambda self, *a, **kw: loadJson(self.ID, self.ID, self.data, self.configPath, *a, **kw)
    loadLangJson = lambda self, *a, **kw: loadJson(self.ID, self.ID, self.data, self.configPath, True, False, *a, **kw)
    writeDataJson = lambda self, *a, **kw: loadJson(self.ID, self.lang, self.i18n, self.langPath, *a, **kw)

    def init(self):
        self.containerClass = SettingContainer
        self.configPath = './mods/configs/%s/%s/' % (self.modsGroup, self.ID)
        self.langPath = '%si18n/' % self.configPath

    def loadLang(self):
        smart_update(self.i18n, self.loadLangJson())

    def createTB(self):
        return TemplateBuilder(self.data, self.i18n)

    def message(self):
        return '%s v.%s %s' % (self.ID, self.version, self.author)

    def load(self):
        print self.message() + ': initialised.'


class ConfigInterface(Base, DummyConfigInterface):
    def __init__(self):
        Base.__init__(self)
        DummyConfigInterface.__init__(self)

    def getData(self):
        return self.data

    def createTemplate(self):
        raise NotImplementedError

    def readCurrentSettings(self, quiet=True):
        processHotKeys(self.data, self.defaultKeys, 'write')
        smart_update(self.data, self.loadDataJson())
        processHotKeys(self.data, self.defaultKeys, 'read')

    def onApplySettings(self, settings):
        smart_update(self.data, settings)
        processHotKeys(self.data, self.defaultKeys, 'write')
        self.writeDataJson()
        processHotKeys(self.data, self.defaultKeys, 'read')
        self.updateMod()

    def load(self):
        DummyConfigInterface.load(self)
        Base.load(self)


class ConfBlockInterface(Base, DummyConfBlockInterface):
    def __init__(self):
        Base.__init__(self)
        DummyConfBlockInterface.__init__(self)

    @property
    def blockIDs(self):
        return self.data.keys()

    def getData(self, blockID=None):
        return self.data[blockID]

    def createTemplate(self, blockID=None):
        raise NotImplementedError('Template for block %s is not created' % blockID)

    def readCurrentSettings(self, quiet=True):
        for blockID in self.data:
            processHotKeys(self.data[blockID], self.defaultKeys, 'write')
        data = self.loadDataJson(quiet=quiet)
        for blockID in self.data:
            if blockID in data:
                smart_update(self.data[blockID], data[blockID])
            processHotKeys(self.data[blockID], self.defaultKeys, 'read')

    def onApplySettings(self, settings, blockID=None):
        smart_update(self.data[blockID], settings)
        processHotKeys(self.data[blockID], self.defaultKeys, 'write')
        self.writeDataJson()
        processHotKeys(self.data[blockID], self.defaultKeys, 'read')
        self.updateMod(blockID)

    def load(self):
        DummyConfBlockInterface.load(self)
        Base.load(self)


class SettingContainer(DummySettingContainer):
    def loadLang(self):
        smart_update(self.i18n, loadJson(
            self.ID, self.lang, self.i18n, 'mods/configs/%s/%s/i18n/' % (self.modsGroup, self.ID)))
