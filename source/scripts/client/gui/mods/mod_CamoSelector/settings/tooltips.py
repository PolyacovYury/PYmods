from PYmodsCore import overrideMethod
from gui.Scaleform.daapi.view.lobby.customization.shared import C11nMode
from gui.Scaleform.daapi.view.lobby.customization.tooltips import NonHistoricTooltip
from .. import g_config


@overrideMethod(NonHistoricTooltip, '_packBlocks')
def new_packBlocks(base, self, isNonHistoric, isInfo, isCustomStyleMode):
    if g_config.data['enabled']:
        isCustomStyleMode = self.service.getCtx().mode == C11nMode.CUSTOM
    return base(self, isNonHistoric, isInfo, isCustomStyleMode)
