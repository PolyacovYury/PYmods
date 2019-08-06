from CurrentVehicle import g_currentVehicle
from PYmodsCore import overrideMethod
from gui.Scaleform.daapi.settings.views import VIEW_ALIAS as ALIAS
from gui.Scaleform.daapi.view.lobby.customization import main_view as mw, shared as sh, tooltips as tt,\
    customization_inscription_controller as ic, customization_style_info as si
from gui.Scaleform.managers.PopoverManager import PopoverManager
from gui.customization.shared import SEASONS_ORDER, getPurchaseMoneyState, isTransactionValid
from gui.impl import backport
from gui.impl.gen import R
from gui.shared.gui_items import GUI_ITEM_TYPE
from helpers import dependency
from shared_utils import first
from skeletons.gui.customization import ICustomizationService
from .. import g_config


@overrideMethod(ic, 'isPersonalNumberAllowed')
@dependency.replace_none_kwargs(service=ICustomizationService)
def isPersonalNumberAllowed(base, number, service=None):
    return (g_config.data['enabled'] and not service.getCtx().isBuy) or base(number)


@overrideMethod(PopoverManager, 'requestShowPopover')
@dependency.replace_none_kwargs(srv=ICustomizationService)
def new_requestShowPopover(base, self, alias, data, srv=None):
    if g_config.data['enabled'] and alias == ALIAS.CUSTOMIZATION_ITEMS_POPOVER and srv.getCtx().mode == sh.C11nMode.STYLE:
        alias = ALIAS.CUSTOMIZATION_KIT_POPOVER
    return base(self, alias, data)


@overrideMethod(mw.MainView, '__setNotificationCounters')
def new_setNotificationCounters(base, self):
    if not g_config.data['enabled']:
        return base(self)
    ctx = self._MainView__ctx
    currentSeason = ctx.currentSeason
    seasonCounters = {season: 0 for season in SEASONS_ORDER}
    itemTypes = GUI_ITEM_TYPE.CUSTOMIZATIONS if ctx.isBuy else ()
    for season in SEASONS_ORDER:
        seasonCounters[season] = (
            0 if not itemTypes or currentSeason == season else g_currentVehicle.item.getC11nItemsNoveltyCounter(
                g_currentVehicle.itemsCache.items, itemTypes, season))

    self.as_setNotificationCountersS([seasonCounters[season] for season in SEASONS_ORDER])


@overrideMethod(si.CustomizationStyleInfo, '__makeButtonVO')
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
        buttonVO = si.ButtonVO(enabled=enabled, label=label, disabledTooltip=backport.text(
            R.strings.vehicle_customization.customization.buyDisabled.body()), visible=True)._asdict()
    return buttonVO


@overrideMethod(tt.NonHistoricTooltip, '_packBlocks')
def new_packBlocks(base, self, isNonHistoric, isInfo, isCustomStyleMode):
    if g_config.data['enabled']:
        isCustomStyleMode = self.service.getCtx().mode == sh.C11nMode.CUSTOM
    return base(self, isNonHistoric, isInfo, isCustomStyleMode)
