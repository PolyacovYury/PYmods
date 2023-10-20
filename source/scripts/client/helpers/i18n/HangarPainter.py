# -*- coding: utf-8 -*-
import BigWorld
import re
import traceback
import urllib2
from OpenModsCore import Analytics, SimpleConfigInterface, config, loadJson, overrideMethod
from debug_utils import LOG_ERROR


class ConfigInterface(SimpleConfigInterface):
    def __init__(self):
        self.backupData = {}
        self.blacklists = {}
        super(ConfigInterface, self).__init__()

    def init(self):
        self.ID = '%(mod_ID)s'
        self.version = '1.2.0.2 (%(file_compile_date)s)'
        self.author = 'by Polyacov_Yury'
        self.modsGroup = 'PYmods'
        self.modSettingsID = 'PYmodsGUI'
        self.data = {
            'enabled': True,
            'debug': True,
            'debugColour': True,
            'debugBegin': 0,
            'crewColour': True,
            'colour': '66CC00',
        }
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
            'UI_restart_restart': 'Restart',
            'UI_restart_shutdown': 'Shutdown',
        }
        super(ConfigInterface, self).init()

    def createTemplate(self):
        colourLabel = self.tb.createControl('colour', self.tb.types.ColorChoice)
        colourLabel['text'] = self.tb.getLabel('colourCheck')
        colourLabel['tooltip'] %= {'colour': self.data['colour']}
        return {'modDisplayName': self.i18n['UI_description'],
                'enabled': self.data['enabled'],
                'column1': [colourLabel],
                'column2': [self.tb.createControl('crewColour')]}

    def onApplySettings(self, settings):
        for setting in settings:
            if setting in ('colour', 'enabled') and setting not in self.backupData:
                self.backupData[setting] = self.data[setting]

        super(ConfigInterface, self).onApplySettings(settings)

    def onMSADestroy(self):
        if any(self.data[setting] != self.backupData[setting] for setting in self.backupData):
            self.onRequestRestart(self.data[key] != self.backupData.get(key, self.data[key]) for key in ('colour', 'enabled'))
        self.backupData = {}

    def readCurrentSettings(self, quiet=True):
        self.blacklists = loadJson(self.ID, 'blacklist', self.blacklists, self.configPath)

    @staticmethod
    def onRestartConfirmed(confirm):
        BigWorld.savePreferences()
        if confirm:
            BigWorld.restartGame()
        else:
            BigWorld.quit()

    def onRequestRestart(self, reason):
        colourChanged, toggled = reason
        reasons = []
        if colourChanged:
            reasons.append(self.i18n['UI_restart_reason_colourChanged'])
        if toggled:
            reasons.append(self.i18n['UI_restart_reason_mod' + ('Enabled' if self.data['enabled'] else 'Disabled')])
        dialogText = self.i18n['UI_restart_text'].format(reason='; '.join(reasons))
        from OpenModsCore.delayed import showConfirmDialog
        showConfirmDialog(self.i18n['UI_restart_header'], dialogText,
                          [self.i18n['UI_restart_%s' % act] for act in ('restart', 'shutdown')], self.onRestartConfirmed)

    def load(self):
        try:
            webConf_url = 'https://gist.githubusercontent.com/PolyacovYury/220e5da411d78e598687b23ab130e922/raw/'
            webConf = config.json_reader.JSONLoader.json_loads(urllib2.urlopen(webConf_url).read())
            loadJson(self.ID, 'blacklist', webConf, self.configPath, True)
        except urllib2.URLError as e:
            if hasattr(e, 'reason'):
                print self.LOG, 'blacklists config download failed:', e.reason
            elif hasattr(e, 'code'):
                print self.LOG, 'GitHub internal error:', e.code
        super(ConfigInterface, self).load()

    def registerHotkeys(self):
        BigWorld.callback(0, super(ConfigInterface, self).registerHotkeys)

    def registerSettings(self):
        BigWorld.callback(0, super(ConfigInterface, self).registerSettings)


