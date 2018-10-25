import binascii
import datetime
import time

import BigWorld
import ResMgr
import SoundGroups
import glob
import os
import shutil
import traceback
import weakref
from PYmodsCore import showConfirmDialog, remDups, loadJson, overrideMethod
from adisp import AdispException, async, process
from functools import partial
from gui import GUI_SETTINGS
from gui.Scaleform.daapi.settings.views import VIEW_ALIAS
from gui.Scaleform.daapi.view.battle.classic.battle_end_warning_panel import _WWISE_EVENTS
from gui.Scaleform.daapi.view.battle.shared.minimap.settings import MINIMAP_ATTENTION_SOUND_ID
from gui.Scaleform.daapi.view.lobby.LobbyView import LobbyView
from gui.Scaleform.daapi.view.login.LoginView import LoginView
from gui.Scaleform.daapi.view.meta.LoginQueueWindowMeta import LoginQueueWindowMeta
from gui.Scaleform.framework import GroupedViewSettings, ScopeTemplates, ViewTypes, g_entitiesFactories
from gui.Scaleform.framework.entities.View import ViewKey
from gui.Scaleform.framework.managers.loaders import SFViewLoadParams
from gui.app_loader.loader import g_appLoader
from helpers import getClientVersion
from zipfile import ZipFile
from . import g_config


def skinsPresenceCheck():
    dirSect = ResMgr.openSection('vehicles/skins/textures/')
    if dirSect is not None and dirSect.keys():
        g_config.skinsData['found'] = True


texReplaced = False
skinsChecked = False
skinsPresenceCheck()
clientIsNew = True
skinsModelsMissing = True
needToReReadSkinsModels = False
modelsDir = BigWorld.curCV + '/vehicles/skins/models/'
skinVehNamesLDict = {}


class SkinnerLoading(LoginQueueWindowMeta):
    def __init__(self):
        super(self.__class__, self).__init__()
        self.lines = []
        self.curPercentage = 0
        self.doLogin = False
        g_config.loadingProxy = weakref.proxy(self)

    def _populate(self):
        super(self.__class__, self)._populate()
        self.__initTexts()

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
        g_config.loadingProxy = None
        self.destroy()
        if needToReReadSkinsModels:
            showConfirmDialog(
                g_config.i18n['UI_restart_header'], g_config.i18n['UI_restart_text'],
                (g_config.i18n['UI_restart_button_restart'], g_config.i18n['UI_restart_button_shutdown']),
                lambda restart: (BigWorld.savePreferences(), (BigWorld.restartGame() if restart else BigWorld.quit())))
        elif self.doLogin:
            loginView = g_appLoader.getDefLobbyApp().containerManager.getViewByKey(ViewKey(VIEW_ALIAS.LOGIN))
            if loginView and loginView.loginManager.getPreference('remember_user'):
                password = '*' * loginView.loginManager.getPreference('password_length')
                login = loginView.loginManager.getPreference('login')
                loginView.onLogin(login, password, loginView._servers.selectedServer['data'], '@' not in login)


g_entitiesFactories.addSettings(
    GroupedViewSettings('SkinnerLoading', SkinnerLoading, 'LoginQueueWindow.swf', ViewTypes.TOP_WINDOW,
                        '', None, ScopeTemplates.DEFAULT_SCOPE, canClose=False))


def CRC32_from_file(filename, localPath):
    buf = str(ResMgr.openSection(filename).asBinary)
    buf = binascii.crc32(buf) & 0xFFFFFFFF & localPath.__hash__()
    return buf


