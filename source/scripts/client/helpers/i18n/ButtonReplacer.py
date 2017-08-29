# -*- coding: utf-8 -*-
import BigWorld
import PYmodsCore
import glob
import os
import traceback
from debug_utils import LOG_ERROR, LOG_WARNING


def __dir__():
    return ['i18n_hook_makeString']


class _Config(PYmodsCore.Config):
    def __init__(self):
        super(self.__class__, self).__init__('%(mod_ID)s')
        self.version = '2.1.2 (%(file_compile_date)s)'
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
    from gui.Scaleform.locale.RES_ICONS import RES_ICONS
    from gui.Scaleform.locale.TOOLTIPS import TOOLTIPS
    from gui.shared.formatters import text_styles, icons
    from gui.shared.items_parameters import formatters as params_formatters, bonus_helper
    from gui.shared.tooltips import formatters
    from gui.shared.utils.functions import stripColorTagDescrTags
    from helpers.i18n import makeString as _ms
    from items import ITEM_TYPES
    block = []

    def checkLocalization(key):
        localization = _ms('#artefacts:%s' % key)
        return key != localization, localization

    if self.lobbyContext.getServerSettings().spgRedesignFeatures.isStunEnabled():
        isRemovingStun = self.module.isRemovingStun
    else:
        isRemovingStun = False
    onUseStr = '%s/removingStun/onUse' if isRemovingStun else '%s/onUse'
    onUse = checkLocalization(onUseStr % self.module.descriptor.name)
    always = checkLocalization('%s/always' % self.module.descriptor.name)
    restriction = checkLocalization('%s/restriction' % self.module.descriptor.name)
    if bonus_helper.isSituationalBonus(self.module.name):
        effectDesc = text_styles.bonusPreviewText(stripColorTagDescrTags(_ms(self.module.fullDescription)))
        # noinspection PyArgumentEqualDefault
        icon = icons.makeImageTag(RES_ICONS.MAPS_ICONS_TOOLTIP_ASTERISK_OPTIONAL, 16, 16, 0, 4)
        desc = params_formatters.packSituationalIcon(effectDesc, icon)
    else:
        desc = text_styles.bonusAppliedText(stripColorTagDescrTags(_ms(self.module.fullDescription)))
    if self.module.itemTypeID == ITEM_TYPES.optionalDevice:
        block.append(formatters.packTitleDescBlock(title='', desc=desc, padding=formatters.packPadding(top=-8)))
    else:
        topPadding = 0
        if always[0] and len(always[1]) > 0:
            block.append(formatters.packTitleDescBlock(title=text_styles.middleTitle(TOOLTIPS.EQUIPMENT_ALWAYS),
                                                       desc=text_styles.bonusAppliedText(always[1])))
            topPadding = 5
        if onUse[0] and len(onUse[1]) > 0:
            block.append(formatters.packTitleDescBlock(title=text_styles.middleTitle(TOOLTIPS.EQUIPMENT_ONUSE),
                                                       desc=text_styles.main(onUse[1]),
                                                       padding=formatters.packPadding(top=topPadding)))
            topPadding = 5
        if restriction[0] and len(restriction[1]) > 0:
            block.append(formatters.packTitleDescBlock(title=text_styles.middleTitle(TOOLTIPS.EQUIPMENT_RESTRICTION),
                                                       desc=text_styles.main(restriction[1]),
                                                       padding=formatters.packPadding(top=topPadding)))
    return block


