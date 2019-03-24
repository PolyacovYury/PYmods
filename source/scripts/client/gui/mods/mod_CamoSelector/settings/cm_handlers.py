from PYmodsCore import overrideMethod
from gui.Scaleform.daapi.view.lobby.customization import CustomizationItemCMHandler
from .. import g_config


@overrideMethod(CustomizationItemCMHandler, '_generateOptions')
def _generateOptions(base, self, ctx=None):
    result = base(self, ctx)
    _ctx = self._CustomizationItemCMHandler__ctx
    if not g_config.data['enabled'] or _ctx.isBuy:
        return result
    result = result[-1:]
    result.append(self._makeItem('TEST', 'I am test text', {'enabled': True}, [
        self._makeItem('TEST2', 'I am test2 text', {'enabled': True}),
        self._makeItem('TEST3', 'I am test3 text', {'enabled': False})]))
    result.append(self._makeItem('TEST4', 'I am test4 text', {'enabled': False}, [
        self._makeItem('TEST5', 'I am test5 text and I shall never be visible', {'enabled': True})]))
    return result


@overrideMethod(CustomizationItemCMHandler, 'onOptionSelect')
def onOptionSelect(base, self, optionId):
    if optionId in ('TEST', 'TEST2', 'TEST4'):
        print optionId
        return
    return base(self, optionId)