@async
@process
def skinCRC32All(callback):
    global texReplaced, skinVehNamesLDict
    CRC32cache = g_config.skinsCache['CRC32']
    skinsPath = 'vehicles/skins/textures/'
    dirSect = ResMgr.openSection(skinsPath)
    if dirSect is not None and dirSect.keys():
        g_config.skinsData['found'] = True
        print g_config.ID + ': listing', skinsPath, 'for CRC32'
        g_config.loadingProxy.addLine(g_config.i18n['UI_loading_skins'])
        CRC32 = 0
        resultList = []
        for skin in remDups(dirSect.keys()):
            completionPercentage = 0
            g_config.loadingProxy.addBar(g_config.i18n['UI_loading_skinPack'] % os.path.basename(skin))
            skinCRC32 = 0
            skinSect = dirSect[skin]['vehicles']
            nationsList = [] if skinSect is None else remDups(skinSect.keys())
            natLen = len(nationsList)
            for num, nation in enumerate(nationsList):
                nationSect = skinSect[nation]
                vehiclesList = [] if nationSect is None else remDups(nationSect.keys())
                vehLen = len(vehiclesList)
                for vehNum, vehicleName in enumerate(vehiclesList):
                    skinVehNamesLDict.setdefault(vehicleName.lower(), []).append(skin)
                    texPrefix = 'vehicles/' + nation + '/' + vehicleName + '/'
                    vehicleSect = nationSect[vehicleName]
                    textures = []
                    if vehicleSect is not None:
                        textures = [texPrefix + texName
                                    for texName in remDups(vehicleSect.keys()) if texName.endswith('.dds')]
                        skinsSect = vehicleSect['_skins']
                        if skinsSect is not None:
                            for skinName in skinsSect.keys():
                                textures.extend(texPrefix + '_skins/' + skinName + '/' + texName for texName in
                                                remDups(skinsSect[skinName].keys()) if texName.endswith('.dds'))
                    for localPath in textures:
                        texPath = skinsPath + skin + '/' + localPath
                        textureCRC32 = CRC32_from_file(texPath, localPath)
                        skinCRC32 ^= textureCRC32
                    yield doFuncCall()
                    currentPercentage = int(100 * (float(num) + float(vehNum) / float(vehLen)) / float(natLen))
                    if currentPercentage != completionPercentage:
                        completionPercentage = currentPercentage
                        g_config.loadingProxy.updatePercentage(completionPercentage)
            g_config.loadingProxy.onBarComplete()
            if skinCRC32 in resultList:
                print g_config.ID + ': detected duplicate skins pack:', skin.replace(os.sep, '/')
                continue
            CRC32 ^= skinCRC32
            resultList.append(skinCRC32)
        if CRC32cache is not None and str(CRC32) == CRC32cache:
            print g_config.ID + ': skins textures were not changed'
        else:
            if CRC32cache is None:
                print g_config.ID + ': skins textures were reinstalled (or you deleted the CRC32 cache)'
            else:
                print g_config.ID + ': skins textures were changed'
            g_config.skinsCache['CRC32'] = str(CRC32)
            texReplaced = True
        ResMgr.purge(skinsPath)
    else:
        print g_config.ID + ': skins folder is empty'
    BigWorld.callback(0.0, partial(callback, True))


@async
@process
def rmtree(rootPath, callback):
    g_config.loadingProxy.updateTitle(g_config.i18n['UI_loading_header_models_clean'])
    g_config.loadingProxy.addLine(g_config.i18n['UI_loading_skins_clean'])
    rootDirs = os.listdir(rootPath)
    for skinPack in rootDirs:
        g_config.loadingProxy.addBar(g_config.i18n['UI_loading_skinPack_clean'] % os.path.basename(skinPack))
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
                    g_config.loadingProxy.updatePercentage(completionPercentage)
        g_config.loadingProxy.onBarComplete()
        shutil.rmtree(os.path.join(rootPath, skinPack))
    shutil.rmtree(rootPath)
    BigWorld.callback(1.0, partial(callback, True))


