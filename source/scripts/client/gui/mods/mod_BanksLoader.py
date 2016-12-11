# -*- coding: utf-8 -*-
import glob
import os
import traceback
import zipfile

import BigWorld
import ResMgr

import PYmodsCore
from debug_utils import LOG_ERROR
from gui.Scaleform.daapi.view.lobby.LobbyView import LobbyView
from gui.Scaleform.daapi.view.login.LoginView import LoginView

res = ResMgr.openSection('../paths.xml')
sb = res['Paths']
vl = sb.values()[0]
if vl is not None and not hasattr(BigWorld, 'curCV'):
    BigWorld.curCV = vl.asString


class _Config(PYmodsCore._Config):
    def __init__(self):
        super(_Config, self).__init__(__file__)
        self.version = '1.1.0 (%s)' % self.version
        self.author = '%s and Ekspoint' % self.author
        self.data = {'defaultPool': 48,
                     'lowEnginePool': 36,
                     'preparedPool': 318,
                     'streamingPool': 48,
                     'IOPoolSize': 32,
                     'max_voices': 310,
                     'debug': False}
        self.i18n = {'UI_restart_header': 'Banks Loader by PY: restart',
                     'UI_restart_text': (
                         'You have installed new audio mods, so the game config was changed. {reason}Client restart '
                         'required to accept changes.\nSound mods proper behaviour <b>NOT GUARANTEED</b> until next '
                         'client start. This will <b>not</b> be required later. Do you want to restart the game now?'),
                     'UI_restart_reason': 'Exact changes:\n{}\n',
                     'UI_restart_create': ' • sections <b>created</b> for these banks: ',
                     'UI_restart_delete': ' • sections <b>deleted</b> for these banks: ',
                     'UI_restart_move': ' • sections <b>moved</b> for these banks: ',
                     'UI_restart_memory': ' • values <b>changed</b> for memory settings: '}
        self.editedBanks = {'create': [], 'delete': [], 'memory': [], 'move': []}
        self.bankGroupsConfig = {'all': set()}
        self.was_declined = False
        self.loadLang()

    def update_data(self, doPrint=False):
        super(_Config, self).update_data(doPrint)
        if not os.path.isdir(self.configPath):
            return
        for configPath in glob.iglob(self.configPath + '*.json'):
            confPath = configPath.replace('%s/' % BigWorld.curCV, '')
            try:
                confdict = self.loadJson(os.path.basename(configPath).split('.')[0], {}, os.path.dirname(configPath) + '/')
            except StandardError:
                print 'BanksLoader: config %s is invalid.' % os.path.basename(confPath)
                traceback.print_exc()
                continue
            for groupName in confdict:
                self.bankGroupsConfig.setdefault(groupName, set()).update(confdict[groupName])
                self.bankGroupsConfig['all'].update(confdict[groupName])

    def onRestartConfirmed(self, proceed):
        if proceed:
            print '%s: client restart confirmed.' % self.ID
            BigWorld.savePreferences()
            BigWorld.restartGame()
        else:
            print '%s: client restart declined.' % self.ID
            self.was_declined = True

    def onRequestRestart(self):
        if self.was_declined:
            return
        if not any(self.editedBanks.values()):
            return
        print '%s: requesting client restart...' % self.ID
        reasons = []
        if self.data['debug']:
            for key in self.editedBanks:
                if self.editedBanks[key]:
                    reasons.append(self.i18n['UI_restart_' + key] + ', '.join(
                        (bankName.join(('<b>', '</b>')) for bankName in self.editedBanks[key])))
        reasonStr = self.i18n['UI_restart_reason'].format(';\n'.join(reasons)) if reasons else ''
        dialogText = self.i18n['UI_restart_text'].format(reason=reasonStr)
        from gui import DialogsInterface
        from gui.Scaleform.daapi.view.dialogs import I18nConfirmDialogButtons, SimpleDialogMeta
        DialogsInterface.showDialog(SimpleDialogMeta(self.i18n['UI_restart_header'], dialogText,
                                                     I18nConfirmDialogButtons('common/confirm'), None),
                                    self.onRestartConfirmed)

    def engineConfigReader(self):
        orig_config = ResMgr.openSection('engine_config.xml')
        if orig_config is None:
            LOG_ERROR('engine_config.xml not found')
            return
        config = ResMgr.openSection('engine_config_edited.xml', True)
        config.copy(orig_config)
        ResMgr.purge('engine_config.xml')
        soundMgr = config['soundMgr']
        mediaPath = soundMgr['wwmediaPath'].asString
        bankFiles = {'mods': set(), 'res': {os.path.basename(path) for path in glob.iglob('./res/' + mediaPath + '/*')}}
        pkg = zipfile.ZipFile('./res/packages/audioww.pkg')
        bankFiles['pkg'] = {os.path.basename(name) for name in pkg.namelist()}
        pkg.close()
        if os.path.isdir(BigWorld.curCV + '/' + mediaPath):
            bankFiles['mods'] = set(filter(lambda x: x.endswith('.bnk') or x.endswith('.pck'),
                                           (os.path.basename(path) for path in
                                            glob.iglob(BigWorld.curCV + '/' + mediaPath + '/*'))))
        bankFiles['all'] = bankFiles['res'] | bankFiles['pkg'] | bankFiles['mods']
        confBanks = {'all': []}
        active_profile_name = soundMgr['WWISE_active_profile'].asString
        active_profile = soundMgr[active_profile_name]
        poolKeys = {'memoryManager': ['defaultPool', 'lowEnginePool', 'preparedPool', 'streamingPool', 'IOPoolSize'],
                    'soundRender': ['max_voices']}
        for poolKey, poolValuesList in poolKeys.iteritems():
            for poolValue in poolValuesList:
                if active_profile[poolKey][poolValue].asInt != int(self.data[poolValue]):
                    self.editedBanks['memory'].append(poolValue)
                    active_profile[poolKey].writeInt(poolValue, self.data[poolValue])
        for name, section in active_profile.items():
            if 'soundbanks' not in name:
                continue
            confBanks[name] = []
            for sectName, project in section.items():
                if sectName != 'project':
                    continue
                bankName = project['name'].asString
                if bankName not in bankFiles['all'] or bankName in self.bankGroupsConfig[
                        'all'] and bankName not in self.bankGroupsConfig.get(name, set()):
                    print 'BanksLoader: deleting section for bank', bankName
                    self.editedBanks['delete'].append(bankName)
                    section.deleteSection(project)
                    continue
                confBanks['all'].append(bankName)
                confBanks[name].append(bankName)
        self.editedBanks['delete'] = PYmodsCore.remDups(self.editedBanks['delete'])
        for bankName in bankFiles['mods']:
            if bankName not in confBanks['all']:
                print 'BanksLoader: creating sections for bank', bankName
                if bankName in self.editedBanks['delete']:
                    self.editedBanks['delete'].remove(bankName)
                    self.editedBanks['move'].append(bankName)
                else:
                    self.editedBanks['create'].append(bankName)
                if bankName in self.bankGroupsConfig['all']:
                    for groupName in self.bankGroupsConfig:
                        if groupName == 'all':
                            continue
                        if bankName in self.bankGroupsConfig[groupName]:
                            active_profile[groupName].createSection('project').writeString('name', bankName)
                elif bankName.endswith('.bnk') and active_profile['SFX_soundbanks_common'] is not None:
                    active_profile['SFX_soundbanks_common'].createSection('project').writeString('name', bankName)
                else:
                    active_profile['SFX_soundbanks_loadonce'].createSection('project').writeString('name', bankName)
        if not any(self.editedBanks.values()):
            return
        config.save()
        if os.path.isfile(BigWorld.curCV + '/engine_config.xml'):
            try:
                os.remove(BigWorld.curCV + '/engine_config.xml')
            except StandardError:
                traceback.print_exc()
        if os.path.isfile(BigWorld.curCV + '/engine_config_edited.xml'):
            os.rename(BigWorld.curCV + '/engine_config_edited.xml', BigWorld.curCV + '/engine_config.xml')
        # noinspection SpellCheckingInspection
        oldModName = BigWorld.curCV + '/scripts/client/gui/mods/mod_wg_load_custom_ekspont_banks.pyc'
        if os.path.isfile(oldModName) and os.path.isfile(oldModName + '1'):
            try:
                os.remove(oldModName + '1')
            except StandardError:
                traceback.print_exc()
        if os.path.isfile(oldModName):
            os.rename(oldModName, oldModName + '1')

    def load(self):
        self.update_data(True)
        self.engineConfigReader()
        print '%s: initialised.' % (self.message())


_config = _Config()
_config.load()


def new_Login_populate(self):
    old_Login_populate(self)
    _config.onRequestRestart()


old_Login_populate = LoginView._populate
LoginView._populate = new_Login_populate


class Analytics(PYmodsCore.Analytics):
    def __init__(self):
        super(Analytics, self).__init__()
        self.mod_description = 'BanksLoader'
        self.mod_id_analytics = 'UA-76792179-9'
        self.mod_version = '1.1.0'


statistic_mod = Analytics()


def fini():
    try:
        statistic_mod.end()
    except StandardError:
        traceback.print_exc()


def new_LW_populate(self):
    old_LW_populate(self)
    try:
        statistic_mod.start()
    except StandardError:
        traceback.print_exc()
    _config.onRequestRestart()


old_LW_populate = LobbyView._populate
LobbyView._populate = new_LW_populate
