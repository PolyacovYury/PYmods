import binascii
import cProfile
import datetime
import time

import BigWorld
import Event
import ResMgr
import SoundGroups
import glob
import os
import shutil
import traceback
from PYmodsCore import remDups, loadJson, events, curCV
from account_helpers.settings_core.settings_constants import GAME
from adisp import AdispException, async, process
from async import await, async as async2
from functools import partial
from gui import GUI_SETTINGS
from gui.Scaleform.daapi.settings.views import VIEW_ALIAS
from gui.Scaleform.daapi.view.battle.classic.battle_end_warning_panel import _WWISE_EVENTS
from gui.Scaleform.daapi.view.battle.shared.minimap.settings import MINIMAP_ATTENTION_SOUND_ID
from gui.Scaleform.daapi.view.login.login_modes import base_wgc_mode as wgc_mode
from gui.Scaleform.daapi.view.meta.LoginQueueWindowMeta import LoginQueueWindowMeta
from gui.Scaleform.framework import GroupedViewSettings, ScopeTemplates as ST, WindowLayer as WL, g_entitiesFactories
from gui.Scaleform.framework.entities.View import ViewKey
from gui.Scaleform.framework.managers.loaders import SFViewLoadParams
from gui.impl.dialogs import dialogs
from gui.impl.dialogs.builders import WarningDialogBuilder
from gui.impl.pub.dialog_window import DialogButtons
from helpers import getClientVersion, dependency
from shared_utils import awaitNextFrame
from skeletons.gui.login_manager import ILoginManager
from . import g_config


