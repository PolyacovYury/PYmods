from CurrentVehicle import g_currentVehicle
from PYmodsCore import overrideMethod
from gui.Scaleform.daapi.view.lobby.customization import (
    main_view as mw, shared as sh, customization_style_info as si)
from gui.customization.constants import CustomizationModes
from gui.customization.shared import SEASONS_ORDER, getPurchaseMoneyState, isTransactionValid
from gui.impl import backport
from gui.impl.gen import R
from gui.shared.formatters import icons, text_styles
from gui.shared.gui_items import GUI_ITEM_TYPE
from gui.shared.utils.requesters import REQ_CRITERIA
from helpers import dependency
from items.components import c11n_components as c11c
from items.components.c11n_constants import EDITABLE_STYLE_STORAGE_DEPTH
from shared_utils import first
from skeletons.gui.customization import ICustomizationService
from .. import g_config


@overrideMethod(c11c, 'isPersonalNumberAllowed')
@dependency.replace_none_kwargs(service=ICustomizationService)
def isPersonalNumberAllowed(base, number, service=None):
    return (g_config.data['enabled'] and not service.getCtx().isBuy) or base(number)


@overrideMethod(mw.MainView, '__setNotificationCounters')
def new_setNotificationCounters(base, self):
    if not g_config.data['enabled']:
        return base(self)
    ctx = self._MainView__ctx
    itemTypes = sh.getItemTypesAvailableForVehicle() if ctx.isBuy else ()
    if not itemTypes:
        return self.as_setNotificationCountersS([0 for _ in SEASONS_ORDER])
    seasonCounters = {season: 0 for season in SEASONS_ORDER}
    itemsFilter = not REQ_CRITERIA.CUSTOMIZATION.ALL_SEASON
    if ctx.modeId == sh.CustomizationModes.EDITABLE_STYLE:
        itemsFilter |= REQ_CRITERIA.CUSTOM(lambda item: ctx.mode.style.isItemInstallable(item))
    for season in SEASONS_ORDER:
        if season != ctx.season:
            seasonCounters[season] = g_currentVehicle.item.getC11nItemsNoveltyCounter(
                g_currentVehicle.itemsCache.items, itemTypes, season, itemsFilter)

    self.as_setNotificationCountersS([seasonCounters[season] for season in SEASONS_ORDER])


@overrideMethod(mw.MainView, 'onPressClearBtn')
def new_onPressClearBtn(base, self):
    base(self)
    if g_config.data['enabled']:
        self._MainView__ctx.cancelChanges()


# noinspection DuplicatedCode
@overrideMethod(mw.MainView, 'as_setHeaderDataS')
def as_setHeaderDataS(base, self, data):
    ctx = self._MainView__ctx
    if ctx.isBuy and ctx.mode.modeId == CustomizationModes.STYLED:
        showSpecialLabel = False
        counter = 0
        for intCD in self._MainView__bottomPanel._carouselDP.collection:
            item = self.service.getItemByCD(intCD)
            if item.itemTypeID != GUI_ITEM_TYPE.STYLE:
                break
            if item.canBeEditedForVehicle(g_currentVehicle.item.intCD):
                counter += 1
            if counter > EDITABLE_STYLE_STORAGE_DEPTH:
                showSpecialLabel = True
                break
        if showSpecialLabel:
            storedStylesCount = len(self.service.getStoredStyleDiffs())
            img = icons.makeImageTag(backport.image(R.images.gui.maps.icons.customization.edited_big()))
            label = text_styles.vehicleStatusSimpleText(backport.text(
                R.strings.vehicle_customization.savedStyles.label(), img=img, current=storedStylesCount,
                max=EDITABLE_STYLE_STORAGE_DEPTH))
            data['tankInfo'] = label
    return base(self, data)


@overrideMethod(si.CustomizationStyleInfo, '__makeButtonVO')
def new_makeButtonVO(base, self, style):
    if not g_config.data['enabled']:
        return base(self, style)
    ctx = self._CustomizationStyleInfo__ctx
    if not ctx.isOutfitsModified():
        return None
    label = backport.text(R.strings.vehicle_customization.commit.apply())
    enabled = True
    if ctx.isBuy:
        stylePrice = style.getBuyPrice().price
        moneyState = getPurchaseMoneyState(stylePrice)
        purchaseItem = first(ctx.mode.getPurchaseItems())
        if purchaseItem is not None and not purchaseItem.isFromInventory:
            label = backport.text(R.strings.vehicle_customization.commit.buy())
            enabled = isTransactionValid(moneyState, stylePrice)
    return si.ButtonVO(enabled=enabled, label=label, disabledTooltip=backport.text(
        R.strings.vehicle_customization.customization.buyDisabled.body()), visible=True)._asdict()
