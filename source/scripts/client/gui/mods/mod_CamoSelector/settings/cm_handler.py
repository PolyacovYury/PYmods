from Event import Event
from PYmodsCore import overrideMethod
from gui.Scaleform import MENU
from gui.Scaleform.daapi.view.lobby.customization import CustomizationItemCMHandler
from gui.Scaleform.daapi.view.lobby.customization.customization_cm_handlers import CustomizationOptions
from gui.Scaleform.daapi.view.lobby.customization.main_view import MainView
from gui.Scaleform.framework import ViewTypes
from items.components.c11n_constants import SeasonType


@overrideMethod(CustomizationItemCMHandler, '__init__')
def __init__(base, self, cmProxy, ctx=None):
    self._c11nView = self.app.containerManager.getContainer(ViewTypes.LOBBY_SUB).getView()
    if isinstance(self._c11nView, MainView):
        base(self, cmProxy, ctx)
        return
    self._intCD = 0
    super(CustomizationItemCMHandler, self).__init__(cmProxy, ctx,
                                                     {CustomizationOptions.REMOVE_FROM_TANK: 'removeItemFromTank'})
    self.onSelected = Event(self._eManager)
    self._item = self.itemsCache.items.getItemByCD(self._intCD)


@overrideMethod(CustomizationItemCMHandler, '__init__')
def fini(base, self):
    if isinstance(self._c11nView, MainView):
        base(self)
        return
    self.onSelected.clear()
    self.onSelected = None
    super(CustomizationItemCMHandler, self).fini()
    return


@overrideMethod(CustomizationItemCMHandler, 'removeItemFromTank')
def removeItemFromTank(base, self):
    """ Removes the item from the currently selected tank.
    """
    if isinstance(self._c11nView, MainView):
        base(self)
        return
    self.onSelected(CustomizationOptions.REMOVE_FROM_TANK, self._intCD)


@overrideMethod(CustomizationItemCMHandler, '_generateOptions')
def _generateOptions(base, self, ctx=None):
    """ Generate a list of options for  the context menu.
    """
    if isinstance(self._c11nView, MainView):
        base(self, ctx)
        return
    item = self.itemsCache.items.getItemByCD(self._intCD)
    style = self._c11nView.getModifiedStyle()
    removeFromTankEnabled = style.intCD == item.intCD if style is not None else False
    for outfit in (self._c11nView.getModifiedOutfit(season) for season in SeasonType.COMMON_SEASONS):
        if outfit.has(item):
            removeFromTankEnabled = True
            break

    return [self._makeItem(CustomizationOptions.REMOVE_FROM_TANK,
                           MENU.cst_item_ctx_menu(CustomizationOptions.REMOVE_FROM_TANK),
                           {'enabled': removeFromTankEnabled})]


@overrideMethod(CustomizationItemCMHandler, '_initFlashValues')
def _initFlashValues(base, self, ctx):
    if isinstance(self._c11nView, MainView):
        base(self, ctx)
        return
    self._intCD = ctx.itemID
