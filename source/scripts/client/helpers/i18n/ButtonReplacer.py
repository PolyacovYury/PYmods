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
        super(_BR_Config, self).__init__('%(mod_ID)s')
        self.version = '2.1.1 (%(file_compile_date)s)'
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
        super(_BR_Config, self).update_data()
        self.configsList = []
        self.confMeta = {}
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
            print '%s: config directory not found: %s' % (self.ID, configPath)

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
        self.mod_description = _config.ID
        self.mod_version = _config.version.split(' ', 1)[0]
        self.mod_id_analytics = 'UA-76792179-1'
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
    global old_fini, old_destroyGUI, old_populate
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
