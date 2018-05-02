import binascii
import datetime
import time

import BigWorld
import PYmodsCore
import ResMgr
import SoundGroups
import glob
import os
import shutil
import traceback
import weakref
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
from gui.Scaleform.framework.managers.loaders import ViewLoadParams
from gui.app_loader.loader import g_appLoader
from helpers import getClientVersion
from zipfile import ZipFile
from . import g_config


def skinsPresenceCheck():
    dirSect = ResMgr.openSection('vehicles/skins/textures/')
    if dirSect is not None and dirSect.keys():
        g_config.skinsFound = True


texReplaced = False
skinsChecked = False
g_config.skinsFound = False
skinsPresenceCheck()
clientIsNew = True
skinsModelsMissing = True
needToReReadSkinsModels = False
modelsDir = BigWorld.curCV + '/vehicles/skins/models/'
skinVehNamesLDict = {}


class RemodEnablerLoading(LoginQueueWindowMeta):
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
        self.as_setCancelLabelS(g_config.i18n['UI_loading_autoLogin%s' % ('_cancel' if self.doLogin else '')])

    def updateTitle(self, title):
        self.as_setTitleS(title)

    def updateMessage(self):
        self.as_setMessageS(''.join(line.join(("<p align='left'>", "</p>")) for line in self.lines))

    def addLine(self, line):
        if len(self.lines) == 8:
            del self.lines[0]
        self.lines.append(line)
        self.updateMessage()

    def onComplete(self):
        self.lines[-1] += g_config.i18n['UI_loading_done'].join(("<font color='#00FF00'>", '</font>'))
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
        if self.doLogin:
            loginView = g_appLoader.getDefLobbyApp().containerManager.getViewByKey(ViewKey(VIEW_ALIAS.LOGIN))
            if loginView and loginView._rememberUser:
                password = '*' * loginView.loginManager.getPreference('password_length')
                login = loginView.loginManager.getPreference('login')
                loginView.onLogin(login, password, loginView._servers.selectedServer['data'], '@' not in login)


g_entitiesFactories.addSettings(
    GroupedViewSettings('RemodEnablerLoading', RemodEnablerLoading, 'LoginQueueWindow.swf', ViewTypes.TOP_WINDOW,
                        '', None, ScopeTemplates.DEFAULT_SCOPE))


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
        g_config.skinsFound = True
        print 'RemodEnabler: listing %s for CRC32' % skinsPath
        g_config.loadingProxy.addLine(g_config.i18n['UI_loading_skins'])
        CRC32 = 0
        resultList = []
        for skin in PYmodsCore.remDups(dirSect.keys()):
            completionPercentage = 0
            g_config.loadingProxy.addBar(g_config.i18n['UI_loading_skinPack'] % os.path.basename(skin))
            skinCRC32 = 0
            skinSect = ResMgr.openSection(skinsPath + skin + '/vehicles/')
            nationsList = [] if skinSect is None else PYmodsCore.remDups(skinSect.keys())
            natLen = len(nationsList)
            for num, nation in enumerate(nationsList):
                nationSect = ResMgr.openSection(skinsPath + skin + '/vehicles/' + nation)
                vehiclesList = [] if nationSect is None else PYmodsCore.remDups(nationSect.keys())
                vehLen = len(vehiclesList)
                for vehNum, vehicleName in enumerate(vehiclesList):
                    skinVehNamesLDict.setdefault(vehicleName.lower(), []).append(skin)
                    vehicleSect = ResMgr.openSection(skinsPath + skin + '/vehicles/' + nation + '/' + vehicleName)
                    for texture in [] if vehicleSect is None else (
                            texName for texName in PYmodsCore.remDups(vehicleSect.keys()) if texName.endswith('.dds')):
                        localPath = 'vehicles/' + nation + '/' + vehicleName + '/' + texture
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
                print 'RemodEnabler: detected duplicate skins pack:', skin.replace(os.sep, '/')
                continue
            CRC32 ^= skinCRC32
            resultList.append(skinCRC32)
        if CRC32cache is not None and str(CRC32) == CRC32cache:
            print 'RemodEnabler: skins textures were not changed'
        else:
            if CRC32cache is None:
                print 'RemodEnabler: skins textures were reinstalled (or you deleted the CRC32 cache)'
            else:
                print 'RemodEnabler: skins textures were changed'
            g_config.skinsCache['CRC32'] = str(CRC32)
            texReplaced = True
    else:
        print 'RemodEnabler: skins folder is empty'
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
    shutil.rmtree(os.path.join(rootPath))
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
            print 'RemodEnabler: skins client version changed'
    else:
        print 'RemodEnabler: skins client version cache not found'

    if os.path.isdir(modelsDir):
        if len(glob.glob(modelsDir + '*')):
            skinsModelsMissing = False
        else:
            print 'RemodEnabler: skins models dir is empty'
    else:
        print 'RemodEnabler: skins models dir not found'
    needToReReadSkinsModels = g_config.skinsFound and (clientIsNew or skinsModelsMissing or texReplaced)
    if g_config.skinsFound and clientIsNew:
        if os.path.isdir(modelsDir):
            yield rmtree(modelsDir)
        g_config.skinsCache['version'] = getClientVersion()
    if g_config.skinsFound and not os.path.isdir(modelsDir):
        os.makedirs(modelsDir)
    elif not g_config.skinsFound and os.path.isdir(modelsDir):
        print 'RemodEnabler: no skins found, deleting %s' % modelsDir
        yield rmtree(modelsDir)
    elif texReplaced and os.path.isdir(modelsDir):
        yield rmtree(modelsDir)
        os.makedirs(modelsDir)
    PYmodsCore.loadJson(g_config.ID, 'skinsCache', g_config.skinsCache, g_config.configPath, True)
    BigWorld.callback(0.0, partial(callback, True))


