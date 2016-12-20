# -*- coding: utf-8 -*-
import json
import traceback
import urllib2

import BigWorld
import ResMgr

import PYmodsCore
from debug_utils import LOG_ERROR

res = ResMgr.openSection('../paths.xml')
sb = res['Paths']
vl = sb.values()[0]
if vl is not None and not hasattr(BigWorld, 'curCV'):
    BigWorld.curCV = vl.asString


def __dir__():
    return ['i18n_hook_makeString']


class _HP_Config(PYmodsCore._Config):
    def __init__(self):
        super(_HP_Config, self).__init__(__file__)
        self.version = '1.1.0 (%s)' % self.version
        self.data = {'enabled': True,
                     'debug': True,
                     'debugColour': True,
                     'crewColour': True,
                     'cleanColour': False,
                     'colour': '0097FA'}
        self.backupData = {}
        self.i18n = {
            'UI_description': 'Hangar Painter',
            'UI_setting_colourCheck_text': 'Hangar texts colour:',
            'UI_setting_colour_text': '<font color=\'#%(colour)s\'>Current colour: #%(colour)s</font>',
            'UI_setting_colour_tooltip': (
                'This colour will be applied to all hangar texts.\n'
                '\n<b>WARNING!</b> Restart required for this setting to be applied properly.'),
            'UI_setting_crewColour_text': 'Enable crew texts colouring',
            'UI_setting_crewColour_tooltip': (
                'Crew names, ranks and roles will be coloured, but this sometimes '
                'does not function properly.\n\n<b>WARNING!</b> Restart required for this setting to be applied.'),
            'UI_setting_cleanColour_text': 'Enable clean mode',
            'UI_setting_cleanColour_tooltip': (
                'If disabled, all available texts will be coloured.\nIf enabled, rare cases of "unreadable" texts will be '
                'fixed, but these texts will not be coloured.\n\n<b>WARNING!</b> Restart required for this setting to be '
                'applied.'),
            'UI_restart_header': 'Restart request',
            'UI_restart_text': 'Hangar Painter: {reason}. Client restart required to accept changes.',
            'UI_restart_reason_colourChanged': 'text colour was changed',
            'UI_restart_reason_modDisabled': 'mod was disabled',
            'UI_restart_reason_modEnabled': 'mod was enabled',
            'UI_restart_reason_crewDisabled': 'crew colouring was disabled',
            'UI_restart_reason_crewEnabled': 'crew colouring was enabled',
            'UI_restart_reason_cleanDisabled': 'clean colouring was disabled',
            'UI_restart_reason_cleanEnabled': 'clean colouring was enabled',
            'UI_restart': 'Restart'}
        self.blacklists = {}
        self.needRestart = False
        self.loadLang()

    def template_settings(self):
        colourLabel = self.createLabel('colour')
        colourLabel['text'] = self.getLabel('colourCheck')
        colourLabel['tooltip'] %= {'colour': self.data['colour']}
        return {'modDisplayName': self.i18n['UI_description'],
                'settingsVersion': 200,
                'enabled': self.data['enabled'],
                'column1': [colourLabel,
                            self.createControl('colour', 'TextInputColor', True)],
                'column2': [self.createControl('crewColour'),
                            self.createControl('cleanColour')]}

    def apply_settings(self, settings):
        for setting in settings:
            if setting in ('colour', 'enabled', 'crewColour', 'cleanColour') and setting not in self.backupData:
                self.backupData[setting] = self.data[setting]

        super(_HP_Config, self).apply_settings(settings)

    def onWindowClose(self):
        if any(self.data[setting] != self.backupData[setting] for setting in self.backupData):
            self.onRequestRestart(self.data[key] != self.backupData.get(key, self.data[key]) for key in
                                  ('colour', 'enabled', 'crewColour', 'cleanColour'))
        self.backupData = {}

    def update_data(self, doPrint=False):
        super(_HP_Config, self).update_data(doPrint)
        self.blacklists = self.loadJson('HangarPainter_blacklist', self.blacklists, self.fileDir)

    @staticmethod
    def onRestartConfirmed(*_):
        BigWorld.savePreferences()
        BigWorld.restartGame()

    def onRequestRestart(self, reason):
        colourChanged, toggled, crewChanged, cleanChanged = reason
        reasons = []
        if colourChanged:
            reasons.append(self.i18n['UI_restart_reason_colourChanged'])
        if toggled:
            reasons.append(self.i18n['UI_restart_reason_mod%s' % ('Enabled' if self.data['enabled'] else 'Disabled')])
        if crewChanged:
            reasons.append(
                self.i18n['UI_restart_reason_crew%s' % ('Enabled' if self.data['crewColour'] else 'Disabled')])
        if cleanChanged:
            reasons.append(
                self.i18n['UI_restart_reason_clean%s' % ('Enabled' if self.data['cleanColour'] else 'Disabled')])
        dialogText = self.i18n['UI_restart_text'].format(reason='; '.join(reasons))
        from gui import DialogsInterface
        from gui.Scaleform.daapi.view.dialogs import SimpleDialogMeta, InfoDialogButtons
        DialogsInterface.showDialog(SimpleDialogMeta(self.i18n['UI_restart_header'], dialogText,
                                                     InfoDialogButtons(self.i18n['UI_restart']), None),
                                    self.onRestartConfirmed)

    def load(self):
        try:
            webConf_url = 'https://gist.githubusercontent.com/PolyacovYury/220e5da411d78e598687b23ab130e922/raw/'
            webConf = self.byte_ify(json.loads(urllib2.urlopen(webConf_url).read()))
            self.loadJson('HangarPainter_blacklist', webConf, self.fileDir, True)
        except urllib2.URLError as e:
            if hasattr(e, 'reason'):
                print '%s: blacklists config download failed: ' % self.ID, e.reason
            elif hasattr(e, 'code'):
                print '%s: GitHub internal error: ' % self.ID, e.code
        super(_HP_Config, self).load()