def new_MIW_populate(self):
    from gui.shared.formatters import text_styles
    from gui.shared.items_parameters import params_helper, formatters
    from gui.shared.utils import GUN_RELOADING_TYPE, GUN_CAN_BE_CLIP, GUN_CLIP, CLIP_ICON_PATH, EXTRA_MODULE_INFO, \
        HYDRAULIC_ICON_PATH
    from gui.shared.gui_items import GUI_ITEM_TYPE
    from gui.Scaleform.locale.MENU import MENU
    from gui.shared.utils.functions import stripColorTagDescrTags
    from helpers import i18n
    from gui.Scaleform.framework.entities.View import View
    from gui.Scaleform.genConsts.SLOT_HIGHLIGHT_TYPES import SLOT_HIGHLIGHT_TYPES
    import re
    _DEF_SHOT_DISTANCE = 720
    super(View, self)._populate()
    curModule = self.itemsCache.items.getItemByCD(self.moduleCompactDescr)
    description = ''
    if curModule.itemTypeID in (GUI_ITEM_TYPE.OPTIONALDEVICE, GUI_ITEM_TYPE.EQUIPMENT):
        description = stripColorTagDescrTags(curModule.fullDescription)
        description = re.sub(r'<[^>]*>', '', description)
    if curModule.itemTypeID in (GUI_ITEM_TYPE.OPTIONALDEVICE, GUI_ITEM_TYPE.SHELL, GUI_ITEM_TYPE.EQUIPMENT):
        icon = curModule.icon
    else:
        icon = curModule.level
    extraModuleInfo = ''
    moduleData = {'name': curModule.longUserName,
                  'windowTitle': ' '.join([curModule.longUserName, i18n.makeString(MENU.MODULEINFO_TITLE)]),
                  'type': curModule.itemTypeName,
                  'description': description,
                  'level': icon,
                  'params': [],
                  'compatible': [],
                  'effects': {},
                  'moduleLabel': curModule.getGUIEmblemID(),
                  'moduleLevel': curModule.level}
    params = params_helper.get(curModule, self._ModuleInfoWindow__vehicleDescr)
    moduleParameters = params.get('parameters', {})
    formattedModuleParameters = formatters.getFormattedParamsList(curModule.descriptor, moduleParameters)
    extraParamsInfo = params.get('extras', {})
    isGun = curModule.itemTypeID == GUI_ITEM_TYPE.GUN
    isShell = curModule.itemTypeID == GUI_ITEM_TYPE.SHELL
    isChassis = curModule.itemTypeID == GUI_ITEM_TYPE.CHASSIS
    isOptionalDevice = curModule.itemTypeID == GUI_ITEM_TYPE.OPTIONALDEVICE
    excludedParametersNames = extraParamsInfo.get('excludedParams', tuple())
    if isGun:
        if 'maxShotDistance' in moduleParameters:
            if moduleParameters['maxShotDistance'] >= _DEF_SHOT_DISTANCE:
                excludedParametersNames += ('maxShotDistance',)
        gunReloadingType = extraParamsInfo[GUN_RELOADING_TYPE]
        if gunReloadingType == GUN_CLIP:
            description = i18n.makeString(MENU.MODULEINFO_CLIPGUNLABEL)
            extraModuleInfo = CLIP_ICON_PATH
        elif gunReloadingType == GUN_CAN_BE_CLIP:
            otherParamsInfoList = []
            for paramName, paramValue in formattedModuleParameters:
                if paramName in excludedParametersNames:
                    otherParamsInfoList.append({'type': formatters.formatModuleParamName(paramName) + '\n',
                                                'value': text_styles.stats(paramValue)})

            imgPathArr = CLIP_ICON_PATH.split('..')
            imgPath = 'img://gui' + imgPathArr[1]
            moduleData['otherParameters'] = {
                'headerText': i18n.makeString(MENU.MODULEINFO_PARAMETERSCLIPGUNLABEL, imgPath),
                'params': otherParamsInfoList}
    if isChassis:
        if moduleParameters['isHydraulic']:
            description = i18n.makeString(MENU.MODULEINFO_HYDRAULICCHASSISLABEL)
            extraModuleInfo = HYDRAULIC_ICON_PATH
    moduleData['description'] = description
    paramsList = []
    for paramName, paramValue in formattedModuleParameters:
        if paramName not in excludedParametersNames:
            paramsList.append({'type': formatters.formatModuleParamName(paramName) + '\n',
                               'value': text_styles.stats(paramValue)})

    moduleData['parameters'] = {
        'headerText': i18n.makeString(MENU.MODULEINFO_PARAMETERSLABEL) if len(paramsList) > 0 else '',
        'params': paramsList}
    moduleData[EXTRA_MODULE_INFO] = extraModuleInfo
    moduleCompatibles = params.get('compatible', tuple())
    for paramType, paramValue in moduleCompatibles:
        compatible = moduleData.get('compatible')
        compatible.append({'type': i18n.makeString(MENU.moduleinfo_compatible(paramType)),
                           'value': paramValue})

    if curModule.itemTypeID == GUI_ITEM_TYPE.EQUIPMENT:
        effectsNameTemplate = '#artefacts:%s/%s'
        if self.lobbyContext.getServerSettings().spgRedesignFeatures.isStunEnabled():
            isRemovingStun = curModule.isRemovingStun
        else:
            isRemovingStun = False
        onUseStr = 'removingStun/onUse' if isRemovingStun else 'onUse'
        moduleData['effects'] = {'effectOnUse': i18n.makeString(effectsNameTemplate % (curModule.name, onUseStr)),
                                 'effectAlways': i18n.makeString(effectsNameTemplate % (curModule.name, 'always')),
                                 'effectRestriction': i18n.makeString(effectsNameTemplate % (curModule.name, 'restriction'))}
        cooldownSeconds = curModule.descriptor.cooldownSeconds
        if cooldownSeconds > 0:
            moduleData['addParams'] = {'type': formatters.formatModuleParamName('cooldownSeconds') + '\n',
                                       'value': text_styles.stats(cooldownSeconds) + '\n'}
    if isShell and self._ModuleInfoWindow__isAdditionalInfoShow is not None:
        moduleData['additionalInfo'] = self._ModuleInfoWindow__isAdditionalInfoShow
    if isOptionalDevice:
        moduleData['highlightType'] = SLOT_HIGHLIGHT_TYPES.EQUIPMENT_PLUS if curModule.isDeluxe() else SLOT_HIGHLIGHT_TYPES.NO_HIGHLIGHT
    self.as_setModuleInfoS(moduleData)
    self._updateActionButton()


# noinspection PyGlobalUndefined
def ButtonReplacer_hooks():
    global old_destroyGUI
    from Avatar import PlayerAvatar
    from gui.Scaleform.daapi.view.lobby.ModuleInfoWindow import ModuleInfoWindow
    from gui.shared.tooltips.module import EffectsBlockConstructor
    old_destroyGUI = PlayerAvatar._PlayerAvatar__destroyGUI
    PlayerAvatar._PlayerAvatar__destroyGUI = new_destroyGUI
    ModuleInfoWindow._populate = new_MIW_populate
    EffectsBlockConstructor.construct = new_construct


BigWorld.callback(0.0, ButtonReplacer_hooks)
statistic_mod = PYmodsCore.Analytics(_config.ID, _config.version.split(' ', 1)[0], 'UA-76792179-1', _config.confMeta)
