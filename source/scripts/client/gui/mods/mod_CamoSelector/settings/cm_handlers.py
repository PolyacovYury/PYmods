from PYmodsCore import overrideMethod
from gui.Scaleform.daapi.view.lobby.customization import CustomizationItemCMHandler as WGCMHandler
from .. import g_config


class CustomizationItemCMHandler(WGCMHandler):
    def _generateOptions(self, ctx=None):
        result = super(CustomizationItemCMHandler, self)._generateOptions(ctx)
        if self.__ctx.isBuy:
            return result
        result = result[-1:]
        result.append(self._makeItem('TEST', 'I am test text', {'enabled': True}, [
            self._makeItem('TEST2', 'I am test2 text', {'enabled': True}),
            self._makeItem('TEST3', 'I am test3 text', {'enabled': False})]))
        result.append(self._makeItem('TEST4', 'I am test4 text', {'enabled': False}, [
            self._makeItem('TEST5', 'I am test5 text and I shall never be visible', {'enabled': True})]))
        return result

    def onOptionSelect(self, optionId):
        if optionId in ('TEST', 'TEST2', 'TEST4'):
            print optionId
            return
        return super(CustomizationItemCMHandler, self).onOptionSelect(optionId)


@overrideMethod(WGCMHandler, '__new__')
def new(base, cls, *a, **kw):
    if not g_config.data['enabled']:
        return base(cls, *a, **kw)
    return base(CustomizationItemCMHandler, *a, **kw)