@async
@process
def modelsProcess(callback):
    if needToReReadSkinsModels:
        g_config.loadingProxy.updateTitle(g_config.i18n['UI_loading_header_models_unpack'])
        SoundGroups.g_instance.playSound2D(_WWISE_EVENTS.APPEAR)
        modelFileFormats = ('.model', '.visual', '.visual_processed')
        print 'RemodEnabler: unpacking vehicle packages'
        for vehPkgPath in glob.glob('./res/packages/vehicles*.pkg') + glob.glob('./res/packages/shared_content*.pkg'):
            completionPercentage = 0
            filesCnt = 0
            g_config.loadingProxy.addBar(g_config.i18n['UI_loading_package'] % os.path.basename(vehPkgPath))
            vehPkg = ZipFile(vehPkgPath)
            fileNamesList = filter(
                lambda x: x.startswith('vehicles') and 'normal' in x and os.path.splitext(x)[1] in modelFileFormats,
                vehPkg.namelist())
            allFilesCnt = len(fileNamesList)
            for fileNum, memberFileName in enumerate(fileNamesList):
                if not needToReReadSkinsModels:
                    continue
                for skinName in skinVehNamesLDict.get(os.path.normpath(memberFileName).split('\\')[2].lower(), []):
                    processMember(memberFileName, skinName)
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
    skinDir = modelsDir.replace('%s/' % BigWorld.curCV, '') + skinName + '/'
    texDir = skinDir.replace('models', 'textures')
    skinsSign = 'vehicles/skins/'
    if '.model' in memberFileName:
        oldModel = ResMgr.openSection(memberFileName)
        newModelPath = skinDir + memberFileName
        curModel = ResMgr.openSection(newModelPath, True)
        curModel.copy(oldModel)
        models = [curModel]
        if 'Chassis' in memberFileName:
            dynModelPath = newModelPath.replace('Chassis', 'Chassis_dynamic')
            dynModel = ResMgr.openSection(dynModelPath, True)
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
        newVisualPath = skinDir + memberFileName
        curVisual = ResMgr.openSection(newVisualPath, True)
        curVisual.copy(oldVisual)
        visuals = [curVisual]
        if 'Chassis' in memberFileName:
            dynVisualPath = newVisualPath.replace('Chassis', 'Chassis_dynamic')
            dynVisual = ResMgr.openSection(dynVisualPath, True)
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
    if g_config.data['enabled'] and g_config.skinsFound and not skinsChecked:
        lobbyApp = g_appLoader.getDefLobbyApp()
        if lobbyApp is not None:
            lobbyApp.loadView(ViewLoadParams('RemodEnablerLoading'))
        else:
            return
        jobStartTime = time.time()
        try:
            yield skinCRC32All()
            yield modelsCheck()
            yield modelsProcess()
        except AdispException:
            traceback.print_exc()
        print 'RemodEnabler: total models check time:', datetime.timedelta(seconds=round(time.time() - jobStartTime))
        BigWorld.callback(1, partial(SoundGroups.g_instance.playSound2D, 'enemy_sighted_for_team'))
        BigWorld.callback(2, g_config.loadingProxy.onWindowClose)
        skinsChecked = True
        loginView._setData()


@PYmodsCore.overrideMethod(LoginView, '_populate')
def new_Login_populate(base, self):
    base(self)
    g_config.isInHangar = False
    if g_config.data['enabled']:
        if g_config.skinsFound and not skinsChecked:
            self.as_setDefaultValuesS('', '', self._rememberUser, GUI_SETTINGS.rememberPassVisible,
                                      GUI_SETTINGS.igrCredentialsReset, not GUI_SETTINGS.isEmpty('recoveryPswdURL'))
        BigWorld.callback(3.0, partial(skinLoader, self))


@PYmodsCore.overrideMethod(LobbyView, '_populate')
def new_Lobby_populate(base, self):
    base(self)
    g_config.isInHangar = True
