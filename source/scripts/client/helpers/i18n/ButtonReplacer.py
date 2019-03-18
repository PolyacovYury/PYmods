# -*- coding: utf-8 -*-
import BigWorld
import glob
import os
import re
import traceback
from PYmodsCore import PYmodsConfigInterface, loadJson, remDups, pickRandomPart, Analytics, overrideMethod, events
from debug_utils import LOG_ERROR, LOG_WARNING
from functools import partial


class ConfigInterface(PYmodsConfigInterface):
    def __init__(self):
        self.textStack = {}
        self.wasReplaced = {}
        self.textId = {}
        self.configsList = []
        self.confMeta = {}
        self.sectDict = {}
        super(self.__class__, self).__init__()

    def init(self):
        self.ID = '%(mod_ID)s'
        self.version = '2.2.0 (%(file_compile_date)s)'
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
        super(ConfigInterface, self).init()

    def createTemplate(self):
        metaList = ['\n'.join(self.confMeta[x][textType].rstrip() for textType in ('name', 'desc'))
                    for x in sorted(self.configsList, key=str.lower)]
        metaStr = '\n'.join(metaList) if metaList else self.i18n['UI_setting_meta_no_configs']
        capLabel = self.tb.createLabel('meta')
        capLabel['text'] = self.tb.getLabel('caps').format(totalCfg=len(self.configsList), keys=len(self.sectDict))
        capLabel['tooltip'] %= {'meta': metaStr}
        return {'modDisplayName': self.i18n['UI_description'],
                'settingsVersion': 200,
                'enabled': self.data['enabled'],
                'column1': [capLabel],
                'column2': [self.tb.createControl('reReadAtEnd')]}

    def readCurrentSettings(self, quiet=True):
        super(self.__class__, self).readCurrentSettings(quiet)
        self.configsList = []
        self.confMeta.clear()
        self.sectDict = {}
        configPath = self.configPath + 'configs/'
        if os.path.isdir(configPath):
            if not quiet:
                print self.ID + ': loading configs from', configPath + ':'
            for conp in glob.iglob(configPath + '*.json'):
                fileName = os.path.basename(conp)
                confdict = loadJson(self.ID, fileName.split('.')[0], {}, os.path.dirname(conp) + '/')
                if fileName not in self.configsList:
                    self.configsList.append(fileName)
                self.confMeta[fileName] = metaDict = {
                    'name': '<b>%s</b>' % fileName, 'desc': self.i18n['UI_setting_NDA'], 'has': False}
                if 'meta' in confdict:
                    metaDict['name'] = confdict['meta'].get('name', metaDict['name'])
                    metaDict['desc'] = confdict['meta'].get('desc', metaDict['desc'])
                    metaDict['has'] = True
                for key, conf in confdict.iteritems():
                    if key == 'meta':
                        continue
                    section = self.sectDict.setdefault(key, {})
                    section['mode'] = conf['mode']
                    if 'bindToKey' in conf:
                        section['bindToKey'] = conf['bindToKey']
                    textList = section.setdefault('textList', [])
                    text = conf['text']
                    if section['mode'] == 'single':
                        if isinstance(text, list):
                            text = ''.join(x for x in text if x)
                        textList.append(text.rstrip())
                    else:
                        if isinstance(text, str):
                            text = text.split(';')
                        textList.extend(x.rstrip() for x in text if x.rstrip())
            if not quiet:
                print self.ID + ': loaded configs:', ', '.join(self.confMeta)

        elif not quiet:
            print self.ID + ': config directory not found:', configPath

        for key in self.sectDict:
            self.sectDict[key]['textList'] = remDups(self.sectDict[key]['textList'])

    def registerSettings(self):
        BigWorld.callback(0, partial(BigWorld.callback, 0, super(ConfigInterface, self).registerSettings))


_config = ConfigInterface()
i18nHooks = ('i18n_hook_makeString',)


def old_makeString(*_, **__):
    LOG_ERROR('i18n hook failed')


def i18n_hook_makeString(key, *args, **kwargs):
    if _config.data['enabled'] and key in _config.sectDict:
        if key not in _config.wasReplaced or not _config.wasReplaced[key]:
            mode = _config.sectDict[key]['mode']
            textList = _config.sectDict[key]['textList']
            if not textList:
                print _config.ID + ': empty text list for key', key
            else:
                if mode == 'single':
                    _config.textStack[key], _config.textId[key] = textList[0], 0
                elif mode in ('circle', 'random'):
                    _config.textStack[key], _config.textId[key] = pickRandomPart(
                        textList, _config.textId.get(key, -1), mode != 'circle')
                elif mode == 'bindToKey':
                    _config.textStack[key] = textList[
                        min(_config.textId.get(_config.sectDict[key].get('bindToKey', key), 0), len(textList) - 1)]
                if mode in ('single', 'random', 'circle', 'bindToKey'):
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


@events.PlayerAvatar.destroyGUI.after
def new_destroyGUI(*_, **__):
    if _config.data['enabled'] and _config.data['reReadAtEnd']:
        _config.wasReplaced = dict.fromkeys(_config.wasReplaced.keys(), False)


def new_construct(base, self):
    block = base(self)
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


def new_setModuleInfoS(base, self, moduleInfo):
    moduleInfo['description'] = re.sub(r'<[^>]*>', '', moduleInfo['description'])
    base(self, moduleInfo)


def new_setFightButtonS(base, self, label):
    from helpers import i18n
    base(self, i18n.makeString(label))


def ButtonReplacer_hooks():
    from gui.Scaleform.daapi.view.meta.LobbyHeaderMeta import LobbyHeaderMeta
    from gui.Scaleform.daapi.view.meta.ModuleInfoMeta import ModuleInfoMeta
    from gui.shared.tooltips.module import EffectsBlockConstructor
    overrideMethod(ModuleInfoMeta, 'as_setModuleInfoS', new_setModuleInfoS)
    overrideMethod(EffectsBlockConstructor, 'construct', new_construct)
    overrideMethod(LobbyHeaderMeta, 'as_setFightButtonS', new_setFightButtonS)


BigWorld.callback(0.0, ButtonReplacer_hooks)
statistic_mod = Analytics(_config.ID, _config.version, 'UA-76792179-1', _config.confMeta)
