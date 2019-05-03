import binascii
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
from PYmodsCore.delayed import showConfirmDialog
from account_helpers.settings_core.settings_constants import GAME
from adisp import AdispException, async, process
from functools import partial
from gui import GUI_SETTINGS
from gui.Scaleform.daapi.settings.views import VIEW_ALIAS
from gui.Scaleform.daapi.view.battle.classic.battle_end_warning_panel import _WWISE_EVENTS
from gui.Scaleform.daapi.view.battle.shared.minimap.settings import MINIMAP_ATTENTION_SOUND_ID
from gui.Scaleform.daapi.view.login.login_modes import wgc_mode
from gui.Scaleform.daapi.view.meta.LoginQueueWindowMeta import LoginQueueWindowMeta
from gui.Scaleform.framework import GroupedViewSettings, ScopeTemplates, ViewTypes, g_entitiesFactories
from gui.Scaleform.framework.entities.View import ViewKey
from gui.Scaleform.framework.managers.loaders import SFViewLoadParams
from helpers import getClientVersion, dependency
from skeletons.account_helpers.settings_core import ISettingsCore
from skeletons.gui.login_manager import ILoginManager
from zipfile import ZipFile
from . import g_config

wgc_mode._g_firstEntry = not g_config.data['enabled']
empty_async = partial(async, cbwrapper=lambda x: partial(x, None))
callLoading = Event.Event()
texReplaced = False
skinsChecked = False
clientIsNew = True
skinsModelsMissing = True
needToReReadSkinsModels = False
modelsDir = curCV + '/vehicles/skins/models/'
vehicleSkins = {}


class SkinnerLoading(LoginQueueWindowMeta):
    loginManager = dependency.descriptor(ILoginManager)
    sCore = dependency.descriptor(ISettingsCore)
    __callMethod = lambda self, name, *a, **kw: getattr(self, name)(*a, **kw)

    def __init__(self, loginView):
        super(SkinnerLoading, self).__init__()
        self.loginView = loginView
        self.lines = []
        self.curPercentage = 0
        self.doLogin = self.loginManager.checkWgcAvailability() and not self.sCore.getSetting(GAME.LOGIN_SERVER_SELECTION)

    def _populate(self):
        super(SkinnerLoading, self)._populate()
        callLoading.__iadd__(self.__callMethod)
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
        if len(self.lines) == 8:
            del self.lines[0]
        self.lines.append(line)
        self.updateMessage()

    def onComplete(self):
        self.lines[-1] += "<font color='#00FF00'>%s</font>" % g_config.i18n['UI_loading_done']
        self.updateMessage()
        SoundGroups.g_instance.playSound2D(MINIMAP_ATTENTION_SOUND_ID)

    def addBar(self, line):
        self.curPercentage = 0
        self.addLine(line)
        self.addLine(self.createBar())

    def createBar(self):
        red = 510 - 255 * self.curPercentage / 50
        green = 255 * self.curPercentage / 50
        return "<font color='#007BFF' face='Arial'>%s</font><font color='#{0:0>2x}{1:0>2x}00'>  %s%%</font>".format(
            red if red < 255 else 255, green if green < 255 else 255) % (
                   u'\u2593' * (self.curPercentage / 4) + u'\u2591' * (25 - self.curPercentage / 4), self.curPercentage)

    def updatePercentage(self, percentage):
        self.curPercentage = percentage
        self.lines[-1] = self.createBar()
        self.updateMessage()

    def onBarComplete(self):
        del self.lines[-1]
        self.onComplete()

    def onTryClosing(self):
        return False

    def onCancelClick(self):
        self.doLogin = not self.doLogin
        self.updateCancelLabel()

    def onWindowClose(self):
        callLoading.__isub__(self.__callMethod)
        if needToReReadSkinsModels:
            showConfirmDialog(
                g_config.i18n['UI_restart_header'], g_config.i18n['UI_restart_text'],
                (g_config.i18n['UI_restart_button_restart'], g_config.i18n['UI_restart_button_shutdown']),
                lambda restart: (BigWorld.savePreferences(), (BigWorld.restartGame() if restart else BigWorld.quit())))
        elif self.doLogin:
            BigWorld.callback(0.1, partial(doLogin, self.app))
        self.destroy()

    @process
    def loadSkins(self):
        global skinsChecked
        jobStartTime = time.time()
        try:
            yield skinCRC32All()
            yield modelsCheck()
            yield modelsProcess()
        except AdispException:
            traceback.print_exc()
        else:
            loadJson(g_config.ID, 'skinsCache', g_config.skinsCache, g_config.configPath, True)
        print g_config.ID + ': total models check time:', datetime.timedelta(seconds=round(time.time() - jobStartTime))
        BigWorld.callback(1, partial(SoundGroups.g_instance.playSound2D, 'enemy_sighted_for_team'))
        BigWorld.callback(2, self.onWindowClose)
        skinsChecked = True
        self.loginView.update()


