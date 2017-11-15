# -*- coding: utf-8 -*-
import BigWorld
import PYmodsCore
import json
import re
import traceback
import urllib2
from debug_utils import LOG_ERROR
from functools import partial


def __dir__():
    return ['i18n_hook_makeString']


class ConfigInterface(PYmodsCore.PYmodsConfigInterface):
    def __init__(self):
        self.backupData = {}
        self.blacklists = {}
        self.needRestart = False
        super(self.__class__, self).__init__()

    def init(self):
        self.ID = '%(mod_ID)s'
        self.version = '1.2.0.1 (%(file_compile_date)s)'
        self.data = {'enabled': True,
                     'debug': True,
                     'debugColour': True,
                     'debugBegin': 0,
                     'crewColour': True,
                     'colour': '66CC00'}
        self.i18n = {
            'UI_description': 'Hangar Painter',
            'UI_setting_colourCheck_text': 'Hangar texts colour:',
            'UI_setting_colour_text': '<font color=\'#%(colour)s\'>Current colour: #%(colour)s</font>',
            'UI_setting_colour_tooltip': (
                'This colour will be applied to all hangar texts.\n'
                '\n<b>WARNING!</b> Restart is required for this setting to be applied properly.'),
            'UI_setting_crewColour_text': 'Enable crew names colouring',
            'UI_setting_crewColour_tooltip': (
                'Crew names and ranks in the sidebar will be coloured, but it glitches in tankmen replacement '
                'view.\n\nYou will need to select another vehicle for changes to take effect.'),
            'UI_restart_header': 'Restart request',
            'UI_restart_text': 'Hangar Painter: {reason}. Client restart required to accept changes.',
            'UI_restart_reason_colourChanged': 'text colour was changed',
            'UI_restart_reason_modDisabled': 'mod was disabled',
            'UI_restart_reason_modEnabled': 'mod was enabled',
            'UI_restart': 'Restart'}
        super(ConfigInterface, self).init()

    def createTemplate(self):
        colourLabel = self.tb.createControl('colour', 'TextInputColor')
        colourLabel['text'] = self.tb.getLabel('colourCheck')
        colourLabel['tooltip'] %= {'colour': self.data['colour']}
        return {'modDisplayName': self.i18n['UI_description'],
                'settingsVersion': 200,
                'enabled': self.data['enabled'],
                'column1': [colourLabel],
                'column2': [self.tb.createControl('crewColour')]}

    def onApplySettings(self, settings):
        for setting in settings:
            if setting in ('colour', 'enabled') and setting not in self.backupData:
                self.backupData[setting] = self.data[setting]

        super(self.__class__, self).onApplySettings(settings)

    def onMSADestroy(self):
        if any(self.data[setting] != self.backupData[setting] for setting in self.backupData):
            self.onRequestRestart(self.data[key] != self.backupData.get(key, self.data[key]) for key in
                                  ('colour', 'enabled'))
        self.backupData = {}

    def readCurrentSettings(self, quiet=True):
        super(self.__class__, self).readCurrentSettings(quiet)
        self.blacklists = PYmodsCore.loadJson(self.ID, 'blacklist', self.blacklists, self.configPath)

    @staticmethod
    def onRestartConfirmed(*_):
        BigWorld.savePreferences()
        BigWorld.restartGame()

    def onRequestRestart(self, reason):
        colourChanged, toggled = reason
        reasons = []
        if colourChanged:
            reasons.append(self.i18n['UI_restart_reason_colourChanged'])
        if toggled:
            reasons.append(self.i18n['UI_restart_reason_mod%s' % ('Enabled' if self.data['enabled'] else 'Disabled')])
        dialogText = self.i18n['UI_restart_text'].format(reason='; '.join(reasons))
        from gui import DialogsInterface
        from gui.Scaleform.daapi.view.dialogs import SimpleDialogMeta, InfoDialogButtons
        DialogsInterface.showDialog(SimpleDialogMeta(self.i18n['UI_restart_header'], dialogText,
                                                     InfoDialogButtons(self.i18n['UI_restart']), None),
                                    self.onRestartConfirmed)

    def load(self):
        try:
            webConf_url = 'https://gist.githubusercontent.com/PolyacovYury/220e5da411d78e598687b23ab130e922/raw/'
            webConf = PYmodsCore.config.json_reader.JSONLoader.byte_ify(json.loads(urllib2.urlopen(webConf_url).read()))
            PYmodsCore.loadJson(self.ID, 'blacklist', webConf, self.configPath, True)
        except urllib2.URLError as e:
            if hasattr(e, 'reason'):
                print '%s: blacklists config download failed: ' % self.ID, e.reason
            elif hasattr(e, 'code'):
                print '%s: GitHub internal error: ' % self.ID, e.code
        super(self.__class__, self).load()

    def registerSettings(self):
        BigWorld.callback(0, partial(BigWorld.callback, 0, super(ConfigInterface, self).registerSettings))


