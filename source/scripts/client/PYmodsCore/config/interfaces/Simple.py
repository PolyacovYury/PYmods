import ResMgr
import os
import traceback
from .Dummy import DummyConfigInterface, DummyConfBlockInterface, DummySettingContainer
from ..json_reader import loadJson, loadJsonOrdered
from ..template_builders import TemplateBuilder
from ..utils import smart_update, processHotKeys

__all__ = ['ConfigInterface', 'ConfBlockInterface', 'SettingContainer']


class ConfigBase(object):
    def __init__(self):
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
    writeDataJson = lambda self, *a, **kw: loadJson(self.ID, self.ID, self.data, self.configPath, True, False, *a, **kw)
    loadLangJson = lambda self, *a, **kw: loadJson(self.ID, self.lang, self.i18n, self.langPath, *a, **kw)

    def init(self):
        self.configPath = './mods/configs/%s/%s/' % (self.modsGroup, self.ID)
        self.langPath = '%si18n/' % self.configPath
        self.registerHotkeys()

    def loadLang(self):
        smart_update(self.i18n, self.loadLangJson())

    def createTB(self):
        return TemplateBuilder(self.data, self.i18n)

    @property
    def containerClass(self):
        return SettingContainer

    def readConfigDir(
            self, quiet, recursive=False, dir_name='configs', error_not_exist=True, make_dir=True, ordered=False,
            encrypted=False, migrate=False, ext='.json'):
        configs_dir = self.configPath + dir_name + '/'
        if not os.path.isdir(configs_dir):
            if error_not_exist and not quiet:
                print self.ID + ': config directory not found:', configs_dir
            if make_dir:
                os.makedirs(configs_dir)
        for dir_path, sub_dirs, names in os.walk(configs_dir):
            dir_path = dir_path.replace('\\', '/').decode('windows-1251').encode('utf-8')
            local_path = dir_path.replace(configs_dir, '')
            names = sorted([x for x in names if x.endswith(ext)], key=str.lower)
            if not recursive:
                sub_dirs[:] = []
            for name in names:
                name = os.path.splitext(name)[0].decode('windows-1251').encode('utf-8')
                json_data = {}
                try:
                    if ext == '.json':
                        if ordered:
                            json_data = loadJsonOrdered(self.ID, dir_path, name)
                        else:
                            json_data = loadJson(self.ID, name, json_data, dir_path, encrypted=encrypted)
                    elif ext == '.xml':
                        json_data = ResMgr.openSection('.' + dir_path + '/' + name + ext)
                except StandardError:
                    traceback.print_exc()
                if not json_data:
                    print self.ID + ':', (dir_path and (dir_path + '/')) + name + ext, 'is invalid'
                    continue
                try:
                    if ext == '.json':
                        if migrate:
                            self.onMigrateConfig(quiet, dir_path, local_path, name, json_data, sub_dirs, names)
                        else:
                            self.onReadConfig(quiet, local_path, name, json_data, sub_dirs, names)
                    elif ext == '.xml':
                        self.onReadDataSection(quiet, dir_path, local_path, name, json_data, sub_dirs, names)
                        ResMgr.purge('.' + dir_path + '/' + name + ext)
                except StandardError:
                    traceback.print_exc()

    def onMigrateConfig(self, quiet, path, dir_path, name, json_data, sub_dirs, names):
        """clearing sub_dirs and/or names using slice assignment breaks the corresponding loop"""
        pass

    def onReadConfig(self, quiet, dir_path, name, json_data, sub_dirs, names):
        """clearing sub_dirs and/or names using slice assignment breaks the corresponding loop"""
        pass

    def onReadDataSection(self, quiet, path, dir_path, name, data_section, sub_dirs, names):
        """clearing sub_dirs and/or names using slice assignment breaks the corresponding loop"""
        pass

    def message(self):
        return '%s v.%s %s' % (self.ID, self.version, self.author)

    def __hotKeyPressed(self, event):
        try:
            self.onHotkeyPressed(event)
        except StandardError:
            print self.ID + ': ERROR at onHotkeyPressed'
            traceback.print_exc()

    def onHotkeyPressed(self, event):
        pass

    def registerHotkeys(self):
        from gui import InputHandler
        InputHandler.g_instance.onKeyDown += self.__hotKeyPressed
        InputHandler.g_instance.onKeyUp += self.__hotKeyPressed

    def load(self):
        print self.message() + ': initialised.'


class ConfigNoInterface(object):
    def updateMod(self):
        pass

    def createTemplate(self):
        pass

    def registerSettings(self):
        pass


class ConfigInterface(ConfigBase, DummyConfigInterface):
    def __init__(self):
        ConfigBase.__init__(self)
        DummyConfigInterface.__init__(self)

    def getData(self):
        return self.data

    def createTemplate(self):
        raise NotImplementedError

    def readData(self, quiet=True):
        processHotKeys(self.data, self.defaultKeys, 'write')
        smart_update(self.data, self.loadDataJson(quiet=quiet))
        processHotKeys(self.data, self.defaultKeys, 'read')

    def onApplySettings(self, settings):
        smart_update(self.data, settings)
        processHotKeys(self.data, self.defaultKeys, 'write')
        self.writeDataJson()
        processHotKeys(self.data, self.defaultKeys, 'read')

    def load(self):
        DummyConfigInterface.load(self)
        ConfigBase.load(self)


class ConfBlockInterface(ConfigBase, DummyConfBlockInterface):
    def __init__(self):
        ConfigBase.__init__(self)
        DummyConfBlockInterface.__init__(self)

    @property
    def blockIDs(self):
        return self.data.keys()

    def getData(self, blockID=None):
        return self.data[blockID]

    def createTemplate(self, blockID=None):
        raise NotImplementedError('Template for block %s is not created' % blockID)

    def readData(self, quiet=True):
        for blockID in self.data:
            processHotKeys(self.data[blockID], self.defaultKeys[blockID], 'write')
        data = self.loadDataJson(quiet=quiet)
        for blockID in self.data:
            if blockID in data:
                smart_update(self.data[blockID], data[blockID])
            processHotKeys(self.data[blockID], self.defaultKeys[blockID], 'read')

    def onApplySettings(self, settings, blockID=None):
        smart_update(self.data[blockID], settings)
        processHotKeys(self.data[blockID], self.defaultKeys[blockID], 'write')
        self.writeDataJson()
        processHotKeys(self.data[blockID], self.defaultKeys[blockID], 'read')

    def load(self):
        DummyConfBlockInterface.load(self)
        ConfigBase.load(self)


class SettingContainer(DummySettingContainer):
    def loadLang(self):
        smart_update(self.i18n, loadJson(
            self.ID, self.lang, self.i18n, 'mods/configs/%s/%s/i18n/' % (self.modsGroup, self.ID)))
