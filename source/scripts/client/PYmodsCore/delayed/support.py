# coding=utf-8
import BigWorld
from . import api
from ..config.interfaces import DummyConfigInterface, PYmodsSettingContainer


class ConfigInterface(DummyConfigInterface):
    def __init__(self):
        super(ConfigInterface, self).__init__()
        # noinspection SpellCheckingInspection
        self.links = {
            'patreon': 'https://www.patreon.com/polyacov_yury/',
            'boosty': 'https://boosty.to/polyacov_yury/',
            'webmoney': 'https://pay.web.money/356226075013/',
            'qiwi': 'https://qiwi.com/n/POLYACOVYURY/',
            'streamlabs_yt': 'https://streamlabs.com/%D0%AE%D1%80%D0%B8%D0%B9%D0%9F%D0%BE%D0%BB%D1%8F%D0%BA%D0%BE%D0%B21/',
            'streamlabs_twitch': 'https://streamlabs.com/polyacov_yury/',
        }

    def init(self):
        self.ID = 'Support'
        self.modsGroup = 'PYmods'
        self.modSettingsID = 'PYmodsGUI'
        self.containerClass = PYmodsSettingContainer
        self.i18n = {}
        super(ConfigInterface, self).init()

    def loadLang(self):
        # noinspection SpellCheckingInspection
        self.i18n = {
            'header': 'Поддержать автора',
            'UI_setting_subscription_text': 'Подписка:',
            'patreon_button_text': 'Patreon:', 'patreon_button_label': 'Открыть в браузере',
            'boosty_button_text': 'Boosty:', 'boosty_button_label': 'Открыть в браузере',
            'UI_setting_donation_text': 'Перевод:',
            'webmoney_button_text': 'WebMoney:', 'webmoney_button_label': 'Открыть в браузере',
            'qiwi_button_text': 'QIWI Кошелёк:', 'qiwi_button_label': 'Открыть в браузере',
            'UI_setting_streamlabs_text': 'PayPal + оповещение на стриме:',
            'streamlabs_yt_button_text': 'YouTube:', 'streamlabs_yt_button_label': 'Открыть в браузере',
            'streamlabs_twitch_button_text': 'Twitch:', 'streamlabs_twitch_button_label': 'Открыть в браузере',
        } if self.lang in ('ru', 'uk') else {
            'header': 'Support the author',
            'UI_setting_subscription_label': 'Subscription:',
            'patreon_button_text': 'Patreon:', 'patreon_button_label': 'Open browser',
            'boosty_button_text': 'Boosty:', 'boosty_button_label': 'Open browser',
            'UI_setting_donation_label': 'Donate:',
            'webmoney_button_text': 'WebMoney:', 'webmoney_button_label': 'Open browser',
            'qiwi_button_text': 'QIWI Wallet:', 'qiwi_button_label': 'Open browser',
            'UI_setting_streamlabs_text': 'PayPal + stream shout-out:',
            'streamlabs_yt_button_text': 'YouTube:', 'streamlabs_yt_button_label': 'Open browser',
            'streamlabs_twitch_button_text': 'Twitch:', 'streamlabs_twitch_button_label': 'Open browser',
        }

    # noinspection SpellCheckingInspection
    def createTemplate(self):
        make_button = lambda _id: self.tb.createOptions(
            _id, [self.i18n[_id + '_button_text']], self.tb.types.RadioButtonGroup, 200, True,
            {'text': self.i18n[_id + '_button_label'], 'width': 150}, 0)
        return {
            'modDisplayName': self.i18n['header'],
            'column1':
                [
                    self.tb.createLabel('subscription'),
                ] + [
                    make_button(_id)
                    for _id in ('patreon', 'boosty')
                ],
            'column2':
                [
                    self.tb.createLabel('donation'),
                ] + [
                    make_button(_id)
                    for _id in ('qiwi', 'webmoney')
                ] + [
                    self.tb.createLabel('streamlabs'),
                ] + [
                    make_button(_id)
                    for _id in ('streamlabs_yt', 'streamlabs_twitch')
                ]}

    def onApplySettings(self, settings):
        pass

    def getData(self):
        return dict.fromkeys(self.links, 0)

    def onButtonPress(self, vName, value):
        link = self.links.get(vName)
        if link:
            BigWorld.wg_openWebBrowser(link)


g_config = None
if api.MSA_Orig is not None and 'PYmodsGUI' in ConfigInterface.modSettingsContainers:
    g_config = ConfigInterface()
