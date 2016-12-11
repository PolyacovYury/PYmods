# -*- coding: utf-8 -*-
import marshal
import os
import traceback

import BigWorld
import ResMgr

from debug_utils import LOG_ERROR


class _Config(object):
    def __init__(self, _):
        self.ID = ''
        self.version = ''
        self.configPath = ''
        self.i18n = {}
        self.tooltipSubs = {}

    def loadLang(self):
        pass

    def apply_settings(self, _):
        pass

    def update_data(self, _=False):
        pass

    # noinspection PyMethodMayBeStatic
    def loadJson(self, *_):
        return {}

    def load(self):
        pass

    def update_settings(self, doPrint=False):
        pass


class Analytics(object):
    def start(self):
        pass

    def end(self):
        pass


def loadPYmodsCore():
    originalFilePath = '%s/scripts/client/gui/mods/PYmodsCore.pyc' % BigWorld.curCV
    if os.path.exists(originalFilePath) and os.path.isfile(originalFilePath):
        with open(originalFilePath, 'rb') as originalFile:
            exec marshal.loads(originalFile.read()[8:]) in globals()
    else:
        raise ImportError('cannot import name PYmodsCore')


res = ResMgr.openSection('../paths.xml')
sb = res['Paths']
vl = sb.values()[0]
if vl is not None and not hasattr(BigWorld, 'curCV'):
    BigWorld.curCV = vl.asString
loadPYmodsCore()


def __dir__():
    return ['i18n_hook_makeString']


