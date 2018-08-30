# -*- coding: utf-8 -*-
import BigWorld
import PYmodsCore
import ResMgr
import glob
import os
import traceback
import zipfile
from Avatar import PlayerAvatar
from debug_utils import LOG_ERROR, LOG_NOTE
from gui.Scaleform.daapi.view.dialogs.SimpleDialog import SimpleDialog
from gui.Scaleform.daapi.view.lobby.LobbyView import LobbyView
from gui.Scaleform.daapi.view.login.LoginView import LoginView


class RestartButtons(object):
    def __init__(self, restart, shutdown, close):
        self._restart = restart
        self._shutdown = shutdown
        self._close = close

    def getLabels(self):
        return [
            {'id': 'submit', 'label': self._restart, 'focused': True},
            {'id': 'shutdown', 'label': self._shutdown, 'focused': False},
            {'id': 'close', 'label': self._close, 'focused': False}
        ]


class ConfigInterface(PYmodsCore.PYmodsConfigInterface):
    def __init__(self):
        self.editedBanks = {'create': [], 'delete': [], 'memory': [], 'move': [], 'remap': set(), 'wotmod': []}
        self.was_declined = False
        super(ConfigInterface, self).__init__()

    def init(self):
        self.ID = '%(mod_ID)s'
        self.version = '1.9.6 (%(file_compile_date)s)'
        self.author += ' and Ekspoint'
        self.data = {'defaultPool': 36,
                     'lowEnginePool': 10,
                     'preparedPool': 200,
                     'streamingPool': 8,
                     'IOPoolSize': 8,
                     'max_voices': 110,
                     'debug': False}
        self.i18n = {'UI_restart_header': 'Banks Loader by PY: restart',
                     'UI_restart_text': (
                         'You have installed new audio mods, so the game config was changed. {reason}Client restart '
                         'required to accept changes.\nSound mods proper behaviour <b>NOT GUARANTEED</b> until next '
                         'client start. This will <b>not</b> be required later. Do you want to restart the game now?'),
                     'UI_restart_button_restart': 'Restart',
                     'UI_restart_button_shutdown': 'Shutdown',
                     'UI_restart_button_close': 'Continue',
                     'UI_restart_reason': 'Exact changes:\n{}.\n',
                     'UI_restart_create': ' • sections <b>created</b> for these banks: ',
                     'UI_restart_delete': ' • sections <b>deleted</b> for these banks: ',
                     'UI_restart_move': ' • sections <b>moved</b> for these banks: ',
                     'UI_restart_memory': ' • values <b>changed</b> for memory settings: ',
                     'UI_restart_remap': ' • sections <b>changed</b> for these settings: ',
                     'UI_restart_wotmod': ' • configs <b>removed</b> from these packages: '}
        super(ConfigInterface, self).init()

    def updateMod(self):
        pass

    def createTemplate(self):
        pass

    def onRestartConfirmed(self, buttonID):
        if buttonID == 'submit':
            print self.ID + ': client restart confirmed.'
            BigWorld.savePreferences()
            BigWorld.restartGame()
        elif buttonID == 'shutdown':
            print self.ID + ': client shut down.'
            BigWorld.savePreferences()
            BigWorld.quit()
        else:
            print self.ID + ': client restart declined.'
            self.was_declined = True

    def onRequestRestart(self):
        if self.was_declined:
            return
        if not any(self.editedBanks.values()):
            return
        print self.ID + ': requesting client restart...'
        reasons = []
        if self.data['debug']:
            for key in self.editedBanks:
                if self.editedBanks[key]:
                    reasons.append(self.i18n['UI_restart_' + key] + ', '.join('<b>%s</b>' % x for x in self.editedBanks[key]))
        reasonStr = self.i18n['UI_restart_reason'].format(';\n'.join(reasons)) if reasons else ''
        dialogText = self.i18n['UI_restart_text'].format(reason=reasonStr)
        from gui import DialogsInterface
        from gui.Scaleform.daapi.view.dialogs import SimpleDialogMeta
        DialogsInterface.showDialog(SimpleDialogMeta(self.i18n['UI_restart_header'], dialogText,
                                                     RestartButtons(self.i18n['UI_restart_button_restart'],
                                                                    self.i18n['UI_restart_button_shutdown'],
                                                                    self.i18n['UI_restart_button_close']), None),
                                    self.onRestartConfirmed)

    @staticmethod
    def suppress_old_mod():
        # noinspection SpellCheckingInspection
        oldModName = BigWorld.curCV + '/scripts/client/gui/mods/mod_wg_load_custom_ekspont_banks.pyc'
        if os.path.isfile(oldModName) and os.path.isfile(oldModName + '1'):
            try:
                os.remove(oldModName + '1')
            except StandardError:
                traceback.print_exc()
        if os.path.isfile(oldModName):
            os.rename(oldModName, oldModName + '1')

    def check_wotmods(self, mediaPath):
        audio_mods_xml = 'res/%s/audio_mods.xml' % mediaPath
        for filePath in ('%s/%s' % (x[0], y) for x in os.walk(BigWorld.curCV.replace('res_', '')) for y in x[2]):
            if not filePath.endswith('.wotmod') or os.path.basename(filePath) == '_aaa_BanksLoader_audioMods.wotmod':
                continue
            zip_orig = zipfile.ZipFile(filePath)
            fileNames = zip_orig.namelist()
            if audio_mods_xml in fileNames:
                self.editedBanks['wotmod'].append(os.path.basename(filePath))
                bankFiles = [x for x in fileNames if x.startswith('res/' + mediaPath) and x.endswith('.bnk')]
                new_filePath = filePath[:-7] + '_BanksLoader_ing' + '.wotmod'
                zip_new = zipfile.ZipFile(new_filePath, 'w')
                for fileInfo in zip_orig.infolist():
                    fileName = fileInfo.filename
                    if fileName != audio_mods_xml:
                        zip_new.writestr(fileInfo, zip_orig.read(fileName))
                    elif bankFiles:
                        fileInfo.filename = bankFiles[0].replace('.bnk', '.xml')
                        zip_new.writestr(fileInfo, zip_orig.read(fileName))
                zip_new.close()
                zip_orig.close()
                print self.ID + ': config cleaned from package', os.path.basename(filePath)
                if os.path.isfile(filePath):
                    try:
                        stat = os.stat(filePath)
                        os.remove(filePath)
                    except StandardError:
                        traceback.print_exc()
                if os.path.isfile(new_filePath):
                    os.rename(new_filePath, filePath)
                if os.path.isfile(filePath):
                    os.utime(filePath, (stat.st_atime, stat.st_mtime))
            else:
                zip_orig.close()

    def checkConfigs(self):
        orig_engine = ResMgr.openSection('engine_config.xml')
        if orig_engine is None:
            LOG_ERROR('engine_config.xml not found')
            return
        new_engine = ResMgr.openSection('engine_config_edited.xml', True)
        new_engine.copy(orig_engine)
        ResMgr.purge('engine_config.xml')
        soundMgr = new_engine['soundMgr']
        mediaPath = soundMgr['wwmediaPath'].asString
        self.check_wotmods(mediaPath)
        if self.editedBanks['wotmod']:
            return
        bankFiles = {'mods': set(), 'pkg': set(),
                     'res': {os.path.basename(path) for path in glob.iglob('./res/' + mediaPath + '/*')
                             if (path.endswith('.bnk') or path.endswith('.pck'))}}
        for pkgPath in glob.iglob('./res/packages/audioww*.pkg'):
            with zipfile.ZipFile(pkgPath) as pkg:
                bankFiles['pkg'].update({os.path.basename(name) for name in pkg.namelist()})
        bankFiles['orig'] = bankFiles['res'] | bankFiles['pkg']
        bankFiles['mods'] = set(x for x in ResMgr.openSection(mediaPath).keys()
                                if (x.endswith('.bnk') or x.endswith('.pck')) and x not in bankFiles['orig'])
        bankFiles['all'] = bankFiles['orig'] | bankFiles['mods']
        active_profile_name = soundMgr['WWISE_active_profile'].asString
        active_profile = soundMgr[active_profile_name]
        poolKeys = {'memoryManager': ('defaultPool', 'lowEnginePool', 'preparedPool', 'streamingPool', 'IOPoolSize'),
                    'soundRender': ('max_voices',)}
        for poolKey, poolValuesList in poolKeys.iteritems():
            for poolValue in poolValuesList:
                if active_profile[poolKey][poolValue].asInt != int(self.data[poolValue]):
                    self.editedBanks['memory'].append(poolValue)
                    active_profile[poolKey].writeInt(poolValue, self.data[poolValue])
                    print self.ID + ': changing value for memory setting:', poolValue
        moddedExist = []
        for name, section in active_profile.items():
            if 'soundbanks' not in name:
                continue
            for sectName, project in section.items():
                if sectName != 'project':
                    continue
                bankName = project['name'].asString
                if bankName not in bankFiles['all']:
                    print '%s: clearing engine_config section for bank' % self.ID, bankName
                    self.editedBanks['delete'].append(bankName)
                    section.deleteSection(project)
                elif bankName not in moddedExist:
                    moddedExist.append(bankName)
        audio_mods = ResMgr.openSection(mediaPath + '/audio_mods.xml')
        audio_mods_new = ResMgr.openSection(mediaPath + '/audio_mods_edited.xml', True)
        if audio_mods is None:
            LOG_NOTE('audio_mods.xml not found, will be created if needed')
        else:
            audio_mods_new.copy(audio_mods)
            ResMgr.purge(mediaPath + '/audio_mods.xml')
        bankFiles['ignore'] = set()
        modsKeys = ('events', 'switches', 'RTPCs', 'states')
        confList = [x for x in ResMgr.openSection(mediaPath).keys()
                    if x.endswith('.xml') and x.replace('.xml', '.bnk') in bankFiles['mods'] | bankFiles['orig']]
        for key in ('loadBanks',) + modsKeys:
            if not audio_mods_new.has_key(key):
                audio_mods_new.createSection(key)
        confData_old = {key: [] for key in modsKeys}
        key_to_sub = {'events': 'event', 'RTPCs': 'RTPC', 'switches': 'switch', 'states': 'stateGroup'}
        subList = {'switches': 'states', 'states': 'stateNames'}
        for key in modsKeys:
            conf = audio_mods_new[key]
            for sectName, confSect in conf.items():
                if sectName != key_to_sub[key] or not confSect.has_key('name') or not confSect.has_key('mod'):
                    conf.deleteSection(confSect)
                    self.editedBanks['remap'].add(key)
                    print '%s: cleaned wrong section for setting' % self.ID, key
                    continue
                result = {'name': confSect['name'].asString, 'mod': confSect['mod'].asString}
                if key in subList:
                    stateList = []
                    for confSubName, confSubSect in confSect[subList[key]].items():
                        if confSubName != 'state' or not confSubSect.has_key('name') or not confSubSect.has_key('mod'):
                            confSect.deleteSection(confSubSect)
                            self.editedBanks['remap'].add(key)
                            print '%s: cleaned wrong section for setting' % self.ID, key
                            continue
                        stateList.append({'name': confSubSect['name'].asString, 'mod': confSubSect['mod'].asString})
                    result[subList[key]] = stateList
                confData_old[key].append(result)
        confData = {key: [] for key in modsKeys}
        bankConfData = {}
        for confPath in confList:
            confSect = ResMgr.openSection(mediaPath + '/' + confPath)
            bankName = confPath.replace('.xml', '.bnk')
            bankData = bankConfData[bankName] = {}
            if confSect is None:
                bankFiles['ignore'].add(bankName)
                print '%s: error while reading' % self.ID, confPath
                continue
            for key in modsKeys:
                if confSect.has_key(key):
                    existingNames = [x['name'] for x in confData[key]]
                    existingMods = [x['mod'] for x in confData[key]]
                    bankEvents = bankData[key] = []
                    for sectName, subSect in confSect[key].items():
                        if sectName != key_to_sub[key] or not subSect.has_key('name') or not subSect.has_key('mod'):
                            continue
                        name = subSect['name'].asString
                        mod = subSect['mod'].asString
                        if name in existingNames or mod in existingMods:
                            bankFiles['ignore'].add(bankName)
                            print self.ID + ': duplicate events in', confPath + ': name:', name + ', mod:', mod
                            break
                        result = {'name': name, 'mod': mod}
                        if key in subList:
                            stateList = []
                            for subSectName, stateSect in subSect[subList[key]].items():
                                if subSectName != 'state' or not stateSect.has_key('name') or not stateSect.has_key('mod'):
                                    continue
                                stateList.append({'name': stateSect['name'].asString, 'mod': stateSect['mod'].asString})
                            result[subList[key]] = stateList
                        bankEvents.append(result)
                if bankName in bankFiles['ignore']:
                    del bankConfData[bankName]
                    break
            for key in confData:
                if bankName not in bankFiles['ignore'] and key in bankData:
                    confData[key].extend(bankData[key])
        for bankSect in audio_mods_new['loadBanks'].values():
            bankName = bankSect.asString
            print self.ID + ': clearing audio_mods section for bank', bankName
            self.editedBanks['delete'].append(bankName)
            audio_mods_new['loadBanks'].deleteSection(bankSect)
        self.editedBanks['delete'] = PYmodsCore.remDups(self.editedBanks['delete'])
        bankFiles['orig'] = set(map(str.lower, bankFiles['orig']))
        for bankName in sorted(bankFiles['mods']):
            if bankName not in bankFiles['orig'] and bankName not in moddedExist and bankName not in bankFiles['ignore']:
                print self.ID + ': creating sections for bank', bankName
                if bankName in self.editedBanks['delete']:
                    self.editedBanks['delete'].remove(bankName)
                    self.editedBanks['move'].append(bankName)
                else:
                    self.editedBanks['create'].append(bankName)
                active_profile.createSection('SFX_soundbanks_loadonce/project').writeString('name', bankName)
        for key in modsKeys:
            if confData_old[key] != confData[key]:
                self.editedBanks['remap'].add(key)
            if key in self.editedBanks['remap']:
                print self.ID + ': creating section for setting', key
                audio_mods_new.deleteSection(audio_mods_new[key])
                newSect = audio_mods_new.createSection(key)
                for data in confData[key]:
                    newSubSect = newSect.createSection(key_to_sub[key])
                    for subKey in ('name', 'mod'):
                        newSubSect.createSection(subKey).asString = data[subKey]
                    if key in subList:
                        newSubLSect = newSubSect.createSection(subList[key])
                        for subData in data[subList[key]]:
                            newSubSSect = newSubLSect.createSection('state')
                            for subKey in subData:
                                newSubSSect.createSection(subKey).asString = subData[subKey]

        if any(self.editedBanks[key] for key in ('delete', 'move', 'create', 'memory')):
            new_engine.save()
            xmlOrig = BigWorld.curCV + '/engine_config.xml'
            if os.path.isfile(xmlOrig):
                try:
                    os.remove(xmlOrig)
                except StandardError:
                    traceback.print_exc()
            newXml = './engine_config_edited.xml'
            if os.path.isfile(newXml):
                os.rename(newXml, xmlOrig)
            else:
                newXml = BigWorld.curCV + '/engine_config_edited.xml'
                if os.path.isfile(newXml):
                    os.rename(newXml, xmlOrig)
        else:
            ResMgr.purge('engine_config_edited.xml')
        if any(self.editedBanks[key] for key in ('delete', 'move', 'remap')):
            dirName = BigWorld.curCV + '/' + mediaPath
            if not os.path.exists(dirName):
                os.makedirs(dirName)
            audio_mods_new.save()
            origXml = dirName + '/audio_mods.xml'
            if os.path.isfile(origXml):
                try:
                    os.remove(origXml)
                except StandardError:
                    traceback.print_exc()
            newXml = dirName + '/audio_mods_edited.xml'
            if os.path.isfile(newXml):
                os.rename(newXml, origXml)
        else:
            ResMgr.purge('audio_mods_edited.xml')

    def load(self):
        self.suppress_old_mod()
        self.readCurrentSettings(False)
        self.checkConfigs()
        print self.message() + ': initialised.'


_config = ConfigInterface()
statistic_mod = PYmodsCore.Analytics(_config.ID, _config.version, 'UA-76792179-9')


@PYmodsCore.overrideMethod(SimpleDialog, '_SimpleDialog__callHandler')
def new_callHandler(base, self, buttonID):
    if len(self._SimpleDialog__buttons) == 3:
        self._SimpleDialog__handler(buttonID)
        self._SimpleDialog__isProcessed = True
    else:
        base(self, buttonID)


@PYmodsCore.overrideMethod(LoginView, '_populate')
def new_Login_populate(base, self):
    base(self)
    _config.onRequestRestart()


@PYmodsCore.overrideMethod(LobbyView, '_populate')
def new_Lobby_populate(base, self):
    base(self)
    _config.onRequestRestart()


@PYmodsCore.overrideMethod(PlayerAvatar, '_PlayerAvatar__startGUI')
def new_startGUI(base, *a, **kw):
    base(*a, **kw)
    _config.onRequestRestart()
