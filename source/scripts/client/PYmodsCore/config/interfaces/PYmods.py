from .Simple import ConfigInterface, ConfBlockInterface, SettingContainer

__all__ = ['PYmodsConfigInterface', 'PYmodsConfBlockInterface', 'PYmodsSettingContainer']


class PYmodsBase(object):
    def __init__(self):
        self.author = ''
        self.modsGroup = ''
        self.modSettingsID = ''

    def init(self):
        self.author = 'by Polyacov_Yury'
        self.modsGroup = 'PYmods'
        self.modSettingsID = 'PYmodsGUI'

    @property
    def containerClass(self):
        return PYmodsSettingContainer


class PYmodsConfigInterface(PYmodsBase, ConfigInterface):
    def __init__(self):
        PYmodsBase.__init__(self)
        ConfigInterface.__init__(self)

    def init(self):
        PYmodsBase.init(self)
        ConfigInterface.init(self)

    def createTemplate(self):
        raise NotImplementedError


class PYmodsConfBlockInterface(PYmodsBase, ConfBlockInterface):
    def __init__(self):
        PYmodsBase.__init__(self)
        ConfBlockInterface.__init__(self)

    def init(self):
        PYmodsBase.init(self)
        ConfBlockInterface.init(self)

    def createTemplate(self, blockID=None):
        raise NotImplementedError('Template for block %s is not created' % blockID)


class PYmodsSettingContainer(SettingContainer):
    def init(self):
        super(PYmodsSettingContainer, self).init()
        self.i18n = {
            'modsListApiName': "PY's mods settings",
            'modsListApiDescription': "<font color='#DD7700'><b>Polyacov_Yury</b></font>'s modification settings",
            'windowTitle': "Polyacov_Yury's mods settings",
            'enableButtonTooltip': '{HEADER}ON/OFF{/HEADER}{BODY}Enable/disable this mod{/BODY}'}