class SkinnerLoading(LoginQueueWindowMeta):
    _loginManager = dependency.descriptor(ILoginManager)
    __callMethod = lambda self, name, *a, **kw: getattr(self, name)(*a, **kw)
    callMethod = Event.Handler()
    skinsChecked = False

    def __init__(self, loginView):
        super(SkinnerLoading, self).__init__()
        self.loginView = loginView
        self.lines = []
        self.progress = 0
        self.restart = False
        self.doLogin = (self._loginManager.wgcAvailable and not self._loginManager.settingsCore.getSetting(
            GAME.LOGIN_SERVER_SELECTION) and not self._loginManager.getPreference('server_select_was_set'))

    def _populate(self):
        super(SkinnerLoading, self)._populate()
        self.callMethod.set(self.__callMethod)
        self.__initTexts()
        BigWorld.callback(0, self.loadSkins)

    def __initTexts(self):
        self.updateTitle(g_config.i18n['UI_loading_header_CRC32'])
        self.updateMessage()
        self.updateCancelLabel()
        self.as_showAutoLoginBtnS(False)

    def updateCancelLabel(self):
        self.as_setCancelLabelS(g_config.i18n['UI_loading_autoLogin' + ('_cancel' if self.doLogin else '')])

    def updateTitle(self, title):
        self.as_setTitleS(title)

    def updateMessage(self):
        self.as_setMessageS(''.join("<p align='left'>%s</p>" % line for line in self.lines))

    def addLine(self, line):
        while len(self.lines) >= 8:
            self.lines.pop(0)
        self.lines.append(line)
        self.updateMessage()

    def addBar(self, line):
        self.progress = 0
        self.addLine(line)
        self.addLine(self.createBar())

    def createBar(self):
        r = min(255, 510 - 255 * self.progress / 50)
        g = min(255, 255 * self.progress / 50)
        return "<font color='#007BFF' face='Arial'>%s%s</font><font color='#%02X%02X00'>  %s%%</font>" % (
            u'\u2593' * (self.progress / 4), u'\u2591' * (25 - self.progress / 4), r, g, self.progress)

    def updateProgress(self, progress):
        if progress != self.progress:
            self.progress = progress
            self.lines[-1] = self.createBar()
            self.updateMessage()
            return True
        return False

    def onBarComplete(self):
        self.lines.pop(-1)
        self.lines[-1] += "<font color='#00FF00'>%s</font>" % g_config.i18n['UI_loading_done']
        self.updateMessage()
        SoundGroups.g_instance.playSound2D(MINIMAP_ATTENTION_SOUND_ID)

    def onTryClosing(self):
        return False

    def onCancelClick(self):
        self.doLogin = not self.doLogin
        self.updateCancelLabel()

    def onWindowClose(self):
        self.callMethod.clear()
        if self.restart:
            self.call_restart()
        elif self.doLogin:
            BigWorld.callback(0.1, partial(doLogin, self.app))
        self.destroy()

    @staticmethod
    @async2
    def call_restart():
        result = yield await(dialogs.showSimple(
            WarningDialogBuilder().setFormattedTitle(g_config.i18n['UI_restart_header'])
            .setFormattedMessage(g_config.i18n['UI_restart_text'])
            .addButton(DialogButtons.PURCHASE, None, True, rawLabel=g_config.i18n['UI_restart_button_restart'])
            .addButton(DialogButtons.RESEARCH, None, False, rawLabel=g_config.i18n['UI_restart_button_shutdown'])
            .build(), DialogButtons.PURCHASE))
        BigWorld.savePreferences()
        BigWorld.restartGame() if result else BigWorld.quit()

    @process
    def loadSkins(self):
        jobStartTime = time.time()
        pr = None
        if g_config.data['isDebug']:
            pr = cProfile.Profile()
            pr.enable()
        try:
            texReplaced, vehicleSkins = yield checkSkinFiles()
            self.restart = yield checkMeta(texReplaced)
            if self.restart:
                yield unpackModels(vehicleSkins)
        except AdispException:
            traceback.print_exc()
        else:
            loadJson(g_config.ID, 'skinsCache', g_config.skinsCache, g_config.configPath, True)
            os.utime(g_config.configPath + 'skinsCache.json', None)  # loadJson does not poke the file, see need_check
        if g_config.data['isDebug']:
            pr.disable()
            pr.print_stats('time')
        print g_config.ID + ': total models check time:', datetime.timedelta(seconds=round(time.time() - jobStartTime))
        BigWorld.callback(1, partial(SoundGroups.g_instance.playSound2D, 'enemy_sighted_for_team'))
        BigWorld.callback(2, self.onWindowClose)
        SkinnerLoading.skinsChecked = True
        self.loginView.update()

    @staticmethod
    def need_check():
        if (not g_config.data['isDebug'] and not SkinnerLoading.skinsChecked
                and g_config.skinsCache['version'] == getClientVersion()
                and time.time() - os.path.getmtime(g_config.configPath + 'skinsCache.json') < 60 * 60 * 6):
            print g_config.ID + ': skins checksum was checked recently, trusting the user on this one'
            SkinnerLoading.skinsChecked = True
        return g_config.data['enabled'] and g_config.skinsData['models'] and not SkinnerLoading.skinsChecked


def doLogin(app):
    # noinspection PyArgumentList
    loginView = app.containerManager.getViewByKey(ViewKey(VIEW_ALIAS.LOGIN))
    if not loginView:
        return
    if loginView.loginManager.wgcAvailable:
        loginView.loginManager.tryWgcLogin()
    elif loginView.loginManager.getPreference('remember_user'):
        login = loginView.loginManager.getPreference('login')
        password = '*' * loginView.loginManager.getPreference('password_length')
        loginView.onLogin(login, password, loginView._servers.selectedServer['data'], '@' not in login)


modelsDir = curCV + '/vehicles/skins/models/'
delay_call = lambda cb, *a: BigWorld.callback(0, partial(cb, a[0] if len(a) == 1 else a))  # a may be an empty tuple
g_entitiesFactories.addSettings(GroupedViewSettings(
    'SkinnerLoading', SkinnerLoading, 'LoginQueueWindow.swf', WL.TOP_WINDOW, '', None, ST.DEFAULT_SCOPE, canClose=False))


