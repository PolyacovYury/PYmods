from PYmodsCore import overrideMethod
from gui.Scaleform.daapi.view.lobby.customization import customization_inscription_controller
from helpers import dependency
from skeletons.gui.customization import ICustomizationService
from .. import g_config


@overrideMethod(customization_inscription_controller, 'isPersonalNumberAllowed')
@dependency.replace_none_kwargs(service=ICustomizationService)
def isPersonalNumberAllowed(base, number, service=None):
    return (g_config.data['enabled'] and not service.getCtx().isBuy) or base(number)
