import traceback

from functools import partial

__all__ = ['g_modsListApi']

try:
    from gui.modsListApi import g_modsListApi
except ImportError:
    print 'PYmodsCore: ModsListApi package not found'


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

try:
    from gui.modsSettingsApi.api import ModsSettingsApi as MSA_Orig


    def overrideAddMod(
            base, container, modsSettingsID, id, name=None, description=None, icon=None, enabled=None, login=None,
            lobby=None, callback=None):
        if id == 'modsSettingsApi':
            id = modsSettingsID
            callback = partial(container.MSAPopulate, callback)
        return base(id, name, description, icon, enabled, login, lobby, callback)


    class ModsSettings(MSA_Orig):
        def __init__(self, modsSettingsID, container):
            self.container = container
            orig = g_modsListApi.__class__.addModification
            g_modsListApi.__class__.addModification = partial(overrideAddMod, orig, container, modsSettingsID)
            super(ModsSettings, self).__init__()
            self.onWindowClosed += container.MSADispose
            g_modsListApi.__class__.addModification = orig

        def settingsLoad(self):
            self.userSettings.update(self.container.i18n)
            self.userSettings['modsListApiIcon'] = self.container.iconPath

        def configLoad(self):
            pass

        def configSave(self):
            pass

except ImportError:
    print 'PYmodsCore: ModsSettingsApi package not found'
    MSA_Orig = ModsSettings = None


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
            config.template = config.createTemplate()
    except StandardError:
        traceback.print_exc()
    if config.modSettingsID not in config.modSettingsContainers:
        c = config.modSettingsContainers[config.modSettingsID] = config.containerClass(config.modSettingsID, config.modsGroup)
        if ModsSettings is None:
            print config.ID + ': no-GUI mode activated'
            return
        c.API = ModsSettings(config.modSettingsID, c)
    msc = config.modSettingsContainers[config.modSettingsID]
    msc.onMSAPopulate += config.onMSAPopulate
    msc.onMSADestroy += config.onMSADestroy
    if hasattr(config, 'blockIDs'):
        for blockID in config.blockIDs:
            msc.MSAHandlers[config.ID + blockID] = {
                'apply': partial(config.onApplySettings, blockID), 'button': partial(config.onButtonPress, blockID)}
            msc.API.setModTemplate(config.ID + blockID, config.template[blockID], msc.MSAApply, msc.MSAButton)
    else:
        msc.MSAHandlers[config.ID] = {'apply': config.onApplySettings, 'button': config.onButtonPress}
        msc.API.setModTemplate(config.ID, config.template, msc.MSAApply, msc.MSAButton)
