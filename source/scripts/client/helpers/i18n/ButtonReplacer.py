# -*- coding: utf-8 -*-
import BigWorld
import re
import traceback
from OpenModsCore import SimpleConfigInterface, remDups, pickRandomPart, Analytics, overrideMethod
from OpenModsCore.config import smart_update
from PlayerEvents import g_playerEvents
from debug_utils import LOG_ERROR, LOG_WARNING
from frameworks.wulf.resource_manager import ResourceManager


class ConfigInterface(SimpleConfigInterface):
    def __init__(self):
        self.textCache = {}
        self.textId = {}
        self.meta = {}
        self.textData = {}
        super(ConfigInterface, self).__init__()

    def init(self):
        self.ID = '%(mod_ID)s'
        self.version = '2.3.0 (%(file_compile_date)s)'
        self.author = 'by Polyacov_Yury'
        self.modsGroup = 'PYmods'
        self.modSettingsID = 'PYmodsGUI'
        self.data = {'enabled': True, 'updateAfterBattle': True}
        self.i18n = {
            'UI_description': 'Button Replacer',
            'UI_setting_updateAfterBattle_text': 'Re-read texts from configs after battle is over',
            'UI_setting_updateAfterBattle_tooltip': (
                'This setting allows the mod to re-read texts from configs while client is in process of hangar loading.'),
            'UI_setting_nums_text': 'Configs loaded: {totalCfg}, texts changed: {keys}',
            'UI_setting_meta_text': 'Loaded configs:',
            'UI_setting_meta_tooltip': '%(meta)s',
            'UI_setting_meta_no_configs': 'No configs were loaded.',
            'UI_setting_NDA': ' • No data available or provided.'}
        super(ConfigInterface, self).init()

    def createTemplate(self):
        cntLabel = self.tb.createLabel('meta')
        cntLabel['text'] = self.tb.getLabel('nums').format(totalCfg=len(self.meta), keys=len(self.textData))
        cntLabel['tooltip'] %= {'meta': '\n'.join([
            '\n'.join(meta[textType].rstrip() for textType in ('name', 'desc'))
            for _, meta in sorted(self.meta.items(), key=lambda x: x[0].lower())
        ]) or self.i18n['UI_setting_meta_no_configs']}
        return {'modDisplayName': self.i18n['UI_description'],
                'enabled': self.data['enabled'],
                'column1': [cntLabel],
                'column2': [self.tb.createControl('updateAfterBattle')]}

    def readCurrentSettings(self, quiet=True):
        self.meta.clear(), self.textData.clear(), self.textCache.clear(), self.textId.clear()
        self.readConfigDir(quiet)
        if not quiet:
            if self.meta:
                print self.LOG, 'loaded configs:', ', '.join(self.meta)
            else:
                print self.LOG, 'no configs loaded'
        for data in self.textData.itervalues():
            data['texts'] = remDups(data['texts'])

    def onReadConfig(self, quiet, dir_path, name, json_data, sub_dirs, names):
        self.meta[name + '.json'] = meta = {'name': '<b>%s.json</b>' % name, 'desc': self.i18n['UI_setting_NDA']}
        smart_update(meta, json_data.get('meta', {}))
        for key, data in json_data.iteritems():
            if key == 'meta':
                continue
            section = self.textData.setdefault(key, {})
            section['mode'] = data['mode']
            if 'bindToKey' in data:
                section['bindToKey'] = data['bindToKey']
            texts = section.setdefault('texts', [])
            text = data['text']
            if section['mode'] == 'single':
                if isinstance(text, (list, tuple)):
                    text = ''.join(x for x in text if x)
                texts.append(text.rstrip())
            else:
                if isinstance(text, str):
                    text = text.split(';')
                texts.extend(x.rstrip() for x in text if x.rstrip())

    def registerHotkeys(self):
        BigWorld.callback(0, super(ConfigInterface, self).registerHotkeys)

    def registerSettings(self):
        BigWorld.callback(0, super(ConfigInterface, self).registerSettings)


g_config = ConfigInterface()
i18nHooks = ('i18n_hook_makeString',)
old_makeString = lambda *_, **__: LOG_ERROR('i18n hook failed')