_config = _HP_Config()
_config.load()


def old_makeString(*_, **kwargs):
    _ = kwargs
    LOG_ERROR('i18n hook failed')
    return ''


def i18n_hook_makeString(key, *args, **kwargs):
    if _config.data['enabled']:
        try:
            if not key or key[0] != '#':
                return key
            moName, subkey = key[1:].split(':', 1)
            if not moName or not subkey:
                return key
            moFile = '#' + moName
            identity = {listType: any(
                    moKey in moFile and (not idList[moKey] or any(x in subkey for x in idList[moKey])) for moKey in idList)
                for listType, idList in _config.blacklists.iteritems()}
            identity['commonBlacklist'] = identity['commonBlacklist'] or (
                '#messenger' in moFile and subkey.startswith('server/errors/') and subkey.endswith('/title'))
            whitelist = _config.blacklists['commonWhitelist']
            identity['commonWhitelist'] = any(
                moKey in moFile and any(x == subkey for x in whitelist[moKey]) for moKey in whitelist)
            if not (identity['commonBlacklist'] or
                    identity['crewBlacklist'] and not _config.data['crewColour'] or
                    identity['cleanBlacklist'] and not identity['cleanWhitelist'] and _config.data[
                            'cleanColour']) or identity['commonWhitelist']:
                if not _config.data['debug']:
                    translation = old_makeString(key, *args, **kwargs)
                    if translation.strip() and not translation == subkey:
                        return "<font color='#%s'>%s</font>" % (_config.data['colour'], translation)
                    else:
                        return translation
                elif _config.data['debugColour']:
                    return "<font color='#%s'>%s</font>" % (_config.data['colour'], subkey)
                else:
                    return key
            else:
                return old_makeString(key, *args, **kwargs)
        except StandardError:
            print '%s: error at %s' % (_config.ID, key)
            traceback.print_exc()
            return old_makeString(key, *args, **kwargs)
    else:
        return old_makeString(key, *args, **kwargs)


class _Analytics(PYmodsCore.Analytics):
    def __init__(self):
        super(_Analytics, self).__init__()
        self.mod_description = _config.ID
        self.mod_version = _config.version.split(' ', 1)[0]
        self.mod_id_analytics = 'UA-76792179-6'


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
def HangarPainter_hooks():
    global old_populate, old_fini
    from gui.Scaleform.daapi.view.lobby.LobbyView import LobbyView
    old_populate = LobbyView._populate
    LobbyView._populate = new_populate
    import game
    old_fini = game.fini
    game.fini = new_fini


BigWorld.callback(0.0, HangarPainter_hooks)
