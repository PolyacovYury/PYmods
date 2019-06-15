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
            self.i18n.update(header='Поддержать автора', button_text='Ссылка на Patreon:', button_label='Открыть в браузере')
        else:
            self.i18n.update(header='Support the author', button_text='Patreon link:', button_label='Open in browser')

    def createTemplate(self):
        return {'modDisplayName': self.i18n['header'],
                'column1': [self.tb.createOptions('button', [self.i18n['button_text']], self.tb.types.RadioButtonGroup, 200,
                                                  True, {'text': self.i18n['button_label'], 'width': 150}, 0)],
                'column2': []}

    def onApplySettings(self, settings):
        pass

    def getData(self):
        return {'button': 0}

    def onButtonPress(self, vName, value):
        if vName != 'button':
            return
        BigWorld.wg_openWebBrowser('https://www.patreon.com/polyacov_yury/')


g_config = None
if api.MSA_Orig is not None and 'PYmodsGUI' in ConfigInterface.modSettingsContainers:
    g_config = ConfigInterface()
