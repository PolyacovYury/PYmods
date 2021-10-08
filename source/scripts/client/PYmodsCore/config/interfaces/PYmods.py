from .Simple import ConfigInterface, ConfBlockInterface

__all__ = ['PYmodsConfigInterface', 'PYmodsConfBlockInterface']


class PYmodsBase(object):
    def __init__(self):
        self.author = ''
        self.modsGroup = ''
        self.modSettingsID = ''

    def init(self):
        self.author = 'by Polyacov_Yury'
        self.modsGroup = 'PYmods'
        self.modSettingsID = 'PYmodsGUI'


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
