# -*- coding: utf-8 -*-
import glob
import os
import traceback
import zipfile

import ResMgr

import BigWorld
import PYmodsCore
from debug_utils import LOG_ERROR, LOG_NOTE
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
        self.version = '1.2.0 (%s)' % self.version
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
                     'UI_restart_delete_engine': ' • sections <b>cleared</b> for these banks: ',
                     'UI_restart_move': ' • sections <b>moved</b> for these banks: ',
                     'UI_restart_memory': ' • values <b>changed</b> for memory settings: ',
                     'UI_restart_remap': ' • sections <b>changed</b> for these settings: ',
                     'UI_restart_wotmod': ' • configs <b>removed</b> from these packages: '}
        self.editedBanks = {'create': [], 'delete': [], 'delete_engine': [], 'memory': [], 'move': [], 'remap': set(),
                            'wotmod': []}
        self.was_declined = False
        self.loadLang()

    def updateMod(self):
        pass

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
        fileList = filter(lambda x: x.endswith('.wotmod'), (path for sublist in map(
            lambda x: map(lambda y: '/'.join((x[0], y)).replace(os.sep, '/'), x[2]),
            os.walk(BigWorld.curCV.replace('res_', ''))) for path in sublist))
        for filePath in fileList:
            if os.path.basename(filePath) == '_aaa_BanksLoader_audioMods.wotmod':
                continue
            zip_orig = zipfile.ZipFile(filePath)
            fileNames = zip_orig.namelist()
            if '/'.join(('res', mediaPath, 'audio_mods.xml')) in fileNames:
                self.editedBanks['wotmod'].append(os.path.basename(filePath))
                bankFiles = filter(lambda x: x.startswith('res/' + mediaPath) and x.endswith('.bnk'), fileNames)
                new_filePath = filePath[:-7] + '_BanksLoader_ing' + '.wotmod'
                zip_new = zipfile.ZipFile(new_filePath, 'w')
                for fileName in fileNames:
                    if fileName != '/'.join(('res', mediaPath, 'audio_mods.xml')):
                        zip_new.writestr(fileName, zip_orig.read(fileName))
                    elif bankFiles:
                        zip_new.writestr(bankFiles[0].replace('.bnk', '.xml'), zip_orig.read(fileName))
                zip_new.close()
                zip_orig.close()
                if os.path.isfile(filePath):
                    try:
                        os.remove(filePath)
                    except StandardError:
                        traceback.print_exc()
                if os.path.isfile(new_filePath):
                    os.rename(new_filePath, filePath)
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
        bankFiles = {'mods': set(), 'res': {os.path.basename(path) for path in glob.iglob('./res/' + mediaPath + '/*')}}
        pkg = zipfile.ZipFile('./res/packages/audioww.pkg')
        bankFiles['pkg'] = {os.path.basename(name) for name in pkg.namelist()}
        pkg.close()
        bankFiles['orig'] = bankFiles['res'] | bankFiles['pkg']
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
            for sectName, project in section.items():
                if sectName != 'project':
                    continue
                bankName = project['name'].asString
                if bankName not in bankFiles['orig']:
                    print 'BanksLoader: clearing section for bank', bankName
                    self.editedBanks['delete_engine'].append(bankName)
                    section.deleteSection(project)
        self.editedBanks['delete_engine'] = PYmodsCore.remDups(self.editedBanks['delete_engine'])

        bankFiles['mods'] = set(filter(lambda x: (x.endswith('.bnk') or x.endswith('.pck')) and x not in bankFiles['orig'],
                                       (ResMgr.openSection(mediaPath).keys())))
        audio_mods = ResMgr.openSection('/'.join((mediaPath, 'audio_mods.xml')))
        audio_mods_new = ResMgr.openSection('/'.join((mediaPath, 'audio_mods_edited.xml')), True)
        if audio_mods is None:
            LOG_NOTE('audio_mods.xml not found, will be created if needed')
        else:
            audio_mods_new.copy(audio_mods)
            ResMgr.purge('/'.join((mediaPath, 'audio_mods.xml')))
        bankFiles['ignore'] = set()
        modsKeys = ('events', 'switches', 'RTPCs', 'states')
        confList = filter(lambda x: any(bankFile in x for bankFile in bankFiles['mods']),
                          glob.glob('/'.join((BigWorld.curCV, mediaPath, '*.xml'))))
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
                    continue
                result = {'name': confSect['name'].asString, 'mod': confSect['mod'].asString}
                if key in subList:
                    stateList = []
                    for confSubName, confSubSect in confSect[subList[key]].items():
                        if confSubName != 'state' or not confSubSect.has_key('name') or not confSubSect.has_key('mod'):
                            confSect.deleteSection(confSubSect)
                            self.editedBanks['remap'].add(key)
                            continue
                        stateList.append({'name': confSubSect['name'].asString, 'mod': confSubSect['mod'].asString})
                    result[subList[key]] = stateList
                confData_old[key].append(result)
        confData = {key: [] for key in modsKeys}
        bankConfData = {}
        for confPath in confList:
            confPathShort = confPath.replace(BigWorld.curCV + '/', '')
            confSect = ResMgr.openSection(confPathShort)
            bankName = os.path.basename(confPathShort).replace('.xml', '.bnk')
            bankData = bankConfData[bankName] = {}
            if confSect is None:
                bankFiles['ignore'].add(bankName)
                print '%s: error while reading' % self.ID, confPathShort
                continue
            for key in modsKeys:
                if confSect.has_key(key):
                    existingNames = map(lambda x: x['name'], confData[key])
                    existingMods = map(lambda x: x['mod'], confData[key])
                    bankEvents = bankData[key] = []
                    for sectName, subSect in confSect[key].items():
                        if sectName != key_to_sub[key] or not subSect.has_key('name') or not subSect.has_key('mod'):
                            continue
                        name = subSect['name'].asString
                        mod = subSect['mod'].asString
                        if name in existingNames or mod in existingMods:
                            bankFiles['ignore'].add(bankName)
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
        moddedExist = []
        for bankSect in audio_mods_new['loadBanks'].values():
            bankName = bankSect.asString
            if bankName not in bankFiles['mods'] or bankName in moddedExist or bankName in bankFiles['ignore']:
                print 'BanksLoader: deleting section for bank', bankName
                self.editedBanks['delete'].append(bankName)
                audio_mods_new['loadBanks'].deleteSection(bankSect)
                continue
            moddedExist.append(bankName)
        self.editedBanks['delete'] = PYmodsCore.remDups(self.editedBanks['delete'])
        for bankName in sorted(bankFiles['mods']):
            if bankName not in bankFiles['orig'] and bankName not in moddedExist and bankName not in bankFiles['ignore']:
                print 'BanksLoader: creating sections for bank', bankName
                if bankName in self.editedBanks['delete_engine']:
                    self.editedBanks['delete_engine'].remove(bankName)
                    self.editedBanks['move'].append(bankName)
                else:
                    self.editedBanks['create'].append(bankName)
                audio_mods_new['loadBanks'].createSection('bank').asString = bankName
        for key in modsKeys:
            if confData_old[key] != confData[key]:
                self.editedBanks['remap'].add(key)
            if key in self.editedBanks['remap']:
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

        if any(self.editedBanks[key] for key in ('delete_engine', 'move', 'memory')):
            new_engine.save()
            xmlOrig = BigWorld.curCV + '/engine_config.xml'
            if os.path.isfile(xmlOrig):
                try:
                    os.remove(xmlOrig)
                except StandardError:
                    traceback.print_exc()
            newXml = BigWorld.curCV + '/engine_config_edited.xml'
            if os.path.isfile(newXml):
                os.rename(newXml, xmlOrig)
        else:
            ResMgr.purge('engine_config_edited.xml')
        if any(self.editedBanks[key] for key in ('delete', 'create', 'move', 'remap')):
            audio_mods_new.save()
            origXml = '/'.join((BigWorld.curCV, mediaPath, 'audio_mods.xml'))
            if os.path.isfile(origXml):
                try:
                    os.remove(origXml)
                except StandardError:
                    traceback.print_exc()
            newXml = '/'.join((BigWorld.curCV, mediaPath, 'audio_mods_edited.xml'))
            if os.path.isfile(newXml):
                os.rename(newXml, origXml)
        else:
            ResMgr.purge('audio_mods_edited.xml')
        self.suppress_old_mod()

    def load(self):
        self.update_data(True)
        self.checkConfigs()
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
        self.mod_description = _config.ID
        self.mod_version = _config.version.split(' ', 1)[0]
        self.mod_id_analytics = 'UA-76792179-9'


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