def enumLen(arr, cond=None):
    arr = filter(cond, arr)
    arrLen = float(len(arr))
    for idx, elem in enumerate(arr):
        yield arrLen, idx, elem


def iterSection(sect, numbers=True, depth=1):
    subs = [] if sect is None else remDups(sect.keys())
    for sub in (enumLen if numbers else zip)(subs):
        if depth > 1:
            for _sub in iterSection(sect[sub[-1]], numbers, depth - 1):
                yield sub + _sub
        else:
            yield sub + (sect[sub[-1]],)


@async
@process
def checkSkinFiles(callback):
    texReplaced = False
    vehicleSkins = {}
    CRC32cache = g_config.skinsCache['CRC32']
    skinsPath = 'vehicles/skins/textures/'
    dirSect = ResMgr.openSection(skinsPath)
    if dirSect is None or not dirSect.keys() or not g_config.skinsData['models']:
        print g_config.ID + ': skins folder is empty'
        delay_call(callback, texReplaced, vehicleSkins)
        return
    print g_config.ID + ': listing', skinsPath, 'for CRC32'
    SkinnerLoading.callMethod('addLine', g_config.i18n['UI_loading_skins'])
    CRC32 = 0
    resultList = []
    for skinName in remDups(dirSect.keys()):
        SkinnerLoading.callMethod('addBar', g_config.i18n['UI_loading_skinPack'] % os.path.basename(skinName))
        skinCRC32 = 0
        skinSect = dirSect[skinName]['vehicles']
        for natLen, natNum, nation, vehLen, vehNum, vehicleName, vehSect in iterSection(skinSect, depth=2):
            vehicleSkins.setdefault('/'.join((nation, vehicleName)).lower(), []).append(skinName)
            texPrefix = '/'.join(('vehicles', nation, vehicleName))
            textures = ['/'.join((texPrefix, texName)) for texName in remDups(vehSect.keys()) if texName.endswith('.dds')]
            for subName, subSect in iterSection(vehSect, False):
                if not subName.startswith('_') or '.' in subName:
                    continue
                for styleName, styleSect in iterSection(subSect, False):
                    vehicleSkins.setdefault('/'.join((nation, vehicleName, styleName)).lower(), []).append(skinName)
                    textures.extend('/'.join((texPrefix, subName, styleName, texName))
                                    for texName in remDups(styleSect.keys()) if texName.endswith('.dds'))
            for localPath in textures:
                texPath = skinsPath + skinName + '/' + localPath
                skinCRC32 ^= binascii.crc32(str(ResMgr.openSection(texPath).asBinary)) & 0xFFFFFFFF & hash(localPath)
            SkinnerLoading.callMethod('updateProgress', int(100 * (natNum + vehNum / vehLen) / natLen))
            yield awaitNextFrame()
        SkinnerLoading.callMethod('onBarComplete')
        if skinCRC32 in resultList:
            print g_config.ID + ': detected duplicate skins pack:', skinName.replace(os.sep, '/')
            continue
        CRC32 ^= skinCRC32
        resultList.append(skinCRC32)
    if str(CRC32) == CRC32cache:
        print g_config.ID + ': textures were not changed'
    else:
        print g_config.ID + ': textures were', ('reinstalled' if CRC32cache is None else 'changed')
        g_config.skinsCache['CRC32'] = str(CRC32)
        texReplaced = True
    ResMgr.purge(skinsPath)
    delay_call(callback, texReplaced, vehicleSkins)