_config = ConfigInterface()
i18nHooks = ('i18n_hook_makeString',)
TAG_RE = re.compile(r'<[^>]+>')
remove_tags = lambda a: TAG_RE.sub('', str(a)) if isinstance(a, basestring) else a


def old_makeString(*_, **__):
    return LOG_ERROR('i18n hook failed')


def i18n_hook_makeString(key, *args, **kw):
    if not _config.data['enabled'] or not key or key[0] != '#':  # already translated text still needs arguments filled in
        return old_makeString(key, *args, **kw)
    try:
        moName, subkey = key[1:].split(':', 1)
        if not moName or not subkey:
            return key
        moFile = '#' + moName
        identity = {listType: any(
            moKey in moFile and (not idList[moKey] or any(re.search(x, subkey) for x in idList[moKey]))
            for moKey in idList) for listType, idList in _config.blacklists.iteritems()}
        if moFile == '#menu' and subkey.startswith('tankmen/') and len(subkey.split('/')) == 2:
            from CurrentVehicle import g_currentVehicle  # this can't be in the script header
            if g_currentVehicle.isPresent() and g_currentVehicle.item.type in subkey:  # don't recolor mismatches
                identity['commonBlacklist'] = False  # fix for tankmen popover
        whitelist = _config.blacklists['commonWhitelist']
        identity['commonWhitelist'] = any(
            moKey in moFile and any(x == subkey for x in whitelist[moKey]) for moKey in whitelist)
        if identity['commonBlacklist'] and not identity['commonWhitelist']:
            return old_makeString(key, *tuple(remove_tags(a) for a in args), **{k: remove_tags(v) for k, v in kw.iteritems()})
        if _config.data['debug']:
            if _config.data['debugColour']:
                return "<font color='#%s'>%s</font>" % (_config.data['colour'], subkey)
            return key[_config.data['debugBegin']:]
        translation = old_makeString(key, *args, **kw)
        if translation.strip() and translation not in (key, subkey):
            return "<font color='#%s'>%s</font>" % (_config.data['colour'], translation)
        else:
            return translation
    except StandardError:
        print _config.LOG, 'error at', key
        traceback.print_exc()
        return old_makeString(key, *args, **kw)


def delayedHooks():
    from gui.Scaleform.daapi.view.dialogs import I18nDialogMeta
    from gui.shared.tooltips.tankman import TankmanSkillListField, ToolTipAttrField, TankmanRoleLevelField, \
        TankmanCurrentVehicleAttrField

    @overrideMethod(I18nDialogMeta, '__init__')
    def new_I18nDialog_init(base, self, *args, **kwargs):
        base(self, *args, **kwargs)
        if _config.data['enabled']:
            for key in self._messageCtx:
                if isinstance(self._messageCtx[key], basestring):
                    self._messageCtx[key] = TAG_RE.sub('', self._messageCtx[key])

    @overrideMethod(TankmanSkillListField, '_getValue')
    def new_tankmanSkill_getValue(base, self, *args, **kwargs):
        result = base(self, *args, **kwargs)
        if _config.data['enabled']:
            for skill in result:
                skill['label'] = "<font color='#%s'>%s</font>" % (_config.data['colour'], skill['label'])
        return result

    @overrideMethod(ToolTipAttrField, '_getValue')
    @overrideMethod(TankmanRoleLevelField, '_getValue')
    @overrideMethod(TankmanCurrentVehicleAttrField, '_getValue')
    def new_tankmanAttr_getValue(base, self, *args, **kwargs):
        result = base(self, *args, **kwargs)
        if _config.data['enabled'] and self._name in ('name', 'rank', 'role', 'efficiencyRoleLevel', 'currentVehicleName'):
            return "<font color='#%s'>%s</font>" % (_config.data['colour'], result)
        return result


BigWorld.callback(0, delayedHooks)
statistic_mod = Analytics(_config.ID, _config.version, 'UA-76792179-6')
