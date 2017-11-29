from functools import partial

from ..json_reader import loadJson
from .Simple import ConfigInterface, ConfBlockInterface, SettingContainer


__all__ = ['PYmodsConfigInterface', 'PYmodsConfBlockInterface', 'PYmodsSettingContainer']


class PYmodsConfigInterface(ConfigInterface):
    def init(self):
        self.author = 'by Polyacov_Yury'
        self.modsGroup = 'PYmods'
        self.modSettingsID = 'PYmodsGUI'
        self.loadJsonData = lambda: loadJson(self.ID, self.ID, self.data, self.configPath)
        self.writeJsonData = lambda: loadJson(self.ID, self.ID, self.data, self.configPath, True, False)
        self.loadJsonLang = lambda: loadJson(self.ID, self.lang, self.i18n, self.langPath)
        super(PYmodsConfigInterface, self).init()

    def createTemplate(self):
        raise NotImplementedError

    @property
    def containerClass(self):
        if self._containerClass is None:
            self._containerClass = PYmodsSettingContainer
        return self._containerClass


class PYmodsConfBlockInterface(ConfBlockInterface):
    def init(self):
        super(PYmodsConfBlockInterface, self).init()
        self.author = 'by Polyacov_Yury'
        self.modsGroup = 'PYmods'
        self.modSettingsID = 'PYmodsGUI'
        self.loadJsonData = lambda: loadJson(self.ID, self.ID, self.data, self.configPath)
        self.writeJsonData = lambda: loadJson(self.ID, self.ID, self.data, self.configPath, True, False)
        self.loadJsonLang = lambda: loadJson(self.ID, self.lang, self.i18n, self.langPath)

    def createTemplate(self, blockID):
        raise NotImplementedError('Template for block %s is not created' % blockID)

    @property
    def containerClass(self):
        if self._containerClass is None:
            self._containerClass = PYmodsSettingContainer
        return self._containerClass


class PYmodsSettingContainer(SettingContainer):
    def loadLang(self):
        self.loadJsonLang = partial(loadJson, self.ID, self.lang, self.i18n, self.langPath)
        self.i18n = {'gui_name': "PY's mods settings",
                     'gui_description': "<font color='#DD7700'><b>Polyacov_Yury</b></font>'s modifications enabling and "
                                        "settings",
                     'gui_windowTitle': "Polyacov_Yury's mods settings",
                     'gui_buttonOK': 'OK',
                     'gui_buttonCancel': 'Cancel',
                     'gui_buttonApply': 'Apply',
                     'gui_enableButtonTooltip': '{HEADER}ON/OFF{/HEADER}{BODY}Enable/disable this mod{/BODY}'}
        super(PYmodsSettingContainer, self).loadLang()
