# -*- coding: utf-8 -*-
import BigWorld
import PYmodsCore
import glob
import os
import re
import traceback
from debug_utils import LOG_ERROR, LOG_WARNING


def __dir__():
    return ['i18n_hook_makeString']


class _Config(PYmodsCore.Config):
    def __init__(self):
        super(self.__class__, self).__init__('%(mod_ID)s')
        self.version = '2.1.3 (%(file_compile_date)s)'
        self.data = {'enabled': True,
                     'reReadAtEnd': True}
        self.i18n = {
            'UI_description': 'Button Replacer',
            'UI_setting_reReadAtEnd_text': 'Re-read texts from configs after battle is over',
            'UI_setting_reReadAtEnd_tooltip': (
                'This setting allows the mod to re-read texts from configs while client is in process of hangar loading.'),
            'UI_setting_caps_text': 'Configs loaded: {totalCfg}, texts changed: {keys}',
            'UI_setting_meta_text': 'Loaded configs:',
            'UI_setting_meta_tooltip': '%(meta)s',
            'UI_setting_meta_no_configs': 'No configs were loaded.',
            'UI_setting_NDA': ' • No data available or provided.'}
        self.textStack = {}
        self.wasReplaced = {}
        self.textId = {}
        self.configsList = []
        self.confMeta = {}
        self.sectDict = {}
        self.loadLang()

    def template_settings(self):
        metaList = map(lambda x: '\n'.join((self.confMeta[x][textType].rstrip() for textType in ('name', 'desc'))),
                       sorted(self.configsList, key=str.lower))
        metaStr = ('\n'.join(metaList)) if metaList else self.i18n['UI_setting_meta_no_configs']
        capLabel = self.createLabel('meta')
        capLabel['text'] = self.getLabel('caps').format(totalCfg=len(self.configsList), keys=len(self.sectDict))
        capLabel['tooltip'] %= {'meta': metaStr}
        return {'modDisplayName': self.i18n['UI_description'],
                'settingsVersion': 200,
                'enabled': self.data['enabled'],
                'column1': [capLabel],
                'column2': [self.createControl('reReadAtEnd')]}

    def update_data(self, doPrint=False):
        super(self.__class__, self).update_data()
        self.configsList = []
        self.confMeta.clear()
        self.sectDict = {}
        configPath = self.configPath + 'configs/'
        if os.path.isdir(configPath):
            if doPrint:
                print '%s: loading configs from %s:' % (self.ID, configPath)
            for conp in glob.iglob(configPath + '*.json'):
                if doPrint:
                    print '%s: loading %s' % (self.ID, os.path.basename(conp))
                confdict = self.loadJson(os.path.basename(conp).split('.')[0], self.data,
                                         os.path.dirname(conp) + '/')
                if os.path.basename(conp) not in self.configsList:
                    self.configsList.append(os.path.basename(conp))
                self.confMeta[os.path.basename(conp)] = metaDict = {'name': '<b>%s</b>' % os.path.basename(conp),
                                                                    'desc': self.i18n['UI_setting_NDA'],
                                                                    'has': False}
                if 'meta' in confdict:
                    metaDict['name'] = confdict['meta'].get('name', metaDict['name'])
                    metaDict['desc'] = confdict['meta'].get('desc', metaDict['desc'])
                    metaDict['has'] = True
                for key in confdict.keys():
                    if key != 'meta' and key not in self.data:
                        self.sectDict.setdefault(key, {})
                        self.sectDict[key]['mode'] = confdict[key]['mode']
                        if confdict[key].get('bindToKey') is not None:
                            self.sectDict[key]['bindToKey'] = confdict[key]['bindToKey']
                        textList = self.sectDict[key].setdefault('textList', [])
                        if self.sectDict[key]['mode'] == 'single':
                            if isinstance(confdict[key]['text'], str):
                                textList.append(confdict[key]['text'].rstrip())
                            elif isinstance(confdict[key]['text'], list):
                                textList.append(
                                    ''.join(filter(None, confdict[key]['text'])).rstrip())
                        else:
                            if isinstance(confdict[key]['text'], str):
                                textList.extend(filter(
                                    None, map(lambda txtStr: txtStr.rstrip(), confdict[key]['text'].split(';'))))
                            elif isinstance(confdict[key]['text'], list):
                                textList.extend(filter(
                                    None, map(lambda txtStr: txtStr.rstrip(), confdict[key]['text'])))

        elif doPrint:
            print '%s: config directory not found: %s' % (self.ID, configPath)

        for key in self.sectDict:
            self.sectDict[key]['textList'] = PYmodsCore.remDups(self.sectDict[key]['textList'])