@async
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
    needToReReadSkinsModels = g_config.skinsData['found'] and (clientIsNew or skinsModelsMissing or texReplaced)
    if g_config.skinsData['found'] and clientIsNew:
        if os.path.isdir(modelsDir):
            yield rmtree(modelsDir)
        g_config.skinsCache['version'] = getClientVersion()
    if g_config.skinsData['found'] and not os.path.isdir(modelsDir):
        os.makedirs(modelsDir)
    elif not g_config.skinsData['found'] and os.path.isdir(modelsDir):
        print g_config.ID + ': no skins found, deleting', modelsDir
        yield rmtree(modelsDir)
    elif texReplaced and os.path.isdir(modelsDir):
        yield rmtree(modelsDir)
        os.makedirs(modelsDir)
    loadJson(g_config.ID, 'skinsCache', g_config.skinsCache, g_config.configPath, True)
    BigWorld.callback(0.0, partial(callback, True))


@async
@process
def modelsProcess(callback):
    if needToReReadSkinsModels:
        g_config.loadingProxy.updateTitle(g_config.i18n['UI_loading_header_models_unpack'])
        SoundGroups.g_instance.playSound2D(_WWISE_EVENTS.APPEAR)
        modelFileFormats = ('.model', '.visual', '.visual_processed')
        print g_config.ID + ': unpacking vehicle packages'
        for vehPkgPath in glob.glob('./res/packages/vehicles*.pkg') + glob.glob('./res/packages/shared_content*.pkg'):
            completionPercentage = 0
            filesCnt = 0
            g_config.loadingProxy.addBar(g_config.i18n['UI_loading_package'] % os.path.basename(vehPkgPath))
            vehPkg = ZipFile(vehPkgPath)
            fileNamesList = [x for x in vehPkg.namelist() if
                             x.startswith('vehicles') and 'normal' in x and os.path.splitext(x)[1] in modelFileFormats]
            allFilesCnt = len(fileNamesList)
            for fileNum, memberFileName in enumerate(fileNamesList):
                for skinName in skinVehNamesLDict.get(os.path.normpath(memberFileName).split('\\')[2].lower(), []):
                    try:
                        processMember(memberFileName, skinName)
                    except ValueError as e:
                        print g_config.ID + ':', e
                    filesCnt += 1
                    if not filesCnt % 25:
                        yield doFuncCall()
                currentPercentage = int(100 * float(fileNum) / float(allFilesCnt))
                if currentPercentage != completionPercentage:
                    completionPercentage = currentPercentage
                    g_config.loadingProxy.updatePercentage(completionPercentage)
                    yield doFuncCall()
            vehPkg.close()
            g_config.loadingProxy.onBarComplete()
    BigWorld.callback(0.0, partial(callback, True))


@async
def doFuncCall(callback):
    BigWorld.callback(0.0, partial(callback, None))