@async
@process
def deleteModelFiles(rootPath, callback):
    SkinnerLoading.callMethod('updateTitle', g_config.i18n['UI_loading_header_models_clean'])
    SkinnerLoading.callMethod('addLine', g_config.i18n['UI_loading_skins_clean'])
    for skinPack in os.listdir(rootPath):
        SkinnerLoading.callMethod('addBar', g_config.i18n['UI_loading_skinPack_clean'] % os.path.basename(skinPack))
        nationsList = os.listdir(os.path.join(rootPath, skinPack, 'vehicles'))
        for natLen, natNum, nation in enumLen(nationsList):
            vehiclesList = os.listdir(os.path.join(rootPath, skinPack, 'vehicles', nation))
            for vehLen, vehNum, vehicleName in enumLen(vehiclesList):
                shutil.rmtree(os.path.join(rootPath, skinPack, 'vehicles', nation, vehicleName))
                SkinnerLoading.callMethod('updateProgress', int(100 * (natNum + vehNum / vehLen) / natLen))
                yield awaitNextFrame()
        SkinnerLoading.callMethod('onBarComplete')
        shutil.rmtree(os.path.join(rootPath, skinPack))
    shutil.rmtree(rootPath)
    delay_call(callback)


@async
@process
def checkMeta(texReplaced, callback):
    lastVersion = g_config.skinsCache['version']
    clientIsNew = getClientVersion() != lastVersion
    if not lastVersion:
        print g_config.ID + ': client version cache not found'
    elif clientIsNew:
        print g_config.ID + ': client version changed'
    skinsModelsMissing = not next(glob.iglob(modelsDir + '*'), False)  # directory does not exist or is empty
    if not os.path.isdir(modelsDir):
        print g_config.ID + ': models dir not found'
    elif skinsModelsMissing:
        print g_config.ID + ': models dir is empty'
    found = bool(g_config.skinsData['models'])
    if found:
        if clientIsNew:
            SkinnerLoading.callMethod('addLine', g_config.i18n['UI_loading_changed_version'])
            g_config.skinsCache['version'] = getClientVersion()
        if texReplaced:
            SkinnerLoading.callMethod('addLine', g_config.i18n['UI_loading_changed_skins'])
        if (clientIsNew or texReplaced) and os.path.isdir(modelsDir):
            yield deleteModelFiles(modelsDir)
        if not os.path.isdir(modelsDir):
            os.makedirs(modelsDir)
    elif os.path.isdir(modelsDir):
        print g_config.ID + ': no skins found, deleting', modelsDir
        yield deleteModelFiles(modelsDir)
    delay_call(callback, found and (clientIsNew or skinsModelsMissing or texReplaced))


@async
@process
def unpackModels(vehicleSkins, callback):
    SkinnerLoading.callMethod('updateTitle', g_config.i18n['UI_loading_header_models_unpack'])
    SoundGroups.g_instance.playSound2D(_WWISE_EVENTS.APPEAR)
    print g_config.ID + ': unpacking vehicle models'
    for nation, nationSect in iterSection(ResMgr.openSection('vehicles'), False):
        if '.' in nation or nation in ('skins', 'remods'):  # idk about any else, it also pretty much doesn't matter
            continue
        SkinnerLoading.callMethod('addBar', g_config.i18n['UI_loading_unpacking'] % ('vehicles/' + nation))
        for vehLen, vehNum, vehName, vehSect in iterSection(nationSect):
            for dirName, dirSect in iterSection(vehSect, False):
                yield unpackVehicleDir(vehicleSkins, nation, vehName, dirName, dirSect, ())
            if SkinnerLoading.callMethod('updateProgress', int(100 * vehNum / vehLen)):
                yield awaitNextFrame()
        SkinnerLoading.callMethod('onBarComplete')
    delay_call(callback)