class _HP_Config(_Config):
    def __init__(self):
        super(_HP_Config, self).__init__(__file__)
        self.version = '1.0.0 (%s)' % self.version
        self.data = {'enabled': True,
                     'debug': True,
                     'debugColour': True,
                     'crewColour': True,
                     'colour': '0097FA'}
        self.backupData = {}
        self.i18n = {
            'UI_description': 'Hangar Painter',
            'UI_setting_colour_text': 'Hangar texts colour:',
            'UI_setting_colour_tooltip': (
                '{HEADER}<font color=\'#{colour}\'>Current colour: #{colour}</font>{/HEADER}{BODY}This colour will be '
                'applied to all hangar texts.\n'
                '\n<b>WARNING!</b> Restart required for this setting to be applied properly.{/BODY}'),
            'UI_setting_crewColour_text': 'Enable crew texts colouring',
            'UI_setting_crewColour_tooltip': (
                '{HEADER}Description:{/HEADER}{BODY}Crew names, ranks and roles will be coloured, but this sometimes '
                'does not function properly.\n\n<b>WARNING!</b> Restart required for this setting to be applied.{/BODY}'),
            'UI_setting_debug_text': 'Enable debug mode',
            'UI_setting_debug_tooltip': (
                '{HEADER}Description:{/HEADER}{BODY}All texts are replaced with their corresponding keys.\n'
                'This setting is used for fixing purposes only.{/BODY}'),
            'UI_restart_header': 'Restart request',
            'UI_restart_text': 'Hangar Painter: {reason}. Client restart required to accept changes.',
            'UI_restart_reason_colourChanged': 'text colour was changed',
            'UI_restart_reason_modDisabled': 'mod was disabled',
            'UI_restart_reason_modEnabled': 'mod was enabled',
            'UI_restart_reason_crewDisabled': 'crew colouring was disabled',
            'UI_restart_reason_crewEnabled': 'crew colouring was enabled',
            'UI_restart': 'Restart'}
        self.whitelists = {
            '#menu': ['headerButtons/battle', 'headerButtons/ready', 'training/info/timeout/label',
                      'awardWindow/personalMission/nextButtonAward/tooltip/header'],
            '#retrain_crew': ['label/result', 'label/crewMembers']}
        self.crewBlacklist = {'tankmen': [], '#item_types': ['tankman/roles']}
        # noinspection SpellCheckingInspection
        self.blacklists = {
            '#achievements': ['marksOnGun/descr/param/label'],
            '#arenas': [],
            '#artefacts': ['name', 'descr'],
            '#battle_results': ['finish', 'research', 'newSkill', 'purchase'],
            '#battle_tutorial': [],
            '#clans': ['clanProfile/mainWindow/title', 'personnelView/clanStats/avg',
                       'section/fort/view/statistics/sorties/detailed/header',
                       'section/fort/view/statistics/battles/detailed/header',
                       'clanInvitesWindow/tabRequests', 'clanInvitesWindow/tabInvites',
                       'clanInvitesWindow/table/inviteButton', 'clanProfile/sendInvitesWindow/title',
                       'search/info/stats/', 'search/info/clanProfileBtn'],
            '#clubs_quests': [],
            '#crew_operations': [],
            '#cyberSport': ['window/intro/search/btn', 'window/intro/create/btn',
                            'window/clubsListView/foundTeamsDescription', 'window/title'],
            '#dialogs': ['quitBattle', 'addSkillWindow/label', 'disconnected', 'title', 'EULA', 'eula',
                         'replayStopped', 'questsConfirmDialog', 'buyVehicleDialog/cancelBtn',
                         'buyVehicleDialog/submitBtn', '/vehicle/level', '/headerButtons/crew',
                         'vehicleSellDialog/count', 'confirmModuleDialog', 'elite/header',
                         'sellModuleConfirmation', 'common/'],
            '#fortifications': ['levelsLbl', 'General/directionName', 'BuildingDirection/label',
                                'fortNotCommanderFirstEnterWindow/windowTitle',
                                'fortNotCommanderFirstEnterWindow/applyBtnLabel',
                                'clanStats/params/sortie/', 'clanStats/params/periodDefence/',
                                'FortClanListWindow/title', '/windowTitle',
                                'clanStats/params/sortie/battlesCount/tooltip/body',
                                '/buildingName', 'FixedPlayers/header/', 'BuildingPopover/defResActions'],
            '#ingame_gui': [],
            '#ingame_help': [],
            '#invites': ['button'],
            '#item_types': ['tankman/skills', 'shell', '/name'],
            '#menu': ['login', 'headerButtons', 'loading', 'clan', 'tuningBtn', 'maitenanceBtn',
                      'shop/table/find', 'ingame_menu', 'promo/toArchive', 'promo/patch/title',
                      'label', 'descriptions', 'barracks/btnBuyBerthDecs',
                      'barracks/barracksRenderer/placesCount', 'lobby_menu/title',
                      'boostersWindow/title', 'boostersWindow/tabs', 'training/info/states',
                      'customization/buttons/apply', 'exchange/rate', 'copy',
                      'boostersWindow/boostersTableRenderer/activateBtnLabel',
                      'boostersWindow/boostersTableRenderer/buyBtnLabel',
                      'finalStatistic/window/title', 'tankCarousel/vehicleStates',
                      'contextMenu/appeal', 'legal', 'awardWindow/title', 'opponents',
                      'research/premium/benefits/head', 'awardWindow/closeButton',
                      'awardWindow/okButton', 'awardWindow/takeNextButton',
                      'awardWindow/personalMission/nextButton', 'boostersTableRenderer/goToQuestBtnLabel',
                      'dateTime/weekDays/short/', 'moduleInfo/title', 'moduleInfo/compatible',
                      'moduleInfo/additionalInfo', 'contextMenu/personalCase/statsBlockTitle',
                      'tankmanPersonalCase/title', 'training/info/observer', 'training/info/timeout/value'],
            '#messenger': ['listView/title', 'messenger/contacts/title',
                           'dialogs/searchChannel/labels/result', 'searchInput',
                           'battle', 'dialogs/contacts/tree', 'client/dynSquad',
                           'mainGrops/Other/', 'messenger/contacts/mainGroups/other/',
                           'messenger/contacts/dropContactPrompt',
                           'messenger/contacts/searchUsers/', 'dialogs/searchContact/labels/result',
                           'messenger/contacts/view/manageGroup/deleteGroup/groupName/Label',
                           'listView/emptyList'],
            '#nations': [],
            '#prebattle': ['labels/company/division', 'title/battleSession/startTime'],
            '#profile': ['section', 'note', 'attention', 'btnLabel'],
            '#quests': ['tileChainsView/buttonBack/text', 'item/type/', 'item/timer/tillStart/',
                        'details/status/notAvailable', 'details/status/completed',
                        'details/header/completion/', 'details/conditions/',
                        'quests/table', 'details/dossier', 'tileChainsView/taskType/inProgress',
                        'tileChainsView/taskType/awardNotReceived'],
            '#readable_key_names': [],
            '#retrain_crew': ['label', 'window'],
            '#settings': [],
            '#tank_carousel_filter': ['defaultButton'],
            '#tips': [],
            '#tooltips': ['note', 'attention', 'login', '/text', 'clanCommonInfo/ClanName',
                          '/vehicleType'],
            '#vehicle_customization': ['customization/bottomPanel/backBtn'],
            '#veh_compare': ['cartPopover/gotoCompareBtn', 'cartPopover/moduleType',
                             'addVehPopover/btnAdd', 'modulesView/windowTitle'],
            'vehicles': [],
            '#waiting': []}
        self.needRestart = False
        self.loadLang()

    def template_settings(self):
        return {'modDisplayName': self.i18n['UI_description'],
                'settingsVersion': 200,
                'enabled': self.data['enabled'],
                'column1': [{'type': 'TextInputField',
                             'text': self.i18n['UI_setting_colour_text'],
                             'tooltip': self.i18n['UI_setting_colour_tooltip'].format(colour=self.data['colour'],
                                                                                      **self.tooltipSubs),
                             'value': self.data['colour'],
                             'width': 60,
                             'varName': 'colour'}],
                'column2': [{'type': 'CheckBox',
                             'text': self.i18n['UI_setting_crewColour_text'],
                             'value': self.data['crewColour'],
                             'tooltip': self.i18n['UI_setting_crewColour_tooltip'],
                             'varName': 'crewColour'},
                            {'type': 'CheckBox',
                             'text': self.i18n['UI_setting_debug_text'],
                             'value': self.data['debug'],
                             'tooltip': self.i18n['UI_setting_debug_tooltip'],
                             'varName': 'debug'}]}

    def apply_settings(self, settings):
        for setting in settings:
            if setting in ('colour', 'enabled', 'crewColour') and setting not in self.backupData:
                self.backupData[setting] = self.data[setting]

        super(_HP_Config, self).apply_settings(settings)
        _gui_config.update_template('%s' % self.ID, self.template_settings)

    def onWindowClose(self):
        if any(self.data[setting] != self.backupData[setting] for setting in self.backupData):
            self.onRequestRestart(self.data[key] != self.backupData.get(key, self.data[key]) for key in
                                  ('colour', 'enabled', 'crewColour'))
        self.backupData = {}

    @staticmethod
    def onRestartConfirmed(*_):
        BigWorld.savePreferences()
        BigWorld.restartGame()

    def onRequestRestart(self, reason):
        colourChanged, toggled, crewChanged = reason
        reasons = []
        if colourChanged:
            reasons.append(self.i18n['UI_restart_reason_colourChanged'])
        if toggled:
            reasons.append(self.i18n['UI_restart_reason_mod%s' % ('Enabled' if self.data['enabled'] else 'Disabled')])
        if crewChanged:
            reasons.append(
                self.i18n['UI_restart_reason_crew%s' % ('Enabled' if self.data['crewColour'] else 'Disabled')])
        dialogText = self.i18n['UI_restart_text'].format(reason='; '.join(reasons))
        from gui import DialogsInterface
        from gui.Scaleform.daapi.view.dialogs import SimpleDialogMeta, InfoDialogButtons
        DialogsInterface.showDialog(SimpleDialogMeta(self.i18n['UI_restart_header'], dialogText,
                                                     InfoDialogButtons(self.i18n['UI_restart']), None),
                                    self.onRestartConfirmed)

    def update_settings(self, doPrint=False):
        super(_HP_Config, self).update_settings(doPrint)
        _gui_config.updateFile('%s' % self.ID, self.data, self.template_settings)


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
            isBlack = any(moKey in moFile and (
                not _config.blacklists[moKey] or any(x in subkey for x in _config.blacklists[moKey])) for moKey in
                          _config.blacklists)
            isBlack = isBlack or (
                '#messenger' in moFile and subkey.startswith('server/errors/') and subkey.endswith('/title'))
            isNoCrew = any(moKey in moFile and (
                not _config.crewBlacklist[moKey] or any(x in subkey for x in _config.crewBlacklist[moKey])) for moKey in
                           _config.crewBlacklist)
            isWhite = any(moKey in moFile and any(x == subkey for x in _config.whitelists[moKey]) for moKey in
                          _config.whitelists)
            if 'TEST_FEATURE_NOT_IN_CLIENT' in subkey:
                print moFile, not isBlack, not isNoCrew, isWhite
                print tuple((moKey in moFile,
                             not _config.blacklists[moKey], tuple((x, x in subkey) for x in _config.blacklists[moKey]))
                            for moKey in _config.blacklists)
            if not (isBlack or isNoCrew and not _config.data['crewColour']) or isWhite:
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


class _Analytics(Analytics):
    def __init__(self):
        super(_Analytics, self).__init__()
        self.mod_description = 'HangarPainter'
        self.mod_id_analytics = 'UA-76792179-6'
        self.mod_version = '1.0.0'


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
    global old_populate, old_fini, _gui_config
    try:
        from gui.mods import mod_PYmodsGUI
    except ImportError:
        mod_PYmodsGUI = None
        print 'HangarPainter: no-GUI mode activated'
    except StandardError:
        mod_PYmodsGUI = None
        traceback.print_exc()
    _gui_config = getattr(mod_PYmodsGUI, 'g_gui', None)
    from gui.Scaleform.daapi.view.lobby.LobbyView import LobbyView
    old_populate = LobbyView._populate
    LobbyView._populate = new_populate
    import game
    old_fini = game.fini
    game.fini = new_fini


BigWorld.callback(0.0, HangarPainter_hooks)
