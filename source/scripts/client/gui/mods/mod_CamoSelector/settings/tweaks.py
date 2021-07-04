from PYmodsCore import overrideMethod
from account_helpers.AccountSettings import AccountSettings, CUSTOMIZATION_SECTION
from gui.Scaleform.daapi.view.lobby.customization import (
    customization_inscription_controller as ic, customization_style_info as si,
)
from gui.Scaleform.daapi.view.lobby.customization.context import custom_mode
from gui.Scaleform.daapi.view.lobby.customization.popovers.custom_popover import CustomPopoverDataProvider
from gui.Scaleform.daapi.view.lobby.customization.popovers.editable_style_popover import EditableStylePopover
from gui.Scaleform.daapi.view.lobby.customization.popovers.style_popover import StylePopoverDataProvider
from gui.Scaleform.daapi.view.lobby.customization.progression_styles.stage_switcher import StageSwitcherView
from gui.Scaleform.daapi.view.lobby.customization.shared import CustomizationTabs
from gui.customization.shared import getPurchaseMoneyState, isTransactionValid
from gui.impl import backport
from gui.impl.gen import R
from gui.impl.lobby.customization.progressive_items_view.progressive_items_view import ProgressiveItemsView
from gui.shared.gui_items import GUI_ITEM_TYPE
from gui.shared.gui_items.Vehicle import Vehicle
from gui.shared.gui_items.customization.slots import EmblemSlot
from helpers import dependency, func_utils
from items.components import c11n_components as c11c
from shared_utils import first
from skeletons.gui.customization import ICustomizationService
from vehicle_outfit.outfit import ANCHOR_TYPE_TO_SLOT_TYPE_MAP, Area
from .shared import fixIconPath
from .. import g_config


@overrideMethod(custom_mode, 'isPersonalNumberAllowed')
@overrideMethod(ic, 'isPersonalNumberAllowed')
@overrideMethod(c11c, 'isPersonalNumberAllowed')
@dependency.replace_none_kwargs(service=ICustomizationService)
def isPersonalNumberAllowed(base, number, service=None):
    return (g_config.data['enabled'] and not service.getCtx().isPurchase) or base(number)


@overrideMethod(ic.CustomizationInscriptionController, '_populate')
def new_InscriptionController_populate(base, self):
    settings = AccountSettings.getSettings(CUSTOMIZATION_SECTION)
    settings.update({ic._PRESS_ENTER_HINT_SHOWN_FIELD: 0, ic._ENTER_NUMBER_HINT_SHOWN_FIELD: 0})
    AccountSettings.setSettings(CUSTOMIZATION_SECTION, settings)
    base(self)


@overrideMethod(si.CustomizationStyleInfo, '__makeButtonVO')
def new_makeButtonVO(base, self, style):
    if not g_config.data['enabled']:
        return base(self, style)
    ctx = self._CustomizationStyleInfo__ctx
    if not ctx.isOutfitsModified():
        return None
    label = backport.text(R.strings.vehicle_customization.commit.apply())
    enabled = True
    if ctx.isPurchase:
        stylePrice = style.getBuyPrice().price
        moneyState = getPurchaseMoneyState(stylePrice)
        purchaseItem = first(ctx.mode.getPurchaseItems())
        if purchaseItem is not None and not purchaseItem.isFromInventory:
            label = backport.text(R.strings.vehicle_customization.commit.buy())
            enabled = isTransactionValid(moneyState, stylePrice)
    return si.ButtonVO(enabled=enabled, label=label, disabledTooltip=backport.text(
        R.strings.vehicle_customization.customization.buyDisabled.body()), visible=True)._asdict()


@overrideMethod(CustomPopoverDataProvider, '__makeItemDataVO')
@overrideMethod(StylePopoverDataProvider, '__makeItemDataVO')
@overrideMethod(EditableStylePopover, '__makeItemDataVO')
def __makeItemDataVO(base, itemData, *a, **k):
    data = base(itemData, *a, **k)
    data['icon'] = fixIconPath(data['icon'])
    return data


