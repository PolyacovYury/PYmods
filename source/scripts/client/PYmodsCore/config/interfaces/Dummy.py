from constants import DEFAULT_LANGUAGE
from ..template_builders import DummyTemplateBuilder


class DummyConfigInterface(object):
    modSettingsContainers = {}
    isMSAOpen = property(lambda self: getattr(self.modSettingsContainers.get(self.modSettingsID), 'isMSAOpen', False))
    MSAInstance = property(lambda self: self.modSettingsContainers.get(self.modSettingsID))

    def __init__(self):
        """Declaration for attribute placeholders, all attributes should be defined in init(), getData() and loadLang()"""
        self.ID = ''
        self.modsGroup = ''
        self.i18n = {}
        self.lang = DEFAULT_LANGUAGE
        self.modSettingsID = self.ID + '_settings'
        self.init()
        self.loadLang()
        self.tb = self.createTB()
        self.load()

    def init(self):
        """
        self.ID = 'AwesomeMod'  - mod ID
        self.modSettingsID = 'AwesomeModSettings' - mod settings container ID.
            Be careful, this will be an alias for a ViewSettings Object!
        """
        pass

    def getData(self):
        """
        :return: dict with your mod settings (if they are stored elsewhere, otherwise you should use ConfigInterface instead)
        """
        raise NotImplementedError

    def loadLang(self):
        """
        self.i18n = {} - your mod texts for messages, setting labels, etc.
        """
        pass

    def createTB(self):
        return DummyTemplateBuilder(self.i18n)

    def createTemplate(self):
        """
        :return: dict representing your mod's settings template.
        """
        raise NotImplementedError

    @property
    def template(self):
        return self.createTemplate()

    @property
    def container_i18n(self):
        return {}

    def migrateConfigs(self):
        """
        Called before initial config load. Should contain code that updates configs from old version
        """
        pass

    def readData(self, quiet=True):
        """
        Is called upon mod loading and every time settings window is opened.
        Loading main config data from main file should be placed here.
        :param quiet: optional, if you have debug mode in your mod - this will be useful
        """
        pass

    def readCurrentSettings(self, quiet=True):
        """
        Is called upon mod loading and every time settings window is opened.
        Loading additional config data should be placed here.
        :param quiet: optional, if you have debug mode in your mod - this will be useful
        """
        pass

    def onApplySettings(self, settings):
        """
        Is called when user clicks the "Apply" button in settings window.
        And also upon mod loading because settings API thinks that it is the only place to store mod settings.
        :param settings: new setting values.
        """
        raise NotImplementedError

    def updateMod(self):
        """
        A function to update mod template after config actions are complete.
        """
        if self.MSAInstance is None:
            return
        self.MSAInstance.config['templates'][self.ID] = self.template
        self.MSAInstance.updateModSettings(self.ID, self.getData())

    def onMSAPopulate(self):
        """
        Called when mod settings window is about to start opening.
        :return:
        """
        self.readData()
        self.readCurrentSettings()
        self.updateMod()

    def onMSADestroy(self):
        """
        Is called when mod settings window has closed.
        """
        pass

    def onButtonPress(self, vName, value):
        """
        Called when a "preview' button for corresponding setting is pressed.
        :param vName: settings value name
        :param value: currently selected setting value (may differ from currently applied. As said, used for settings preview)
        """
        pass

    def registerSettings(self):
        from ...delayed.api import registerSettings
        registerSettings(self)

    def load(self):
        """
        Called after mod __init__() is complete.
        """
        self.migrateConfigs()
        self.registerSettings()
        self.readData(False)
        self.readCurrentSettings(False)
        self.updateMod()


class DummyConfBlockInterface(DummyConfigInterface):
    def __init__(self):
        self._blockIDs = []  # overwrite in init() of derived class
        super(DummyConfBlockInterface, self).__init__()

    def getData(self, blockID=None):
        raise NotImplementedError('Data block for block %s is not defined' % blockID)

    @property
    def blockIDs(self):
        return self._blockIDs

    def createTemplate(self, blockID=None):
        raise NotImplementedError('Template for block %s is not created' % blockID)

    @property
    def template(self):
        return {blockID: self.createTemplate(blockID) for blockID in self.blockIDs}

    def onApplySettings(self, settings, blockID=None):
        raise NotImplementedError

    def updateMod(self):
        if self.MSAInstance is None:
            return
        templates = self.template  # saves calls
        for blockID in self.blockIDs:
            self.MSAInstance.config['templates'][self.ID + blockID] = templates[blockID]
            self.MSAInstance.updateModSettings(self.ID + blockID, self.getData(blockID))

    def onButtonPress(self, vName, value, blockID=None):
        pass