def doLogin(app):
    # noinspection PyArgumentList
    loginView = app.containerManager.getViewByKey(ViewKey(VIEW_ALIAS.LOGIN))
    if not loginView:
        return
    if loginView.loginManager.checkWgcAvailability():
        loginView.loginManager.tryWgcLogin()
    elif loginView.loginManager.getPreference('remember_user'):
        password = '*' * loginView.loginManager.getPreference('password_length')
        login = loginView.loginManager.getPreference('login')
        loginView.onLogin(login, password, loginView._servers.selectedServer['data'], '@' not in login)


g_entitiesFactories.addSettings(
    GroupedViewSettings('SkinnerLoading', SkinnerLoading, 'LoginQueueWindow.swf', ViewTypes.TOP_WINDOW,
                        '', None, ScopeTemplates.DEFAULT_SCOPE, canClose=False))


def CRC32_from_file(filename, localPath):
    return binascii.crc32(str(ResMgr.openSection(filename).asBinary)) & 0xFFFFFFFF & hash(localPath)


@empty_async
@process
def skinCRC32All(callback):
    global texReplaced, vehicleSkins
    CRC32cache = g_config.skinsCache['CRC32']
    skinsPath = 'vehicles/skins/textures/'
    dirSect = ResMgr.openSection(skinsPath)
    if dirSect is None or not dirSect.keys() or not g_config.skinsData['models']:
        print g_config.ID + ': skins folder is empty'
        BigWorld.callback(0, callback)
        return
    print g_config.ID + ': listing', skinsPath, 'for CRC32'
    callLoading('addLine', g_config.i18n['UI_loading_skins'])
    CRC32 = 0
    resultList = []
    for skin in remDups(dirSect.keys()):
        completionPercentage = 0
        callLoading('addBar', g_config.i18n['UI_loading_skinPack'] % os.path.basename(skin))
        skinCRC32 = 0
        skinSect = dirSect[skin]['vehicles']
        nationsList = [] if skinSect is None else remDups(skinSect.keys())
        natLen = len(nationsList)
        for num, nation in enumerate(nationsList):
            nationSect = skinSect[nation]
            vehiclesList = [] if nationSect is None else remDups(nationSect.keys())
            vehLen = len(vehiclesList)
            for vehNum, vehicleName in enumerate(vehiclesList):
                vehicleSkins.setdefault(vehicleName.lower(), []).append(skin)
                texPrefix = 'vehicles/' + nation + '/' + vehicleName + '/'
                vehicleSect = nationSect[vehicleName]
                textures = []
                if vehicleSect is not None:
                    textures = [texPrefix + texName for texName in remDups(vehicleSect.keys()) if texName.endswith('.dds')]
                    modelsSect = vehicleSect['_skins']
                    for modelsSet in modelsSect.keys() if modelsSect is not None else ():
                        vehicleSkins.setdefault((vehicleName + '/' + modelsSet).lower(), []).append(skin)
                        textures.extend(texPrefix + '_skins/' + modelsSet + '/' + texName
                                        for texName in remDups(modelsSect[modelsSet].keys()) if texName.endswith('.dds'))
                for localPath in textures:
                    texPath = skinsPath + skin + '/' + localPath
                    textureCRC32 = CRC32_from_file(texPath, localPath)
                    skinCRC32 ^= textureCRC32
                yield doFuncCall()
                currentPercentage = int(100 * (float(num) + float(vehNum) / float(vehLen)) / float(natLen))
                if currentPercentage != completionPercentage:
                    completionPercentage = currentPercentage
                    callLoading('updatePercentage', completionPercentage)
        callLoading('onBarComplete')
        if skinCRC32 in resultList:
            print g_config.ID + ': detected duplicate skins pack:', skin.replace(os.sep, '/')
            continue
        CRC32 ^= skinCRC32
        resultList.append(skinCRC32)
    if str(CRC32) == CRC32cache:
        print g_config.ID + ': skins textures were not changed'
    else:
        print g_config.ID + ': skins textures were', ('reinstalled' if CRC32cache is None else 'changed')
        g_config.skinsCache['CRC32'] = str(CRC32)
        texReplaced = True
    ResMgr.purge(skinsPath)
    BigWorld.callback(0, callback)