_config = ConfigInterface()


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
            if moFile == '#menu' and subkey.startswith('tankmen/') and len(subkey.split('/')) == 2:
                from CurrentVehicle import g_currentVehicle
                if g_currentVehicle.isPresent() and g_currentVehicle.item.type in subkey:
                    identity['commonBlacklist'] = False
            whitelist = _config.blacklists['commonWhitelist']
            identity['commonWhitelist'] = any(
                moKey in moFile and any(x == subkey for x in whitelist[moKey]) for moKey in whitelist)
            if not identity['commonBlacklist'] or identity['commonWhitelist']:
                if not _config.data['debug']:
                    translation = old_makeString(key, *args, **kwargs)
                    if translation.strip() and translation not in (key, subkey):
                        return "<font color='#%s'>%s</font>" % (_config.data['colour'], translation)
                    else:
                        return translation
                elif _config.data['debugColour']:
                    return "<font color='#%s'>%s</font>" % (_config.data['colour'], subkey)
                else:
                    return key[_config.data['debugBegin']:]
            else:
                return old_makeString(key, *args, **kwargs)
        except StandardError:
            print '%s: error at %s' % (_config.ID, key)
            traceback.print_exc()
            return old_makeString(key, *args, **kwargs)
    else:
        return old_makeString(key, *args, **kwargs)


def new_as_tankmenResponseS(base, self, data):
    if _config.data['enabled']:
        from CurrentVehicle import g_currentVehicle
        vehicle = g_currentVehicle.item
        for tankmanData in data['tankmen']:
            for key in tankmanData:
                if (key in ('firstName', 'lastName', 'rank') and _config.data['crewColour']) or key == 'role' or \
                        (key == 'vehicleType' and tankmanData[key] == vehicle.shortUserName):
                    tankmanData[key] = "<font color='#%s'>%s</font>" % (_config.data['colour'], tankmanData[key])
        for roleData in data['roles']:
            for key in ('role', 'vehicleType'):
                roleData[key] = "<font color='#%s'>%s</font>" % (_config.data['colour'], roleData[key])
    return base(self, data)


def new_tankmanSkill_getValue(base, self):
    result = base(self)
    if _config.data['enabled']:
        for skill in result:
            skill['label'] = "<font color='#%s'>%s</font>" % (_config.data['colour'], skill['label'])
    return result


def new_tankmanAttr_getValue(base, self):
    result = base(self)
    return ("<font color='#%s'>%s</font>" % (_config.data['colour'], result)
            if _config.data['enabled'] and
            self._name in ('name', 'rank', 'role', 'efficiencyRoleLevel', 'currentVehicleName') else result)


def new_I18nDialog_init(base, self, *args):
    base(self, *args)
    if _config.data['enabled']:
        TAG_RE = re.compile(r'<[^>]+>')
        for key in self._messageCtx:
            self._messageCtx[key] = TAG_RE.sub('', str(self._messageCtx[key]))


def delayedHooks():
    # noinspection PyGlobalUndefined
    global new_as_tankmenResponseS, new_tankmanSkill_getValue, new_I18nDialog_init, new_tankmanAttr_getValue
    from gui.Scaleform.daapi.view.lobby.hangar.Crew import Crew
    from gui.shared.tooltips.tankman import TankmanSkillListField, ToolTipAttrField, TankmanRoleLevelField, \
        TankmanCurrentVehicleAttrField
    from gui.Scaleform.daapi.view.dialogs import I18nDialogMeta
    PYmodsCore.overrideMethod(Crew, 'as_tankmenResponseS')(new_as_tankmenResponseS)
    PYmodsCore.overrideMethod(TankmanSkillListField, '_getValue')(new_tankmanSkill_getValue)
    PYmodsCore.overrideMethod(ToolTipAttrField, '_getValue')(new_tankmanAttr_getValue)
    PYmodsCore.overrideMethod(TankmanRoleLevelField, '_getValue')(new_tankmanAttr_getValue)
    PYmodsCore.overrideMethod(TankmanCurrentVehicleAttrField, '_getValue')(new_tankmanAttr_getValue)
    PYmodsCore.overrideMethod(I18nDialogMeta, '__init__')(new_I18nDialog_init)


BigWorld.callback(0, delayedHooks)
statistic_mod = PYmodsCore.Analytics(_config.ID, _config.version, 'UA-76792179-6')
