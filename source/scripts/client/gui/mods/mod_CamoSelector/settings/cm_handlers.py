from PYmodsCore import overrideMethod
from gui.Scaleform.daapi.view.lobby.customization import CustomizationItemCMHandler
from .shared import CSMode


@overrideMethod(CustomizationItemCMHandler, '_generateOptions')
def _generateOptions(base, self, ctx=None):
    result = base(self, ctx)
    if self._CustomizationItemCMHandler__ctx.mode == CSMode.BUY:
        return result
    return result[-1:]
