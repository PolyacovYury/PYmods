from PYmodsCore import overrideMethod
from gui.Scaleform.daapi.view.lobby.customization import CustomizationItemCMHandler
from gui.Scaleform.daapi.view.lobby.customization.customization_cm_handlers import CustomizationOptions
from gui.Scaleform.daapi.view.lobby.customization.main_view import MainView


@overrideMethod(CustomizationItemCMHandler, '__init__')
def __init__(base, self, cmProxy, ctx=None):
    base(self, cmProxy, ctx)
    if not isinstance(self._c11nView, MainView):
        self._CustomizationItemCMHandler__handlers = {CustomizationOptions.REMOVE_FROM_TANK: 'removeItemFromTank'}


@overrideMethod(CustomizationItemCMHandler, '_generateOptions')
def _generateOptions(base, self, ctx=None):
    """ Generate a list of options for  the context menu.
    """
    result = base(self, ctx)
    return [result[-1]] if isinstance(self._c11nView, MainView) else result
