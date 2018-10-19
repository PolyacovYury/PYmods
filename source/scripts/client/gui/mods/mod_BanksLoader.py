# -*- coding: utf-8 -*-
import BigWorld
import ResMgr
import glob
import os
import traceback
import zipfile
from Avatar import PlayerAvatar
from PYmodsCore import PYmodsConfigInterface, remDups, Analytics, overrideMethod, showConfirmDialog
from debug_utils import LOG_ERROR, LOG_NOTE
from gui.Scaleform.daapi.view.dialogs import DIALOG_BUTTON_ID
from gui.Scaleform.daapi.view.lobby.LobbyView import LobbyView
from gui.Scaleform.daapi.view.login.LoginView import LoginView


class ConfigInterface(PYmodsConfigInterface):
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
        if buttonID == DIALOG_BUTTON_ID.SUBMIT:
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
        if not any(self.editedBanks.itervalues()):
            return
        print self.ID + ': requesting client restart...'
        reasons = []
        if self.data['debug']:
            reasons = [
                self.i18n['UI_restart_' + key] + ', '.join('<b>%s</b>' % x for x in remDups(self.editedBanks[key]))
                for key in self.editedBanks if self.editedBanks[key]]
        reasonStr = self.i18n['UI_restart_reason'].format(';\n'.join(reasons)) if reasons else ''
        dialogText = self.i18n['UI_restart_text'].format(reason=reasonStr)
        showConfirmDialog(
            self.i18n['UI_restart_header'], dialogText,
            [self.i18n['UI_restart_button_%s' % key] for key in ('restart', 'shutdown', 'close')], self.onRestartConfirmed)

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

    def check_order(self, order, filePath, new_filePath):
        modsRoot = BigWorld.curCV.replace('res_', '') + '/'
        filePath = filePath.replace(modsRoot, '')
        new_filePath = new_filePath.replace(modsRoot, '')
        if filePath not in order:
            if new_filePath in order:
                order.insert(order.index(new_filePath), filePath)
            else:
                order.append(filePath)
                order.append(new_filePath)
            return True
        elif new_filePath not in order:
            order.insert(order.index(filePath) + 1, new_filePath)
            return True
        return False

    def check_wotmods(self, mediaPath):
        modsRoot = BigWorld.curCV.replace('res_', '') + '/'
        load_order_xml = '.' + modsRoot + 'load_order.xml'
        BLMarker = '_BanksLoaded'
        order_changed = False
        BL_present = False
        was_BLaM = False
        order = []
        orderSect = ResMgr.openSection(load_order_xml)
        if orderSect is None:
            orderSect = ResMgr.openSection(load_order_xml, True)
            collection = orderSect.createSection('Collection')
        else:
            collection = orderSect['Collection']
        BLaM = '_aaa_BanksLoader_audioMods.wotmod'
        for pkgSect in collection.values():
            pkgPath = pkgSect.asString
            if not os.path.isfile(modsRoot + pkgPath):
                collection.deleteSection(pkgSect)
                order_changed = True
            elif pkgPath == BLaM:
                was_BLaM = True
            else:
                if BLMarker in pkgPath:
                    BL_present = True
                order.append(pkgSect.asString)
        audio_mods_xml = 'res/%s/audio_mods.xml' % mediaPath
        for filePath in (os.path.join(x[0], y).replace(os.sep, '/') for x in os.walk(modsRoot) for y in x[2]):
            if not filePath.endswith('.wotmod') or os.path.basename(filePath) == BLaM or BLMarker in filePath:
                continue
            new_filePath = BLMarker.join(os.path.splitext(filePath))
            if os.path.isfile(new_filePath) and os.stat(filePath).st_mtime == os.stat(new_filePath).st_mtime:
                order_changed |= self.check_order(order, filePath, new_filePath)
                BL_present = True
                continue
            cleaned = False
            with zipfile.ZipFile(filePath) as zip_orig:
                fileNames = zip_orig.namelist()
                if audio_mods_xml in fileNames:
                    cleaned = True
                    self.editedBanks['wotmod'].append(os.path.basename(filePath))
                    bankFiles = [x for x in fileNames if x.startswith('res/' + mediaPath) and x.endswith('.bnk')]
                    if bankFiles:
                        with zipfile.ZipFile(new_filePath, 'w') as zip_new:
                            for fileInfo in zip_orig.infolist():
                                fileName = fileInfo.filename
                                if fileName == audio_mods_xml:
                                    fileInfo.filename = bankFiles[0].replace('.bnk', '.xml')
                                    zip_new.writestr(fileInfo, zip_orig.read(fileName))
            if cleaned:
                print self.ID + ': config renamed for package', os.path.basename(filePath)
                order_changed |= self.check_order(order, filePath, new_filePath)
                BL_present = True
                if os.path.isfile(new_filePath):
                    try:
                        stat = os.stat(filePath)
                        os.utime(new_filePath, (stat.st_atime, stat.st_mtime))
                    except StandardError:
                        traceback.print_exc()
        if BL_present:
            order.append(BLaM)
        order_changed |= was_BLaM != BL_present
        if order_changed:
            orderSect.deleteSection(collection)
            collection = orderSect.createSection('Collection')
            collection.writeStrings('pkg', order)
            orderSect.save()
        ResMgr.purge(load_order_xml, True)

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
        bankFiles = {'mods': set(), 'pkg': set(), 'ignore': set(),
                     'res': {os.path.basename(path) for path in glob.iglob('./res/' + mediaPath + '/*')
                             if (path.endswith('.bnk') or path.endswith('.pck'))}}
        for pkgPath in glob.iglob('./res/packages/audioww*.pkg'):
            with zipfile.ZipFile(pkgPath) as pkg:
                bankFiles['pkg'].update({os.path.basename(name) for name in pkg.namelist()})
        bankFiles['orig'] = bankFiles['res'] | bankFiles['pkg']
        bankFiles['mods'] = set(x for x in ResMgr.openSection(mediaPath).keys()
                                if (x.endswith('.bnk') or x.endswith('.pck')) and x not in bankFiles['orig'])
        bankFiles['all'] = bankFiles['orig'] | bankFiles['mods']
        audio_mods = ResMgr.openSection(mediaPath + '/audio_mods.xml')
        audio_mods_new = ResMgr.openSection(mediaPath + '/audio_mods_edited.xml', True)
        if audio_mods is None:
            LOG_NOTE('audio_mods.xml not found, will be created if needed')
        else:
            audio_mods_new.copy(audio_mods)
            ResMgr.purge(mediaPath + '/audio_mods.xml')
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
                    print self.ID + ': cleaned wrong section for setting', key
                    continue
                result = {'name': confSect['name'].asString, 'mod': confSect['mod'].asString}
                if key in subList:
                    stateList = []
                    for confSubName, confSubSect in confSect[subList[key]].items():
                        if confSubName != 'state' or not confSubSect.has_key('name') or not confSubSect.has_key('mod'):
                            confSect.deleteSection(confSubSect)
                            self.editedBanks['remap'].add(key)
                            print self.ID + ': cleaned wrong section for setting', key
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
                print self.ID + ': error while reading', confPath
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
        self.editedBanks['delete'] = remDups(self.editedBanks['delete'])
        bankFiles['orig'] = set(map(str.lower, bankFiles['orig']))
        poolKeys = {'memoryManager': ('defaultPool', 'lowEnginePool', 'preparedPool', 'streamingPool', 'IOPoolSize'),
                    'soundRender': ('max_voices',)}
        for profile_name in ('WWISE_active_profile', 'WWISE_emergency_profile'):
            moddedExist = set()
            profile_type = profile_name.split('_')[1]
            profile = soundMgr[soundMgr[profile_name].asString]
            for poolKey, poolValuesList in poolKeys.iteritems():
                for poolValue in poolValuesList:
                    value = profile[poolKey][poolValue]
                    if value is not None and value.asInt != int(self.data[poolValue]):
                        self.editedBanks['memory'].append(poolValue)
                        profile[poolKey].writeInt(poolValue, self.data[poolValue])
                        print self.ID + ': changing value for', profile_type, 'memory setting:', poolValue
            for name, section in profile.items():
                if 'soundbanks' not in name:
                    continue
                for sectName, project in section.items():
                    if sectName != 'project':
                        continue
                    bankName = project['name'].asString
                    if bankName not in bankFiles['all']:
                        print self.ID + ': clearing engine_config', profile_type, 'section for bank', bankName
                        self.editedBanks['delete'].append(bankName)
                        section.deleteSection(project)
                    elif bankName not in moddedExist:
                        moddedExist.add(bankName)
            for bankName in sorted(bankFiles['mods']):
                if bankName not in bankFiles['orig'] and bankName not in moddedExist and bankName not in bankFiles['ignore']:
                    print self.ID + ': creating', profile_type, 'sections for bank', bankName
                    if bankName in self.editedBanks['delete']:
                        self.editedBanks['delete'].remove(bankName)
                        self.editedBanks['move'].append(bankName)
                    else:
                        self.editedBanks['create'].append(bankName)
                    profile.createSection('SFX_soundbanks_loadonce/project').writeString('name', bankName)
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
statistic_mod = Analytics(_config.ID, _config.version, 'UA-76792179-9')


@overrideMethod(LoginView, '_populate')
def new_Login_populate(base, self):
    base(self)
    _config.onRequestRestart()


@overrideMethod(LobbyView, '_populate')
def new_Lobby_populate(base, self):
    base(self)
    _config.onRequestRestart()


@overrideMethod(PlayerAvatar, '_PlayerAvatar__startGUI')
def new_startGUI(base, *a, **kw):
    base(*a, **kw)
    _config.onRequestRestart()