_config = _Config()
_config.load()


def old_makeString(*_, **kwargs):
    _ = kwargs
    LOG_ERROR('i18n hook failed')


def i18n_hook_makeString(key, *args, **kwargs):
    if _config.data['enabled'] and key in _config.sectDict:
        if key not in _config.wasReplaced or not _config.wasReplaced[key]:
            if _config.sectDict[key]['mode'] == 'single':
                _config.textStack[key], _config.textId[key] = (_config.sectDict[key]['textList'][0], 0) if len(
                    _config.sectDict[key]['textList']) else ('', -1)
            elif _config.sectDict[key]['mode'] == 'random':
                _config.textStack[key], _config.textId[key] = PYmodsCore.pickRandomPart(
                    _config.sectDict[key]['textList'], _config.textId.get(key, -1))
            elif _config.sectDict[key]['mode'] == 'circle':
                _config.textStack[key], _config.textId[key] = PYmodsCore.pickRandomPart(
                    _config.sectDict[key]['textList'], _config.textId.get(key, -1), True)
            elif _config.sectDict[key]['mode'] == 'bindToKey':
                _config.textStack[key] = _config.sectDict[key]['textList'][
                    min(_config.textId.get(_config.sectDict[key].get('bindToKey', key), 0),
                        len(_config.sectDict[key]['textList']) - 1)] if len(_config.sectDict[key]['textList']) else ''
            if _config.sectDict[key]['mode'] in ('single', 'random', 'circle', 'bindToKey'):
                _config.wasReplaced[key] = True
        text = _config.textStack.get(key)
        if text is not None:
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


def new_destroyGUI(self):
    old_destroyGUI(self)
    if _config.data['enabled'] and _config.data['reReadAtEnd']:
        _config.wasReplaced = dict.fromkeys(_config.wasReplaced.keys(), False)


def new_construct(self):
    block = old_construct(self)
    from gui.Scaleform.locale.RES_ICONS import RES_ICONS
    from gui.shared.formatters import text_styles, icons
    from gui.shared.items_parameters import formatters as params_formatters, bonus_helper
    from gui.shared.utils.functions import stripColorTagDescrTags
    from helpers.i18n import makeString as _ms
    from items import ITEM_TYPES
    if self.module.itemTypeID == ITEM_TYPES.optionalDevice:
        if bonus_helper.isSituationalBonus(self.module.name):
            effectDesc = text_styles.bonusPreviewText(stripColorTagDescrTags(_ms(self.module.fullDescription)))
            # noinspection PyArgumentEqualDefault
            icon = icons.makeImageTag(RES_ICONS.MAPS_ICONS_TOOLTIP_ASTERISK_OPTIONAL, 16, 16, 0, 4)
            desc = params_formatters.packSituationalIcon(effectDesc, icon)
        else:
            desc = text_styles.bonusAppliedText(stripColorTagDescrTags(_ms(self.module.fullDescription)))
        block[0]['data']['blocksData'][1]['data']['text'] = desc
    return block


def new_setModuleInfoS(self, moduleInfo):
    moduleInfo['description'] = re.sub(r'<[^>]*>', '', moduleInfo['description'])
    old_setModuleInfoS(self, moduleInfo)


# noinspection PyGlobalUndefined
def ButtonReplacer_hooks():
    global old_destroyGUI, old_setModuleInfoS, old_construct
    from Avatar import PlayerAvatar
    from gui.Scaleform.daapi.view.meta.ModuleInfoMeta import ModuleInfoMeta
    from gui.shared.tooltips.module import EffectsBlockConstructor
    old_destroyGUI = PlayerAvatar._PlayerAvatar__destroyGUI
    PlayerAvatar._PlayerAvatar__destroyGUI = new_destroyGUI
    old_setModuleInfoS = ModuleInfoMeta.as_setModuleInfoS
    ModuleInfoMeta.as_setModuleInfoS = new_setModuleInfoS
    old_construct = EffectsBlockConstructor.construct
    EffectsBlockConstructor.construct = new_construct


BigWorld.callback(0.0, ButtonReplacer_hooks)
statistic_mod = PYmodsCore.Analytics(_config.ID, _config.version, 'UA-76792179-1', _config.confMeta)