@overrideMethod(ProgressiveItemsView, '__setEachLevelInfo')
def __setEachLevelInfo(base, self, model, item):
    base(self, model, item)
    if not g_config.data['enabled'] or self._ProgressiveItemsView__customizationService.getCtx().isPurchase:
        return
    model.setCurrentLevel(model.getMaxLevel())
    for level in model.eachLevelInfo.getItems():
        level.setLevelText('')
        level.setInProgress(False)
        level.progressBlock.setHideProgressBarAndString(True)
        level.setUnlocked(True)
        level.progressBlock.setUnlockCondition('')


@overrideMethod(ProgressiveItemsView, '_onSelectItem')
def _onSelectItem(base, self, args=None):
    if not g_config.data['enabled']:
        return base(self)
    if args is not None:
        intCD = int(args['intCD'])
        level = int(args['level'])
        ctx = self._ProgressiveItemsView__customizationService.getCtx()
        func_utils.callback(0.0, ctx, 'changeModeWithProgressionDecal', intCD, level)
    self.destroyWindow()


def updateCSInfo(self, *_):
    ctx = self._StageSwitcherView__ctx
    if ctx.mode.tabId != CustomizationTabs.STYLES:
        return
    originalLevel = 1 if not ctx.isPurchase else (
        ctx.mode.getOriginalOutfit().progressionLevel
        if ctx.mode.originalStyle and ctx.mode.originalStyle.isProgressive else -1)
    selectedLevel = ctx.mode.getStyleProgressionLevel()
    with self.getViewModel().transaction() as model:
        model.setCurrentLevel(originalLevel)
        model.setSelectedLevel(selectedLevel)


StageSwitcherView.updateCSInfo = updateCSInfo


@overrideMethod(StageSwitcherView, '_initialize')
def _initialize(base, self, *args, **kwargs):
    base(self, *args, **kwargs)
    if not g_config.data['enabled']:
        return
    self._StageSwitcherView__ctx.events.onModeChanged += self.updateCSInfo
    self._StageSwitcherView__ctx.events.onChangesCanceled += self.updateCSInfo


@overrideMethod(StageSwitcherView, '_finalize')
def _finalize(base, self):
    if not g_config.data['enabled']:
        return base(self)
    self._StageSwitcherView__ctx.events.onChangesCanceled -= self.updateCSInfo
    self._StageSwitcherView__ctx.events.onModeChanged -= self.updateCSInfo
    base(self)


@overrideMethod(StageSwitcherView, '_onLoading')
def new_onLoading(base, self, *args, **kwargs):
    base(self, *args, **kwargs)
    ctx = self._StageSwitcherView__ctx
    if not g_config.data['enabled'] or ctx.isPurchase:
        return
    progressionLevel = ctx.mode.getStyleProgressionLevel()
    with self.getViewModel().transaction() as model:
        model.setCurrentLevel(1)
        model.setSelectedLevel(progressionLevel)


@overrideMethod(Vehicle, '__initAnchors')
def new_initAnchors(base, self):
    slotsAnchorsById, slotsAnchors = base(self)
    slotsAnchors[GUI_ITEM_TYPE.INSIGNIA] = {area: {} for area in Area.ALL}
    vehDescr = self._descriptor
    for emblemSlot in vehDescr.gun.emblemSlots:
        areaId = Area.GUN
        slotType = ANCHOR_TYPE_TO_SLOT_TYPE_MAP.get(emblemSlot.type)
        if slotType is not None:
            regionIdx = len(slotsAnchors[slotType][areaId])
            slot = EmblemSlot(emblemSlot, areaId, regionIdx)
            slotsAnchors[slotType][areaId][regionIdx] = slot
            slotsAnchorsById[emblemSlot.slotId] = slot
    return slotsAnchorsById, slotsAnchors