def i18n_hook_makeString(key, *args, **kwargs):
    if not g_config.data['enabled'] or key not in g_config.textData:
        return old_makeString(key, *args, **kwargs)
    if key not in g_config.textCache:
        mode = g_config.textData[key]['mode']
        texts = g_config.textData[key]['texts']
        if not texts:
            print g_config.LOG, 'empty text list for key', key
        elif mode == 'single':
            g_config.textCache[key], g_config.textId[key] = texts[0], 0
        elif mode in ('circle', 'random'):
            g_config.textCache[key], g_config.textId[key] = pickRandomPart(
                texts, g_config.textId.get(key, -1), mode != 'circle')
        elif mode == 'bindToKey':
            g_config.textCache[key] = texts[
                min(g_config.textId.get(g_config.textData[key].get('bindToKey', key), 0), len(texts) - 1)]
    text = g_config.textCache.get(key)
    if text is None:
        return old_makeString(key, *args, **kwargs)
    try:
        text = text.encode('utf-8')
        if args:
            try:
                text %= args
            except TypeError:
                LOG_WARNING("Arguments do not match string read by key '%s': %s", (key, args))
                return key
        elif kwargs:
            try:
                text %= kwargs
            except TypeError:
                LOG_WARNING("Arguments do not match string read by key '%s': %s", (key, kwargs))
                return key
        return text
    except StandardError:
        traceback.print_exc()
        print key
    return old_makeString(key, *args, **kwargs)


def onAvatarBecomeNonPlayer(*_, **__):
    if g_config.data['enabled'] and g_config.data['updateAfterBattle']:
        from gui.doc_loaders import messages_panel_reader
        messages_panel_reader._cache.clear()
        g_config.textCache.clear()


def new_construct(base, self, *args, **kwargs):
    block = base(self, *args, **kwargs)
    from gui.Scaleform.locale.RES_ICONS import RES_ICONS
    from gui.shared.formatters import text_styles, icons
    from gui.shared.items_parameters import formatters as params_formatters, bonus_helper
    from gui.shared.utils.functions import stripColorTagDescrTags, stripShortDescrTags
    from helpers.i18n import makeString as _ms
    from items import ITEM_TYPES
    if self.module.itemTypeID == ITEM_TYPES.optionalDevice:
        if bonus_helper.isSituationalBonus(self.module.name):
            effectDesc = text_styles.bonusPreviewText(
                stripShortDescrTags(stripColorTagDescrTags(_ms(self.module.fullDescription))))
            # noinspection PyArgumentEqualDefault
            icon = icons.makeImageTag(RES_ICONS.MAPS_ICONS_TOOLTIP_ASTERISK_OPTIONAL, 16, 16, 0, 4)
            desc = params_formatters.packSituationalIcon(effectDesc, icon)
        else:
            desc = text_styles.bonusAppliedText(stripShortDescrTags(stripColorTagDescrTags(_ms(self.module.fullDescription))))
        block[0]['data']['blocksData'][1]['data']['text'] = desc
    return block


def new_setModuleInfoS(base, self, moduleInfo, *args, **kwargs):
    if 'description' in moduleInfo:
        moduleInfo['description'] = re.sub(r'<[^>]*>', '', moduleInfo['description'])
    base(self, moduleInfo, *args, **kwargs)


@overrideMethod(ResourceManager, 'getTranslatedText')
def getTranslatedText(base, self, resourceID, *args, **kwargs):
    from gui.impl import backport
    full_key = backport.msgid(resourceID)
    if not full_key:
        return base(self, resourceID, *args, **kwargs)
    from helpers import i18n
    key = full_key.lower().partition('#tips:')[2]
    if not key:
        return i18n.makeString(full_key)
    # noinspection SpellCheckingInspection
    override_key = 'override/' + (
        'title' if (('battleroyale' not in key or 'status' in key) and not any(x in key for x in ('/', 'sandbox', 'tip')))
        else 'body')
    result = i18n.makeString('#tips:' + override_key)  # orig_makeString strips off file name for no reason
    return result if result != override_key else i18n.makeString(full_key)


def new_makeReasonInfo(base, *a, **k):
    return re.sub(r'<[^>]*>', '', base(*a, **k))


def ButtonReplacer_hooks():
    from gui.Scaleform.daapi.view.meta.ModuleInfoMeta import ModuleInfoMeta
    from gui.shared.tooltips.module import EffectsBlockConstructor
    from gui.doc_loaders import messages_panel_reader
    from gui.Scaleform.daapi.view.battle.shared.postmortem_panel import PostmortemPanel
    overrideMethod(ModuleInfoMeta, 'as_setModuleInfoS', new_setModuleInfoS)
    overrideMethod(EffectsBlockConstructor, 'construct', new_construct)
    messages_panel_reader._cache.clear()
    overrideMethod(PostmortemPanel, '__makeReasonInfo', new_makeReasonInfo)


g_playerEvents.onAvatarBecomeNonPlayer += onAvatarBecomeNonPlayer
BigWorld.callback(0, ButtonReplacer_hooks)
statistic_mod = Analytics(g_config.ID, g_config.version, 'UA-76792179-1', g_config.meta)
