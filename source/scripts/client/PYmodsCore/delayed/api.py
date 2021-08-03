import Event
import traceback
from functools import partial
from .. import overrideMethod

__all__ = ['g_modsListApi']

try:
    from gui.modsListApi import g_modsListApi
except ImportError:
    print 'PYmodsCore: ModsListApi package not found, ModsSettingsApi check skipped'


    class ModsList(object):
        @staticmethod
        def addModification(*_, **__):
            return NotImplemented

        @staticmethod
        def updateModification(*_, **__):
            return NotImplemented

        @staticmethod
        def alertModification(*_, **__):
            return NotImplemented

        @staticmethod
        def clearModificationAlert(*_, **__):
            return NotImplemented


    g_modsListApi = ModsList()
    MSA_Orig = None
else:
    try:
        from gui.modsSettingsApi.api import ModsSettingsApi as MSA_Orig
        # noinspection PyUnresolvedReferences
        from gui.modsSettingsApi.hotkeys import HotkeysContoller
        from gui.modsSettingsApi.view import loadView, ModsSettingsApiWindow, HotkeyContextHandler
        from gui.modsSettingsApi._constants import MOD_ICON, MOD_NAME, MOD_DESCRIPTION, VIEW_ALIAS
        from gui.Scaleform.framework.managers.context_menu import ContextMenuManager
        from gui.shared.personality import ServicesLocator as SL
        from gui.Scaleform.framework.entities.View import ViewKey

        ModsSettingsApiWindow.api = None
        HotkeyContextHandler.api = None


        @overrideMethod(ModsSettingsApiWindow, '__init__')
        def new_init(base, self, ctx):
            self.api = ctx
            return base(self, ctx)


        @overrideMethod(ContextMenuManager, 'requestOptions')
        def new_requestOptions(base, self, handlerType, ctx):
            base(self, handlerType, ctx)
            if handlerType == 'modsSettingsHotkeyContextHandler':
                self._ContextMenuManager__currentHandler.api = SL.appLoader.getDefLobbyApp(
                ).containerManager.getViewByKey(ViewKey(VIEW_ALIAS)).api


        class ModsSettings(MSA_Orig):
            def __init__(self, ID, cont):
                self.container = cont
                self.activeMods = set()
                self.config = {'templates': {}, 'settings': {}}
                self.onSettingsChanged = Event.Event()
                self.onButtonClicked = Event.Event()
                self.onWindowClosed = Event.Event()
                self.updateHotKeys = Event.Event()
                self.hotkeys = HotkeysContoller(self)
                self.hotkeys.onUpdated += self.updateHotKeys
                self.userSettings = {}
                self.settingsLoad()
                self.configLoad()
                g_modsListApi.addModification(
                    id=ID,
                    name=self.userSettings.get('modsListApiName') or MOD_NAME,
                    description=self.userSettings.get('modsListApiDescription') or MOD_DESCRIPTION,
                    icon=self.userSettings.get('modsListApiIcon') or MOD_ICON,
                    enabled=True,
                    login=True,
                    lobby=True,
                    callback=partial(cont.MSAPopulate, partial(loadView, self))
                )
                self.onWindowClosed += cont.MSADispose

            def settingsLoad(self):
                self.userSettings.update(self.container.i18n)
                self.userSettings['modsListApiIcon'] = self.container.iconPath

            def configLoad(self):
                pass

            def configSave(self):
                pass

    except ImportError as e:
        print 'PYmodsCore: ModsSettingsApi package not loaded:', e
        MSA_Orig = loadView = ModsSettingsApiWindow = HotkeyContextHandler\
            = MOD_ICON = MOD_NAME = MOD_DESCRIPTION = VIEW_ALIAS = ContextMenuManager = SL = ViewKey = None


def registerSettings(config):
    """
    Register a settings block in this mod's settings window.
    """
    try:
        from helpers import getClientLanguage
        newLang = str(getClientLanguage()).lower()
        if newLang != config.lang:
            config.lang = newLang
            config.loadLang()
    except StandardError:
        traceback.print_exc()
    if MSA_Orig is None:
        print config.LOG, 'no-GUI mode activated'
        return
    if config.modSettingsID not in config.modSettingsContainers:
        c = config.modSettingsContainers[config.modSettingsID] = config.containerClass(config.modSettingsID, config.modsGroup)
        c.API = ModsSettings(config.modSettingsID, c)
    msc = config.modSettingsContainers[config.modSettingsID]
    msc.onMSAPopulate += config.onMSAPopulate
    msc.onMSADestroy += config.onMSADestroy
    if hasattr(config, 'blockIDs'):
        for ID in config.blockIDs:
            msc.MSAHandlers[config.ID + ID] = {
                'apply': partial(config.onApplySettings, blockID=ID), 'button': partial(config.onButtonPress, blockID=ID)}
            msc.API.setModTemplate(config.ID + ID, config.template[ID], msc.MSAApply, msc.MSAButton)
    else:
        msc.MSAHandlers[config.ID] = {'apply': config.onApplySettings, 'button': config.onButtonPress}
        msc.API.setModTemplate(config.ID, config.template, msc.MSAApply, msc.MSAButton)
