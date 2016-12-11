# -*- coding: utf-8 -*-
import glob
import os
import traceback

import BigWorld

import PYmodsCore
from debug_utils import LOG_ERROR, LOG_WARNING


def __dir__():
    return ['i18n_hook_makeString']


class _BR_Config(PYmodsCore._Config):
    def __init__(self):
        super(_BR_Config, self).__init__(__file__)
        self.version = '2.0.0 (%s)' % self.version
        self.configPath = './res_mods/configs/%s/' % self.ID
        self.data = {'enabled': True,
                     'reReadAtEnd': True}
        self.i18n = {
            'UI_description': 'Button Replacer',
            'UI_setting_reReadAtEnd_text': 'Re-read texts from configs after battle is over',
            'UI_setting_reReadAtEnd_tooltip': (
                '{HEADER}Description:{/HEADER}{BODY}This setting allows the mod to re-read texts from configs while '
                'client is in process of hangar loading.{/BODY}'),
            'UI_setting_meta_text': 'Configs loaded: {totalCfg}, texts changed: {keys}',
            'UI_setting_meta_tooltip': '{HEADER}Loaded configs:{/HEADER}',
            'UI_setting_meta_no_configs': '{BODY}No configs were loaded.{/BODY}',
            'UI_setting_meta_configs': '{BODY}{/BODY}',
            'UI_setting_NDA': ' • No data available or provided.'}
        self.textStack = {}
        self.wasReplaced = {}
        self.textId = {}
        self.configsList = []
        self.confMeta = {}
        self.sectDict = {}
        self.loadLang()

    def template_settings(self):
        tooltipStr = self.i18n['UI_setting_meta_tooltip']
        if not len(self.configsList):
            tooltipStr += self.i18n['UI_setting_meta_no_configs']
        else:
            tooltipStrSuff = self.i18n['UI_setting_meta_configs']
            for config in sorted(self.configsList, key=str.lower):
                tooltipStrSuff = tooltipStrSuff.replace('{/BODY}', '%s\n%s\n{/BODY}' % (
                    self.confMeta[config]['name'].rstrip(), self.confMeta[config]['desc'].rstrip()))

            tooltipStr += tooltipStrSuff
        return {'modDisplayName': self.i18n['UI_description'],
                'settingsVersion': 200,
                'enabled': self.data['enabled'],
                'column1': [{'type': 'Label',
                             'text': self.i18n['UI_setting_meta_text'].format(
                                 totalCfg=len(self.configsList), keys=len(self.sectDict)),
                             'tooltip': tooltipStr}],
                'column2': [{'type': 'CheckBox',
                             'text': self.i18n['UI_setting_reReadAtEnd_text'],
                             'value': self.data['reReadAtEnd'],
                             'tooltip': self.i18n['UI_setting_reReadAtEnd_tooltip'],
                             'varName': 'reReadAtEnd'}]}

    def apply_settings(self, settings):
        super(_BR_Config, self).apply_settings(settings)
        _gui_config.update_template('%s' % self.ID, self.template_settings)

    def update_settings(self, doPrint=False):
        super(_BR_Config, self).update_settings()
        _gui_config.updateFile('%s' % self.ID, self.data, self.template_settings)

    def update_data(self, doPrint=False):
        super(_BR_Config, self).update_data(doPrint)
        self.configsList = []
        self.confMeta = {}
        self.sectDict = {}
        if os.path.isdir(self.configPath):
            if doPrint:
                print '%s: loading configs from %s:' % (self.ID, self.configPath)
            for conp in glob.iglob(self.configPath + '*.json'):
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
                            if isinstance(confdict[key]['text'], basestring):
                                textList.append(confdict[key]['text'].rstrip())
                            elif isinstance(confdict[key]['text'], list):
                                textList.append(
                                    ''.join(filter(None, confdict[key]['text'])).rstrip())
                        else:
                            if isinstance(confdict[key]['text'], basestring):
                                textList.extend(filter(
                                    None, map(lambda txtStr: txtStr.rstrip(), confdict[key]['text'].split(';'))))
                            elif isinstance(confdict[key]['text'], list):
                                textList.extend(filter(
                                    None, map(lambda txtStr: txtStr.rstrip(), confdict[key]['text'])))

        elif doPrint:
            print '%s: config directory not found: %s' % (self.ID, self.configPath)

        for key in self.sectDict:
            self.sectDict[key]['textList'] = PYmodsCore.remDups(self.sectDict[key]['textList'])


