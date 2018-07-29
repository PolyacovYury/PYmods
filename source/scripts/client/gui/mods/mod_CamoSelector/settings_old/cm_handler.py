from PYmodsCore import overrideMethod
from gui.Scaleform import MENU
from gui.Scaleform.daapi.view.lobby.customization import CustomizationItemCMHandler
from gui.Scaleform.daapi.view.lobby.customization.customization_cm_handlers import CustomizationOptions
from gui.Scaleform.daapi.view.lobby.customization.main_view import MainView
from items.components.c11n_constants import SeasonType


@overrideMethod(CustomizationItemCMHandler, '_generateOptions')
def _generateOptions(base, self, ctx=None):
    """ Generate a list of options for  the context menu.
    """
    if isinstance(self._c11nView, MainView):
        return base(self, ctx)
    item = self.itemsCache.items.getItemByCD(self._intCD)
    removeFromTankEnabled = False
    for outfit in (self._c11nView.getModifiedOutfit(season) for season in SeasonType.COMMON_SEASONS):
        if outfit.has(item):
            removeFromTankEnabled = True
            break
    return [
        self._makeItem(CustomizationOptions.REMOVE_FROM_TANK, MENU.cst_item_ctx_menu(CustomizationOptions.REMOVE_FROM_TANK),
                       {'enabled': removeFromTankEnabled})]