@empty_async
@process
def rmtree(rootPath, callback):
    callLoading('updateTitle', g_config.i18n['UI_loading_header_models_clean'])
    callLoading('addLine', g_config.i18n['UI_loading_skins_clean'])
    rootDirs = os.listdir(rootPath)
    for skinPack in rootDirs:
        callLoading('addBar', g_config.i18n['UI_loading_skinPack_clean'] % os.path.basename(skinPack))
        completionPercentage = 0
        nationsList = os.listdir(os.path.join(rootPath, skinPack, 'vehicles'))
        natLen = len(nationsList)
        for num, nation in enumerate(nationsList):
            vehiclesList = os.listdir(os.path.join(rootPath, skinPack, 'vehicles', nation))
            vehLen = len(vehiclesList)
            for vehNum, vehicleName in enumerate(vehiclesList):
                shutil.rmtree(os.path.join(rootPath, skinPack, 'vehicles', nation, vehicleName))
                yield doFuncCall()
                currentPercentage = int(100 * (float(num) + float(vehNum) / float(vehLen)) / float(natLen))
                if currentPercentage != completionPercentage:
                    completionPercentage = currentPercentage
                    callLoading('updatePercentage', completionPercentage)
        callLoading('onBarComplete')
        shutil.rmtree(os.path.join(rootPath, skinPack))
    shutil.rmtree(rootPath)
    BigWorld.callback(1, callback)


@empty_async
@process
def modelsCheck(callback):
    global clientIsNew, skinsModelsMissing, needToReReadSkinsModels
    lastVersion = g_config.skinsCache['version']
    if lastVersion:
        if getClientVersion() == lastVersion:
            clientIsNew = False
        else:
            print g_config.ID + ': skins client version changed'
    else:
        print g_config.ID + ': skins client version cache not found'

    if os.path.isdir(modelsDir):
        if len(glob.glob(modelsDir + '*')):
            skinsModelsMissing = False
        else:
            print g_config.ID + ': skins models dir is empty'
    else:
        print g_config.ID + ': skins models dir not found'
    found = bool(g_config.skinsData['models'])
    needToReReadSkinsModels = found and (clientIsNew or skinsModelsMissing or texReplaced)
    if found and clientIsNew:
        if os.path.isdir(modelsDir):
            yield rmtree(modelsDir)
        g_config.skinsCache['version'] = getClientVersion()
    if found and not os.path.isdir(modelsDir):
        os.makedirs(modelsDir)
    elif not found and os.path.isdir(modelsDir):
        print g_config.ID + ': no skins found, deleting', modelsDir
        yield rmtree(modelsDir)
    elif texReplaced and os.path.isdir(modelsDir):
        yield rmtree(modelsDir)
        os.makedirs(modelsDir)
    BigWorld.callback(0, callback)


@empty_async
@process
def modelsProcess(callback):
    if not needToReReadSkinsModels:
        BigWorld.callback(0, callback)
        return
    callLoading('updateTitle', g_config.i18n['UI_loading_header_models_unpack'])
    SoundGroups.g_instance.playSound2D(_WWISE_EVENTS.APPEAR)
    modelFileFormats = ('.model', '.visual', '.visual_processed', '.vt')
    print g_config.ID + ': unpacking vehicle packages'
    for pkgPath in glob.glob('./res/packages/vehicles*.pkg') + glob.glob('./res/packages/shared_content*.pkg'):
        completionPercentage = 0
        callLoading('addBar', g_config.i18n['UI_loading_package'] % os.path.basename(pkgPath)[:-4].replace('sandbox', 'sb'))
        pkg = ZipFile(pkgPath)
        fileNamesList = [x for x in pkg.namelist()
                         if x.startswith('vehicles') and 'normal' in x and os.path.splitext(x)[1] in modelFileFormats]
        allFilesCnt = len(fileNamesList)
        for fileNum, memberFileName in enumerate(fileNamesList):
            attempt = memberFileName.split('/')[2]
            if '_skins/' in memberFileName:
                attempt += '/' + memberFileName.split('_skins/')[1].split('/', 1)[0]
            for skinName in vehicleSkins.get(attempt.lower(), []):
                try:
                    processMember(memberFileName, skinName)
                except ValueError as e:
                    print g_config.ID + ':', e
            if not fileNum % 25:
                yield doFuncCall()
            currentPercentage = int(100 * float(fileNum) / float(allFilesCnt))
            if currentPercentage != completionPercentage:
                completionPercentage = currentPercentage
                callLoading('updatePercentage', completionPercentage)
                yield doFuncCall()
        pkg.close()
        callLoading('onBarComplete')
    BigWorld.callback(0, callback)