# noinspection PyPep8,PyPep8
def processMember(memberFileName, skinName):
    skinDir = modelsDir.replace(BigWorld.curCV + '/', '') + skinName + '/'
    texDir = skinDir.replace('models', 'textures')
    skinsSign = 'vehicles/skins/'
    if '.model' in memberFileName:
        oldModel = ResMgr.openSection(memberFileName)
        newModelPath = './' + skinDir + memberFileName
        curModel = ResMgr.openSection(ResMgr.resolveToAbsolutePath(newModelPath), True)
        curModel.copy(oldModel)
        models = [curModel]
        if 'Chassis' in memberFileName:
            dynModelPath = newModelPath.replace('Chassis', 'Chassis_dynamic')
            dynModel = ResMgr.openSection(ResMgr.resolveToAbsolutePath(dynModelPath), True)
            dynModel.copy(oldModel)
            models.append(dynModel)
        for idx, modelSect in enumerate(models):
            if modelSect is None:
                print skinDir + memberFileName
            if modelSect.has_key('parent') and skinsSign not in modelSect['parent'].asString:
                curParent = skinDir + modelSect['parent'].asString
                if idx:
                    curParent = curParent.replace('Chassis', 'Chassis_dynamic')
                modelSect.writeString('parent', curParent.replace('\\', '/'))
            if skinsSign not in modelSect['nodefullVisual'].asString:
                curVisual = skinDir + modelSect['nodefullVisual'].asString
                if idx:
                    curVisual = curVisual.replace('Chassis', 'Chassis_dynamic')
                modelSect.writeString('nodefullVisual', curVisual.replace('\\', '/'))
            modelSect.save()
    elif '.visual' in memberFileName:
        oldVisual = ResMgr.openSection(memberFileName)
        newVisualPath = './' + skinDir + memberFileName
        curVisual = ResMgr.openSection(ResMgr.resolveToAbsolutePath(newVisualPath), True)
        curVisual.copy(oldVisual)
        visuals = [curVisual]
        if 'Chassis' in memberFileName:
            dynVisualPath = newVisualPath.replace('Chassis', 'Chassis_dynamic')
            dynVisual = ResMgr.openSection(ResMgr.resolveToAbsolutePath(dynVisualPath), True)
            dynVisual.copy(oldVisual)
            visuals.append(dynVisual)
        for idx, visualSect in enumerate(visuals):
            for (curName, curSect), oldSect in zip(visualSect.items(), oldVisual.values()):
                if curName != 'renderSet':
                    continue
                for (curSubName, curSSect), oldSSect in zip(curSect['geometry'].items(), oldSect['geometry'].values()):
                    if curSubName != 'primitiveGroup':
                        continue
                    hasTracks = False
                    for (curPName, curProp), oldProp in zip(curSSect['material'].items(), oldSSect['material'].values()):
                        if curPName != 'property' or not curProp.has_key('Texture'):
                            continue
                        curTexture = curProp['Texture'].asString
                        oldTexture = oldProp['Texture'].asString
                        if skinsSign not in curTexture:
                            newTexture = texDir + curTexture
                            if idx and 'tracks' in curTexture and curProp.asString == 'diffuseMap':
                                newTexture = skinsSign + 'tracks/track_AM.dds'
                                hasTracks = True
                            if ResMgr.isFile(newTexture):
                                curProp.writeString('Texture', newTexture.replace('\\', '/'))
                        elif skinsSign in curTexture and not ResMgr.isFile(curTexture):
                            curProp.writeString('Texture', oldTexture.replace('\\', '/'))
                    if hasTracks:
                        curSSect['material'].writeString('fx', 'shaders/std_effects/lightonly_alpha.fx')

            visualSect.writeString('primitivesName', os.path.splitext(memberFileName)[0])
            visualSect.save()


@process
def skinLoader(loginView):
    global skinsChecked
    if g_config.data['enabled'] and g_config.skinsData['found'] and not skinsChecked:
        lobbyApp = g_appLoader.getDefLobbyApp()
        if lobbyApp is not None:
            lobbyApp.loadView(SFViewLoadParams('SkinnerLoading'))
        else:
            return
        jobStartTime = time.time()
        try:
            yield skinCRC32All()
            yield modelsCheck()
            yield modelsProcess()
        except AdispException:
            traceback.print_exc()
        print g_config.ID + ': total models check time:', datetime.timedelta(seconds=round(time.time() - jobStartTime))
        BigWorld.callback(1, partial(SoundGroups.g_instance.playSound2D, 'enemy_sighted_for_team'))
        BigWorld.callback(2, g_config.loadingProxy.onWindowClose)
        skinsChecked = True
        loginView.update()


@overrideMethod(LoginView, '_populate')
def new_Login_populate(base, self):
    base(self)
    if g_config.data['enabled']:
        if g_config.skinsData['found'] and not skinsChecked:
            self.as_setDefaultValuesS({
                'loginName': '', 'pwd': '', 'memberMe': self._loginMode.rememberUser,
                'memberMeVisible': self._loginMode.rememberPassVisible,
                'isIgrCredentialsReset': GUI_SETTINGS.igrCredentialsReset,
                'showRecoveryLink': not GUI_SETTINGS.isEmpty('recoveryPswdURL')})
        BigWorld.callback(3.0, partial(skinLoader, self))
