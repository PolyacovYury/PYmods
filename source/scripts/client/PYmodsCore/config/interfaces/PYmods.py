import traceback

from functools import partial

from ..json_reader import loadJson
from .. import modSettingsContainers
from .Simple import ConfigInterface, ConfBlockInterface, SettingContainer


__all__ = ['PYmodsConfigInterface', 'PYmodsConfBlockInterface', 'PYmodsSettingContainer']


class PYmodsConfigInterface(ConfigInterface):
    def init(self):
        self.author = 'by Polyacov_Yury'
        self.modsGroup = 'PYmods'
        self.modSettingsID = 'PYmodsGUI'
        self.loadJsonData = lambda: loadJson(self.ID, self.ID, self.data, self.configPath)
        self.writeJsonData = lambda: loadJson(self.ID, self.ID, self.data, self.configPath, True, False)
        self.loadLangJson = lambda: loadJson(self.ID, self.lang, self.i18n, self.langPath)
        super(PYmodsConfigInterface, self).init()

    def loadLang(self):
        newConfig = loadJson(self.ID, self.lang, self.i18n, self.langPath)
        for setting in newConfig:
            if setting in self.i18n:
                self.i18n[setting] = newConfig[setting]

    def createTemplate(self):
        raise NotImplementedError

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
                msc = modSettingsContainers[self.modSettingsID] = PYmodsSettingContainer(self.modSettingsID, self.configPath)
                msc.load()
            vxSettingsApi.addMod(self.modSettingsID, self.ID, self.createTemplate, self.data, self.onApplySettings,
                                 self.onButtonPress)
        except ImportError:
            print '%s: no-GUI mode activated' % self.ID
        except StandardError:
            traceback.print_exc()


class PYmodsConfBlockInterface(ConfBlockInterface):
    def init(self):
        super(PYmodsConfBlockInterface, self).init()
        self.author = 'by Polyacov_Yury'
        self.modsGroup = 'PYmods'
        self.modSettingsID = 'PYmodsGUI'
        self.loadJsonData = partial(loadJson, self.ID, self.ID, self.data, self.configPath, True, False)
        self.writeJsonData = partial(loadJson, self.ID, self.ID, self.data, self.configPath)


class PYmodsSettingContainer(SettingContainer):
    def loadLang(self):
        self.loadJsonData = partial(loadJson, self.ID, self.lang, self.i18n, self.langPath)
        self.i18n = {'gui_name': "PY's mods settings",
                     'gui_description': "<font color='#DD7700'><b>Polyacov_Yury</b></font>'s modifications enabling and "
                                        "settings",
                     'gui_windowTitle': "Polyacov_Yury's mods settings",
                     'gui_buttonOK': 'OK',
                     'gui_buttonCancel': 'Cancel',
                     'gui_buttonApply': 'Apply',
                     'gui_enableButtonTooltip': '{HEADER}ON/OFF{/HEADER}{BODY}Enable/disable this mod{/BODY}'}
        super(PYmodsSettingContainer, self).loadLang()
