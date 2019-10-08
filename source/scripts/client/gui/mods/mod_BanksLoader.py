# -*- coding: utf-8 -*-
import BigWorld
import ResMgr
import glob
import os
import traceback
import zipfile
from PYmodsCore import PYmodsConfigInterface, remDups, Analytics, events, curCV
from PYmodsCore.delayed import showConfirmDialog
from debug_utils import LOG_ERROR, LOG_NOTE
from gui.Scaleform.daapi.view.dialogs import DIALOG_BUTTON_ID


class ConfigInterface(PYmodsConfigInterface):
    def __init__(self):
        self.editedBanks = {'create': [], 'delete': [], 'memory': [], 'move': [], 'remap': set(), 'wotmod': []}
        self.was_declined = False
        events.LoginView.populate.after(events.LobbyView.populate.after(events.PlayerAvatar.startGUI.after(self.tryRestart)))
        super(ConfigInterface, self).__init__()

    def init(self):
        self.ID = '%(mod_ID)s'
        self.version = '1.4.0 (%(file_compile_date)s)'
        self.author += ' and Ekspoint'
        self.data = {'defaultPool': 36,
                     'lowEnginePool': 10,
                     'memoryLimit': 250,
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

    def tryRestart(self, *_, **__):
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
        oldModName = curCV + '/scripts/client/gui/mods/mod_wg_load_custom_ekspont_banks.pyc'
        if os.path.isfile(oldModName) and os.path.isfile(oldModName + '1'):
            try:
                os.remove(oldModName + '1')
            except StandardError:
                traceback.print_exc()
        if os.path.isfile(oldModName):
            os.rename(oldModName, oldModName + '1')

    def check_wotmods(self, mediaPath):
        modsRoot = '.' + curCV.replace('res_', '') + '/'
        load_order_xml = modsRoot + 'load_order.xml'
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
                order.append(pkgSect.asString)
        audio_mods_xml = 'res/%s/audio_mods.xml' % mediaPath
        for filePath in (os.path.join(x[0], y).replace(os.sep, '/') for x in os.walk(modsRoot) for y in x[2]):
            if not filePath.endswith('.wotmod') or os.path.basename(filePath) == BLaM or BLMarker in filePath:
                continue
            new_filePath = BLMarker.join(os.path.splitext(filePath))
            _filePath = filePath.replace(modsRoot, '')
            if os.path.isfile(new_filePath) and os.stat(filePath).st_mtime == os.stat(new_filePath).st_mtime:
                order_changed |= _filePath not in order and not order.append(_filePath)
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
                                    fileInfo.extra = ''
                                    zip_new.writestr(fileInfo, zip_orig.read(fileName))
            if cleaned:
                print self.ID + ': config renamed for package', os.path.basename(filePath)
                order_changed |= _filePath not in order and not order.append(_filePath)
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
        bankFiles = self.collectBankFiles(mediaPath)
        audio_mods_new = self.merge_audio_mods(mediaPath, bankFiles)
        self.manageMemorySettings(soundMgr)
        for profile_name in ('WWISE_active_profile', 'WWISE_emergency_profile'):
            profile_type = profile_name.split('_')[1]
            profile = soundMgr[soundMgr[profile_name].asString]
            self.manageProfileMemorySettings(profile_type, profile)
            self.manageProfileBanks(profile_type, profile, bankFiles)
        self.saveNewFile(audio_mods_new, mediaPath + '/', 'audio_mods_edited.xml', mediaPath + '/audio_mods.xml',
                         ('delete', 'move', 'remap'))
        self.saveNewFile(new_engine, '', 'engine_config_edited.xml', 'engine_config.xml',
                         ('delete', 'move', 'create', 'memory'))

    def collectBankFiles(self, mediaPath):
        bankFiles = {'mods': set(), 'pkg': set(), 'ignore': set(),
                     'res': {os.path.basename(path) for path in glob.iglob('../res/' + mediaPath + '/*')
                             if os.path.splitext(path)[1] in ('.bnk', '.pck')}}
        for pkgPath in glob.iglob('../res/packages/audioww*.pkg'):
            with zipfile.ZipFile(pkgPath) as pkg:
                bankFiles['pkg'].update({os.path.basename(name) for name in pkg.namelist()})
        bankFiles['orig'] = bankFiles['res'] | bankFiles['pkg']
        bankFiles['mods'] = set(x for x in ResMgr.openSection(mediaPath).keys()
                                if os.path.splitext(x)[1] in ('.bnk', '.pck') and not any(y in bankFiles['orig'] for y in (x, x.lower())))
        bankFiles['all'] = bankFiles['orig'] | bankFiles['mods']
        return bankFiles

    def check_and_collect_data(self, key, section, struct, is_orig):
        result = []
        for name, sect in section.items():
            if name != struct['key'] or not all(sect.has_key(x) for x in struct['keys']):
                if is_orig:
                    self.editedBanks['remap'].add(key)
                    print self.ID + ': cleaned wrong section for setting', key
                continue
            data = {x: sect[x].asString for x in struct['keys']}
            if struct['data']:
                sub_name = struct['data']['name']
                if sect.has_key(sub_name):
                    data[sub_name] = self.check_and_collect_data(key, sect[sub_name], struct['data'], is_orig)
            result.append(data)
        return result

    def create_sect_from_data(self, sect, data, struct):
        for data in data:
            new_sect = sect.createSection(struct['key'])
            for key in struct['keys']:
                new_sect.writeString(key, data[key])
            if struct['data']:
                sub_name = struct['data']['name']
                self.create_sect_from_data(new_sect.createSection(sub_name), data[sub_name], struct['data'])

    def merge_audio_mods(self, mediaPath, bankFiles):
        audio_mods = ResMgr.openSection(mediaPath + '/audio_mods.xml')
        audio_mods_new = ResMgr.openSection(mediaPath + '/audio_mods_edited.xml', True)
        if audio_mods is None:
            LOG_NOTE('audio_mods.xml not found, will be created if needed')
        data_structure = [
            {'name': 'events', 'key': 'event', 'keys': ('name', 'mod'), 'data': ()},
            {'name': 'switches', 'key': 'switch', 'keys': ('name', 'mod'),
             'data': {'name': 'states', 'key': 'state', 'keys': ('name', 'mod'), 'data': ()}},
            {'name': 'RTPCs', 'key': 'RTPC', 'keys': ('name', 'mod'), 'data': ()},
            {'name': 'states', 'key': 'stateGroup', 'keys': ('name', 'mod'),
             'data': {'name': 'stateNames', 'key': 'state', 'keys': ('name', 'mod'), 'data': ()}}]
        data_old, data_new = {}, {}
        for struct in data_structure:
            key = struct['name']
            data_old[key] = self.check_and_collect_data(key, audio_mods[key], struct, True)
        banksData = {}
        for path in ResMgr.openSection(mediaPath).keys():
            if not path.endswith('.xml') or path.replace('.xml', '.bnk') not in bankFiles['all']:
                continue
            sect = ResMgr.openSection(mediaPath + '/' + path)
            bankName = path.replace('.xml', '.bnk')
            if sect is None:
                bankFiles['ignore'].add(bankName)
                print self.ID + ': error while reading', path
                continue
            bankData = banksData[bankName] = {}
            for struct in data_structure:
                key = struct['name']
                if sect.has_key(key):
                    bankData[key] = self.check_and_collect_data(key, sect[key], struct, False)
                data_new.setdefault(key, []).extend(bankData.get(key, []))
        for bankSect in audio_mods['loadBanks'].values():
            bankName = bankSect.asString
            print self.ID + ': clearing audio_mods section for bank', bankName
            self.editedBanks['delete'].append(bankName)
        self.editedBanks['delete'] = remDups(self.editedBanks['delete'])
        for key in ['loadBanks'] + [struct['name'] for struct in data_structure]:
            audio_mods_new.createSection(key)
        for struct in data_structure:
            key = struct['name']
            if data_old[key] != data_new.setdefault(key, []):
                self.editedBanks['remap'].add(key)
            if key in self.editedBanks['remap']:
                print self.ID + ': creating section for setting', key
            self.create_sect_from_data(audio_mods_new[key], data_new[key], struct)
        return audio_mods_new

    def manageMemorySettings(self, soundMgr):
        for mgrKey in ('memoryLimit',):  # in case they add something later
            value = soundMgr[mgrKey]
            if value is not None and value.asInt != int(self.data[mgrKey]):
                self.editedBanks['memory'].append(mgrKey)
                soundMgr.writeInt(mgrKey, self.data[mgrKey])
                print self.ID + ': changing value for memory setting:', mgrKey

    def manageProfileMemorySettings(self, profile_type, profile):
        poolKeys = {'memoryManager': ('defaultPool', 'lowEnginePool', 'streamingPool', 'IOPoolSize'),
                    'memoryManager_64bit': ('defaultPool', 'lowEnginePool', 'streamingPool', 'IOPoolSize'),
                    'soundRender': ('max_voices',)}
        for poolKey, poolValuesList in poolKeys.iteritems():
            for poolValue in poolValuesList:
                value = profile[poolKey][poolValue]
                if value is not None and value.asInt != int(self.data[poolValue]):
                    self.editedBanks['memory'].append(poolValue)
                    profile[poolKey].writeInt(poolValue, self.data[poolValue])
                    print self.ID + ': changing value for', profile_type, 'memory setting:', poolValue

    def manageProfileBanks(self, profile_type, profile, bankFiles):
        moddedExist = set()
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
        bankFiles['orig'] = [x.lower() for x in bankFiles['orig']]
        for bankName in sorted(bankFiles['mods']):
            if bankName not in bankFiles['orig'] and bankName not in moddedExist and bankName not in bankFiles['ignore']:
                print self.ID + ': creating', profile_type, 'sections for bank', bankName
                if bankName in self.editedBanks['delete']:
                    self.editedBanks['delete'].remove(bankName)
                    self.editedBanks['move'].append(bankName)
                else:
                    self.editedBanks['create'].append(bankName)
                profile.createSection('SFX_soundbanks_loadonce/project').writeString('name', bankName)

    def saveNewFile(self, new_file, new_dir, new_name, orig_path, keys):
        if not any(self.editedBanks[key] for key in keys):
            ResMgr.purge(new_dir + new_name)
            return
        orig_path = '.' + curCV + '/' + orig_path
        new_path = new_dir + new_name
        new_dir = '.' + curCV + '/' + new_dir
        if not os.path.exists(new_dir):
            os.makedirs(new_dir)
        new_file.save()
        if os.path.isfile(orig_path):
            try:
                os.remove(orig_path)
            except StandardError:
                traceback.print_exc()
        for new_path in (new_dir + new_name, '../res/' + new_path, './' + new_path):
            if os.path.isfile(new_path):
                os.rename(new_path, orig_path)
                break

    def load(self):
        self.suppress_old_mod()
        self.readCurrentSettings(False)
        self.checkConfigs()
        print self.message() + ': initialised.'


_config = ConfigInterface()
statistic_mod = Analytics(_config.ID, _config.version, 'UA-76792179-9')
