from PYmodsCore import overrideMethod
from gui.Scaleform.daapi.settings.views import VIEW_ALIAS
from gui.Scaleform.daapi.view.lobby.customization.shared import C11nMode
from gui.Scaleform.managers.PopoverManager import PopoverManager
from helpers import dependency
from skeletons.gui.customization import ICustomizationService
from .. import g_config


@overrideMethod(PopoverManager, 'requestShowPopover')
@dependency.replace_none_kwargs(srv=ICustomizationService)
def new_requestShowPopover(base, self, alias, data, srv=None):
    if g_config.data['enabled'] and alias == VIEW_ALIAS.CUSTOMIZATION_ITEMS_POPOVER and srv.getCtx().mode == C11nMode.STYLE:
        alias = VIEW_ALIAS.CUSTOMIZATION_KIT_POPOVER
    return base(self, alias, data)
