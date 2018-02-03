from PYmodsCore import overrideMethod
from gui.Scaleform.daapi.view.lobby.customization import CustomizationItemCMHandler
from gui.Scaleform.daapi.view.lobby.customization.main_view import MainView


@overrideMethod(CustomizationItemCMHandler, '_generateOptions')
def _generateOptions(base, self, ctx=None):
    """ Generate a list of options for  the context menu.
    """
    result = base(self, ctx)
    return [result[-1]] if not isinstance(self._c11nView, MainView) else result