@empty_async
def doFuncCall(callback):
    BigWorld.callback(0, callback)


def processMember(memberFileName, skinName):
    skinDir = modelsDir.replace(curCV + '/', '') + skinName + '/'
    texDir = skinDir.replace('models', 'textures')
    newPath = ResMgr.resolveToAbsolutePath('./' + skinDir + memberFileName)
    oldSection = ResMgr.openSection(memberFileName)
    if '.vt' in memberFileName:
        if not os.path.isdir(os.path.dirname(newPath)):  # because .vts are not always first and makedirs is dumb
            os.makedirs(os.path.dirname(newPath))  # because .vts are sometimes first and dirs need to be there
        with open(newPath, 'wb') as newFile:
            newFile.write(oldSection.asBinary)
        return
    newSection = ResMgr.openSection(newPath, True)
    newSection.copy(oldSection)
    sections = [newSection]
    if 'Chassis' in memberFileName:
        dynSection = ResMgr.openSection(newPath.replace('Chassis', 'Chassis_dynamic'), True)
        dynSection.copy(oldSection)
        sections.append(dynSection)
    for idx, section in enumerate(sections):
        if '.model' in memberFileName:
            if section.has_key('parent'):
                parent = skinDir + section['parent'].asString
                if idx:
                    parent = parent.replace('Chassis', 'Chassis_dynamic')
                section.writeString('parent', parent.replace('\\', '/'))
            visualPath = skinDir + section['nodefullVisual'].asString
            if idx:
                visualPath = visualPath.replace('Chassis', 'Chassis_dynamic')
            section.writeString('nodefullVisual', visualPath.replace('\\', '/'))
        elif '.visual' in memberFileName:
            for sub in (sub for name, sect in section.items() if name == 'renderSet'
                        for s_name, sub in sect['geometry'].items() if s_name == 'primitiveGroup'):
                hasTracks = False
                for prop in (p for name, p in sub['material'].items() if name == 'property' and p.has_key('Texture')):
                    newTexture = texDir + prop['Texture'].asString
                    if idx and 'tracks' in newTexture and prop.asString == 'diffuseMap':
                        newTexture = 'vehicles/skins/tracks/track_AM.dds'
                        hasTracks = True
                    if ResMgr.isFile(newTexture):
                        prop.writeString('Texture', newTexture.replace('\\', '/'))
                if hasTracks:
                    sub['material'].writeString('fx', 'shaders/std_effects/lightonly_alpha.fx')
            if section['primitivesName'] is None:
                section.writeString('primitivesName', os.path.splitext(memberFileName)[0])
        section.save()


@events.LoginView.populate.before
def before_Login_populate(*_, **__):
    wgc_mode._g_firstEntry = not (g_config.data['enabled'] and g_config.skinsData['models'] and not skinsChecked)


@events.LoginView.populate.after
def new_Login_populate(self, *_, **__):
    if g_config.data['enabled'] and g_config.skinsData['models'] and not skinsChecked:
        self.as_setDefaultValuesS({
            'loginName': '', 'pwd': '', 'memberMe': self._loginMode.rememberUser,
            'memberMeVisible': self._loginMode.rememberPassVisible,
            'isIgrCredentialsReset': GUI_SETTINGS.igrCredentialsReset,
            'showRecoveryLink': not GUI_SETTINGS.isEmpty('recoveryPswdURL')})
        BigWorld.callback(3, partial(self.app.loadView, SFViewLoadParams('SkinnerLoading'), self))
