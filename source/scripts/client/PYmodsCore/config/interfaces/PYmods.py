from .Simple import ConfigInterface, ConfBlockInterface, SettingContainer

__all__ = ['PYmodsConfigInterface', 'PYmodsConfBlockInterface', 'PYmodsSettingContainer']


def init(self):
    self.author = 'by Polyacov_Yury'
    self.modsGroup = 'PYmods'
    self.modSettingsID = 'PYmodsGUI'


def postInit(self):
    self.containerClass = PYmodsSettingContainer


class PYmodsConfigInterface(ConfigInterface):
    def init(self):
        init(self)
        super(PYmodsConfigInterface, self).init()
        postInit(self)

    def createTemplate(self):
        raise NotImplementedError


class PYmodsConfBlockInterface(ConfBlockInterface):
    def init(self):
        init(self)
        super(PYmodsConfBlockInterface, self).init()
        postInit(self)

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
