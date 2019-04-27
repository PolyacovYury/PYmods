import Event
import traceback
from constants import DEFAULT_LANGUAGE
from ..template_builders import DummyTemplateBuilder


class DummyConfigInterface(object):
    modSettingsContainers = {}
    isMSAOpen = property(lambda self: getattr(self.modSettingsContainers.get(self.modSettingsID), 'isMSAOpen', False))
    MSAInstance = property(lambda self: getattr(self.modSettingsContainers.get(self.modSettingsID), 'API', None))

    def __init__(self):
        """Declaration for attribute placeholders, all attributes should be defined in init(), getData() and loadLang()"""
        self.ID = ''
        self.modsGroup = ''
        self.i18n = {}
        self.lang = DEFAULT_LANGUAGE
        self.modSettingsID = self.ID + '_settings'
        self.containerClass = DummySettingContainer
        self.init()
        self.loadLang()
        self.tb = self.createTB()
        self.template = self.createTemplate()
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

    def readCurrentSettings(self, quiet=True):
        """
        Is called upon mod loading and every time settings window is opened.
        Loading config data from files should be placed here.
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
        if self.MSAInstance is not None:
            self.MSAInstance.updateModSettings(self.ID, self.getData())

    def onMSAPopulate(self):
        """
        Called when mod settings window is about to start opening.
        :return:
        """
        self.readCurrentSettings()
        self.updateMod()

    def onMSADestroy(self):
        """
        Is called when mod settings window has closed.
        """
        pass

    def onButtonPress(self, vName, value):
        """
        Is called when a "preview' button for corresponding setting is pressed.
        :param vName: settings value name
        :param value: currently selected setting value (may differ from currently applied. As said, used for settings preview)
        """
        pass

    def registerSettings(self):
        from ...gui.api import registerSettings
        registerSettings(self)

    def load(self):
        """
        Called after mod __init__() is complete.
        """
        self.readCurrentSettings(False)
        self.registerSettings()


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

    def onApplySettings(self, settings, blockID=None):
        raise NotImplementedError

    def updateMod(self, blockID=''):
        if self.MSAInstance is not None:
            self.MSAInstance.updateModSettings(self.ID + blockID, self.getData(blockID))

    def onMSAPopulate(self):
        self.readCurrentSettings()
        for blockID in self.blockIDs:
            self.updateMod(blockID)

    def onButtonPress(self, vName, value, blockID=None):
        pass


class DummySettingContainer(object):
    def __init__(self, ID, modsGroup):
        self.modsGroup = modsGroup
        self.ID = ID
        self.langPath = ''
        self.iconPath = 'scripts/client/%s.png' % self.ID
        self.lang = DEFAULT_LANGUAGE
        self.i18n = {}
        self.onMSAPopulate = Event.Event()
        self.onMSADestroy = Event.Event()
        self.isMSAWindowOpen = False
        self.MSAHandlers = {}
        self.init()
        try:
            from helpers import getClientLanguage
            newLang = str(getClientLanguage()).lower()
            if newLang != self.lang:
                self.lang = newLang
        except StandardError:
            traceback.print_exc()
        self.loadLang()

    def init(self):
        pass

    def loadLang(self):
        pass

    def MSAPopulate(self, callback):
        self.isMSAWindowOpen = True
        self.onMSAPopulate()
        callback()

    def MSADispose(self):
        self.isMSAWindowOpen = False
        self.onMSADestroy()

    def MSAApply(self, alias, *a, **kw):
        self.MSAHandlers[alias]['apply'](*a, **kw)

    def MSAButton(self, alias, *a, **kw):
        self.MSAHandlers[alias]['button'](*a, **kw)
