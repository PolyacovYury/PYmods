from OpenModsCore import SimpleConfigInterface, overrideMethod
from gui.impl import backport
from helpers import i18n
from messenger import g_settings
from messenger.doc_loaders.html_templates import _MessageTemplate


class ConfigInterface(SimpleConfigInterface):
    def init(self):
        self.ID = '%(mod_ID)s'
        self.version = '1.0.0 (%(file_compile_date)s)'
        self.author = 'by Polyacov_Yury'
        self.modsGroup = 'PYmods'
        self.modSettingsID = 'PYmodsGUI'
        self.data = {
            'enabled': True,
            'color_header': '98FB98',
            'color_xp': '98FB98',
            'color_credits': '98FB98',
        }
        self.i18n = {
            'UI_description': 'Colored Battle Result Messages',
            'UI_setting_color_header_tooltip_header_text': 'Header color:',
            'UI_setting_color_xp_tooltip_header_text': 'XP color:',
            'UI_setting_color_credits_tooltip_header_text': 'Credits color:',
            'UI_setting_color_header_text': 'Current <font color=\'#%(color)s\'>header</font> color: #%(color)s',
            'UI_setting_color_xp_text': 'Current <font color=\'#%(color)s\'>xp</font> color: #%(color)s',
            'UI_setting_color_credits_text': 'Current <font color=\'#%(color)s\'>credits</font> color: #%(color)s',
            'UI_setting_color_header_tooltip': (
                'This color will be applied to all battle result headers.\n\n%(example)s'),
            'UI_setting_color_xp_tooltip': (
                'This color will be applied to all battle result xp values.\n\n%(example)s'),
            'UI_setting_color_credits_tooltip': (
                'This color will be applied to all battle result credits values.\n\n%(example)s'),
        }
        super(ConfigInterface, self).init()

    def createTemplate(self):
        controls = []
        for ix in ('header', 'xp', 'credits'):
            color_control = self.tb.createControl('color_%s' % ix, self.tb.types.ColorChoice)
            color_control['text'] = self.tb.getLabel('color_%s_tooltip_header' % ix)
            win = 'battleVictoryResult'
            # noinspection SpellCheckingInspection
            color_control['tooltip'] %= {'color': self.data['color_%s' % ix], 'example': g_settings.msgTemplates.format(win, {
                'color_messages_only': (ix,),
                'arenaName': i18n.makeString('#arenas:02_malinovka/name'),
                'vehicleNames': i18n.makeString('#germany_vehicles:Maus_short'),
                'xp': backport.getIntegralFormat(1234), 'credits': 56789,
                'xpEx': '', 'battlePassProgress': '', 'crystalStr': '', 'gold': '', 'eventCoinStr': '', 'bpcoinStr': '',
                'creditsEx': '', 'rankedProgress': '', 'rankedBonusBattles': '', 'achieves': '', 'badges': '', 'lock': '',
                'quests': '', 'piggyBank': '', 'platformCurrencyStr': ''})['message']}
            controls.append(color_control)
        return {
            'modDisplayName': self.i18n['UI_description'],
            'enabled': self.data['enabled'],
            'column1': controls,
            'column2': []}


g_config = ConfigInterface()


# noinspection SpellCheckingInspection
@overrideMethod(_MessageTemplate, 'format')
def new_format(base, self, ctx, *a, **k):
    orig_message = self.source['message']
    try:
        only = ctx.pop('color_messages_only', ())
        for color_type, mask in (('header', 'E9E2BF'), ('xp', 'C8C8B5'), ('credits', 'C5CFCF')):
            if only and color_type not in only:
                continue
            self.source['message'] = self.source['message'].replace(mask, g_config.data['color_%s' % color_type])
        return base(self, ctx, *a, **k)
    finally:
        self.source['message'] = orig_message