_config = _BR_Config()
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


class _Analytics(PYmodsCore.Analytics):
    def __init__(self):
        super(_Analytics, self).__init__()
        self.mod_description = 'ButtonReplacer'
        self.mod_id_analytics = 'UA-76792179-1'
        self.mod_version = '2.0.0'
        self.analytics_started = False
        self.playerName = ''
        self.old_playerName = ''
        self.lang = ''
        self.user = None
        self.old_user = None

    def analytics_start(self):
        if not self.analytics_started:
            from constants import AUTH_REALM
            import urllib
            import urllib2
            from helpers import getClientLanguage
            self.lang = str(getClientLanguage()).upper()
            param = urllib.urlencode({
                'v': 1,  # Version.
                'tid': '%s' % self.mod_id_analytics,  # Код мода для сбора статистики
                'cid': '%s' % self.user,  # ID пользователя
                't': 'screenview',  # Screenview hit type.
                'an': '%s' % self.mod_description,  # Имя мода
                'av': '%s %s' % (self.mod_description, self.mod_version),  # App version.
                'cd': '%s (Cluster: [%s], lang: [%s])' % (self.playerName, AUTH_REALM, self.lang),
                'ul': '%s' % self.lang,
                'aid': '%s' % _config.confMeta.keys()[0].split('.')[0] if _config.confMeta else '(not set)',
                'sc': 'start'
            })
            urllib2.urlopen(url='http://www.google-analytics.com/collect?', data=param).read()
            for confName in _config.confMeta.keys()[1:]:
                param = urllib.urlencode({
                    'v': 1,  # Version.
                    'tid': '%s' % self.mod_id_analytics,  # Код мода для сбора статистики
                    'cid': '%s' % self.user,  # ID пользователя
                    't': 'event',  # event hit type.
                    'an': '%s' % self.mod_description,  # Имя мода
                    'av': '%s %s' % (self.mod_description, self.mod_version),  # App version.
                    'cd': '%s (Cluster: [%s], lang: [%s])' % (self.playerName, AUTH_REALM, self.lang),
                    'ul': '%s' % self.lang,
                    'aid': '%s' % confName.split('.')[0]
                })
                urllib2.urlopen(url='http://www.google-analytics.com/collect?', data=param).read()
            self.analytics_started = True
            self.old_user = BigWorld.player().databaseID
            self.old_playerName = BigWorld.player().name


statistic_mod = _Analytics()


def new_fini():
    try:
        statistic_mod.end()
    except StandardError:
        traceback.print_exc()
    old_fini()


def new_populate(self):
    old_populate(self)
    try:
        statistic_mod.start()
    except StandardError:
        traceback.print_exc()


# noinspection PyGlobalUndefined
def ButtonReplacer_hooks():
    global old_fini, old_destroyGUI, old_populate, _gui_config
    try:
        from gui.mods import mod_PYmodsGUI
    except ImportError:
        mod_PYmodsGUI = None
        print 'ButtonReplacer: no-GUI mode activated'
    except StandardError:
        mod_PYmodsGUI = None
        traceback.print_exc()
    _gui_config = getattr(mod_PYmodsGUI, 'g_gui', None)
    import game
    old_fini = game.fini
    game.fini = new_fini
    from Avatar import PlayerAvatar
    old_destroyGUI = PlayerAvatar._PlayerAvatar__destroyGUI
    PlayerAvatar._PlayerAvatar__destroyGUI = new_destroyGUI
    from gui.Scaleform.daapi.view.lobby.LobbyView import LobbyView
    old_populate = LobbyView._populate
    LobbyView._populate = new_populate


BigWorld.callback(0.0, ButtonReplacer_hooks)
