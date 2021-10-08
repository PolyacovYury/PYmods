import Event
import traceback
from functools import partial
from .. import loadJson, overrideMethod
from ..config import smart_update

__all__ = ['g_modsListApi']


def try_import():
    try:
        from gui.modsListApi import g_modsListApi as modsListApi
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

        modsListApi = ModsList()
        return modsListApi, None, None
    try:
        from gui.modsSettingsApi.api import ModsSettingsApi as _MSA_Orig
        from gui.modsSettingsApi.hotkeys import HotkeysContoller
        from gui.modsSettingsApi.view import loadView, ModsSettingsApiWindow, HotkeyContextHandler
        from gui.modsSettingsApi._constants import MOD_ICON, MOD_NAME, MOD_DESCRIPTION, STATE_TOOLTIP, VIEW_ALIAS
        from gui.Scaleform.framework.managers.context_menu import ContextMenuManager
        from gui.shared.personality import ServicesLocator as SL
        from gui.Scaleform.framework.entities.View import ViewKey
    except ImportError as e:
        print 'PYmodsCore: ModsSettingsApi package not loaded:', e
        return modsListApi, None, None
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

    class _ModsSettings(_MSA_Orig):
        def __init__(self, modsGroup, ID, langID, i18n):
            self.modsGroup = modsGroup
            self.ID = ID
            self.lang = langID
            self.isMSAWindowOpen = False
            self.activeMods = set()
            self.config = {'templates': {}, 'settings': {}}
            self.settingsListeners = {}
            self.buttonListeners = {}
            self.onSettingsChanged = Event.Event()
            self.onButtonClicked = Event.Event()
            self.onWindowClosed = Event.Event()
            self.updateHotKeys = Event.Event()
            self.onWindowOpened = Event.Event()
            self.hotkeys = HotkeysContoller(self)
            self.hotkeys.onUpdated += self.updateHotKeys
            self.userSettings = {
                'modsListApiName': MOD_NAME,
                'modsListApiDescription': MOD_DESCRIPTION,
                'modsListApiIcon': '../mods/configs/%s/%s/icon.png' % (self.modsGroup, self.ID),
                'windowTitle': MOD_NAME,
                'enableButtonTooltip': STATE_TOOLTIP,
            }
            smart_update(self.userSettings, i18n)
            self.settingsLoad()
            self.configLoad()
            modsListApi.addModification(
                id=ID,
                name=self.userSettings['modsListApiName'],
                description=self.userSettings['modsListApiDescription'],
                icon=self.userSettings['modsListApiIcon'],
                enabled=True,
                login=True,
                lobby=True,
                callback=self.MSAPopulate
            )
            self.onWindowClosed += self.MSADispose

        def MSAPopulate(self):
            self.isMSAWindowOpen = True
            self.onWindowOpened()
            loadView(self)

        def MSADispose(self):
            self.isMSAWindowOpen = False

        def MSAApply(self, alias, *a, **kw):
            self.settingsListeners[alias](*a, **kw)

        def MSAButton(self, alias, *a, **kw):
            self.buttonListeners[alias](*a, **kw)

        def settingsLoad(self):
            smart_update(self.userSettings, loadJson(
                self.ID, self.lang, self.userSettings, 'mods/configs/%s/%s/i18n/' % (self.modsGroup, self.ID)))

        def configLoad(self):
            pass

        def configSave(self):
            pass

        def setModTemplate(self, linkage, template, callback, buttonHandler):
            self.settingsListeners[linkage] = callback
            self.buttonListeners[linkage] = buttonHandler
            return super(_ModsSettings, self).setModTemplate(linkage, template, self.MSAApply, self.MSAButton)

    return modsListApi, _MSA_Orig, _ModsSettings


g_modsListApi, MSA_Orig, ModsSettings = try_import()


def registerSettings(config):
    """
    Register a settings block in this mod's settings window.
    """
    newLangID = config.lang
    try:
        from helpers import getClientLanguage
        newLangID = str(getClientLanguage()).lower()
        if newLangID != config.lang:
            config.lang = newLangID
            config.loadLang()
    except StandardError:
        traceback.print_exc()
    if MSA_Orig is None:
        print config.LOG, 'no-GUI mode activated'
        return
    if config.modSettingsID not in config.modSettingsContainers:
        config.modSettingsContainers[config.modSettingsID] = ModsSettings(
            config.modsGroup, config.modSettingsID, newLangID, config.container_i18n)
    msc = config.modSettingsContainers[config.modSettingsID]
    msc.onWindowOpened += config.onMSAPopulate
    msc.onWindowClosed += config.onMSADestroy
    if not hasattr(config, 'blockIDs'):
        msc.setModTemplate(config.ID, config.template, config.onApplySettings, config.onButtonPress)
        return
    templates = config.template
    [msc.setModTemplate(
        config.ID + ID, templates[ID], partial(config.onApplySettings, blockID=ID), partial(config.onButtonPress, blockID=ID))
        for ID in config.blockIDs]
