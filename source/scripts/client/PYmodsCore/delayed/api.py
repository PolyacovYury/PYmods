import traceback

from functools import partial

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
        from gui.modsListApi import g_controller

        class ModsSettings(MSA_Orig):
            def __init__(self, ID, cont):
                self.container = cont
                if 'modsSettingsApi' in g_controller.modifications:
                    g_controller.modifications['modsSettingsApi_PYmods'] = g_controller.modifications.pop('modsSettingsApi')
                    g_controller.updateModification('modsSettingsApi_PYmods')
                super(ModsSettings, self).__init__()
                mod = g_controller.modifications[ID] = g_controller.modifications.pop('modsSettingsApi')
                g_controller.updateModification(ID, callback=partial(cont.MSAPopulate, mod._ModificationItem__callback))
                self.onWindowClosed += cont.MSADispose

            def settingsLoad(self):
                self.userSettings.update(self.container.i18n)
                self.userSettings['modsListApiIcon'] = self.container.iconPath

            def configLoad(self):
                pass

            def configSave(self):
                pass

    except ImportError:
        print 'PYmodsCore: ModsSettingsApi package not found'
        MSA_Orig = g_controller = None


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
        print config.ID + ': no-GUI mode activated'
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