@async
@process
def unpackVehicleDir(vehicleSkins, nation, vehName, dirName, dirSect, style, callback):
    if dirName.startswith('_') and '.' not in dirName:
        if style:
            print g_config.ID + ': detected styles directory inside style directory:',
            print nation, vehName, style, dirName
        else:
            for styleName, _dirName, _dirSect in iterSection(dirSect, False, 2):
                yield unpackVehicleDir(vehicleSkins, nation, vehName, _dirName, _dirSect, (dirName, styleName))
                yield awaitNextFrame()
    if dirName != 'normal':
        delay_call(callback)
        return
    for skinName in vehicleSkins.get('/'.join((nation, vehName) + style[1:]).lower(), []):
        for lod, fName, fSect in iterSection(dirSect, False, 2):
            ext = os.path.splitext(fName)[1]
            if ext not in ('.model', '.visual', '.visual_processed', '.vt'):
                continue
            unpackNormal('/'.join(('vehicles', nation, vehName) + style + (dirName, lod, fName)), fSect, skinName)
            if ext == '.vt':
                yield awaitNextFrame()
    delay_call(callback)


def unpackNormal(oldPath, oldSection, skinName):
    skinDir = modelsDir.replace(curCV + '/', '') + skinName + '/'
    texDir = skinDir.replace('models', 'textures')
    newPath = ResMgr.resolveToAbsolutePath('./' + skinDir + oldPath)
    oldPath, ext = os.path.splitext(oldPath)
    if '.vt' in ext:
        if not os.path.isdir(os.path.dirname(newPath)):  # because .vts are not always first and makedirs is dumb
            os.makedirs(os.path.dirname(newPath))  # because .vts are sometimes first and dirs need to be there
        with open(newPath, 'wb') as newFile:
            newFile.write(oldSection.asBinary)
        return
    newSection = ResMgr.openSection(newPath, True)
    newSection.copy(oldSection)
    sections = [newSection]
    if 'hassis' in newPath:
        dynSection = ResMgr.openSection(newPath.replace('hassis', 'hassis_dynamic'), True)
        dynSection.copy(oldSection)
        sections.append(dynSection)
    for idx, section in enumerate(sections):
        if '.model' in ext:
            if section.has_key('parent'):
                parent = skinDir + section['parent'].asString
                if idx:
                    parent = parent.replace('hassis', 'hassis_dynamic')
                section.writeString('parent', parent.replace('\\', '/'))
            visualPath = skinDir + section['nodefullVisual'].asString
            if idx:
                visualPath = visualPath.replace('hassis', 'hassis_dynamic')
            section.writeString('nodefullVisual', visualPath.replace('\\', '/'))
        elif '.visual' in ext:
            for sub in (sub for name, sect in section.items() if name == 'renderSet'
                        for s_name, sub in sect['geometry'].items() if s_name == 'primitiveGroup'):
                hasTracks = False
                for name, prop in sub['material'].items():
                    if name != 'property' or not prop.has_key('Texture'):
                        continue
                    newTexture = texDir + prop['Texture'].asString
                    if idx and 'tracks' in newTexture and prop.asString == 'diffuseMap':
                        newTexture = 'vehicles/skins/tracks/track_AM.dds'
                        hasTracks = True
                    if ResMgr.isFile(newTexture):
                        prop.writeString('Texture', newTexture.replace('\\', '/'))
                if hasTracks:
                    for name, prop in sub['material'].items():
                        if name == 'property' and prop.asString == 'g_useNormalPackDXT1':
                            prop.writeString('Bool', 'true')
            if section['primitivesName'] is None:
                section.writeString('primitivesName', oldPath)
        section.save()


@events.LoginView.populate.before
def before_Login_populate(*_, **__):
    wgc_mode._g_firstEntry &= not SkinnerLoading.need_check()


@events.LoginView.populate.after
def new_Login_populate(self, *_, **__):
    if not SkinnerLoading.need_check():
        return
    self.as_setDefaultValuesS({
        'loginName': '', 'pwd': '', 'memberMe': self._loginMode.rememberUser,
        'memberMeVisible': self._loginMode.rememberPassVisible,
        'isIgrCredentialsReset': GUI_SETTINGS.igrCredentialsReset,
        'showRecoveryLink': not GUI_SETTINGS.isEmpty('recoveryPswdURL')})
    BigWorld.callback(3, partial(self.app.loadView, SFViewLoadParams('SkinnerLoading'), self))
