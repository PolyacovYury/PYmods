# coding=utf-8
import BigWorld
from ..config.interfaces import DummyConfigInterface, PYmodsSettingContainer
from . import api


class ConfigInterface(DummyConfigInterface):
    def init(self):
        self.ID = 'Patreon'
        self.modsGroup = 'PYmods'
        self.modSettingsID = 'PYmodsGUI'
        self.containerClass = PYmodsSettingContainer
        self.i18n = {}
        super(ConfigInterface, self).init()

    def loadLang(self):
        if self.lang == 'ru':
            self.i18n = {'header': 'Поддержать автора',
                         'patreon_button_text': 'Ссылка на Patreon:', 'patreon_button_label': 'Открыть в браузере',
                         'dueler_button_text': 'Сайт клуба Дуэлянт:', 'dueler_button_label': 'Открыть в браузере'}
        else:
            self.i18n = {'header': 'Support the author',
                         'patreon_button_text': 'Patreon link:', 'patreon_button_label': 'Open in browser',
                         'dueler_button_text': 'Dueler Club link:', 'dueler_button_label': 'Open in browser'}

    def createTemplate(self):
        return {'modDisplayName': self.i18n['header'],
                'column1': [self.tb.createOptions(
                    'patreon', [self.i18n['patreon_button_text']], self.tb.types.RadioButtonGroup, 200, True,
                    {'text': self.i18n['patreon_button_label'], 'width': 150}, 0)],
                'column2': [self.tb.createOptions(
                    'dueler', [self.i18n['dueler_button_text']], self.tb.types.RadioButtonGroup, 200, True,
                    {'text': self.i18n['dueler_button_label'], 'width': 150}, 0)]}

    def onApplySettings(self, settings):
        pass

    def getData(self):
        return {'patreon': 0, 'dueler': 0}

    def onButtonPress(self, vName, value):
        if vName == 'patreon':
            BigWorld.wg_openWebBrowser('https://www.patreon.com/polyacov_yury/')
        elif vName == 'dueler':
            BigWorld.wg_openWebBrowser('https://www.dueler.club/')


g_config = None
if api.MSA_Orig is not None and 'PYmodsGUI' in ConfigInterface.modSettingsContainers:
    g_config = ConfigInterface()
