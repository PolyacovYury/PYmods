from PYmodsCore import overrideMethod
from gui.Scaleform.daapi.view.lobby.customization.customization_style_info import CustomizationStyleInfo, ButtonVO
from gui.customization.shared import getPurchaseMoneyState, isTransactionValid
from gui.impl import backport
from gui.impl.gen import R
from shared_utils import first
from .. import g_config


@overrideMethod(CustomizationStyleInfo, '__makeButtonVO')
def new_makeButtonVO(base, self, style):
    if not g_config.data['enabled']:
        return base(self, style)
    buttonVO = None
    ctx = self._CustomizationStyleInfo__ctx
    if ctx.isOutfitsModified():
        label = backport.text(R.strings.vehicle_customization.commit.apply())
        enabled = True
        if ctx.isBuy:
            stylePrice = style.getBuyPrice().price
            moneyState = getPurchaseMoneyState(stylePrice)
            purchaseItem = first(ctx.getPurchaseItems())
            if purchaseItem is not None and not purchaseItem.isFromInventory:
                label = backport.text(R.strings.vehicle_customization.commit.buy())
                enabled = isTransactionValid(moneyState, stylePrice)
        buttonVO = ButtonVO(enabled=enabled, label=label,
                            disabledTooltip=backport.text(R.strings.vehicle_customization.customization.buyDisabled.body()),
                            visible=True)._asdict()
    return buttonVO
