from PYmodsCore import BigWorld_callback, overrideMethod
from account_helpers.AccountSettings import AccountSettings, CUSTOMIZATION_SECTION
from gui.Scaleform.daapi.view.lobby.customization import (
    customization_inscription_controller as ic, customization_style_info as si,
    vehicle_anchor_states as vas, vehicle_anchors_updater as vau,
)
from gui.Scaleform.daapi.view.lobby.customization.context import custom_mode
from gui.Scaleform.daapi.view.lobby.customization.popovers.custom_popover import CustomPopoverDataProvider
from gui.Scaleform.daapi.view.lobby.customization.popovers.editable_style_popover import EditableStylePopover
from gui.Scaleform.daapi.view.lobby.customization.popovers.style_popover import StylePopoverDataProvider
from gui.Scaleform.daapi.view.lobby.customization.progression_styles.stage_switcher import StageSwitcherView
from gui.Scaleform.daapi.view.lobby.customization.shared import CustomizationTabs, isSlotFilled
from gui.customization.shared import getPurchaseMoneyState, isTransactionValid
from gui.impl.backport import text
from gui.impl.gen import R
from gui.impl.lobby.customization.progressive_items_view.progressive_items_view import ProgressiveItemsView
from gui.shared.gui_items import GUI_ITEM_TYPE
from gui.shared.gui_items.Vehicle import Vehicle
from gui.shared.gui_items.customization.slots import EmblemSlot
from helpers import dependency
from items.components import c11n_components as c11c
from shared_utils import first
from skeletons.gui.customization import ICustomizationService
from vehicle_outfit.outfit import ANCHOR_TYPE_TO_SLOT_TYPE_MAP, Area
from .shared import fixIconPath, isSlotLocked
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
    label = text(R.strings.vehicle_customization.commit.apply())
    enabled = True
    if ctx.isPurchase:
        stylePrice = style.getBuyPrice().price
        moneyState = getPurchaseMoneyState(stylePrice)
        purchaseItem = first(ctx.mode.getPurchaseItems())
        if purchaseItem is not None and not purchaseItem.isFromInventory:
            label = text(R.strings.vehicle_customization.commit.buy())
            enabled = isTransactionValid(moneyState, stylePrice)
    return si.ButtonVO(enabled=enabled, label=label, disabledTooltip=text(
        R.strings.vehicle_customization.customization.buyDisabled.body()), visible=True)._asdict()


@overrideMethod(CustomPopoverDataProvider, '__makeItemDataVO')
@overrideMethod(StylePopoverDataProvider, '__makeItemDataVO')
@overrideMethod(EditableStylePopover, '__makeItemDataVO')
def new_makeItemDataVO(base, itemData, *a, **k):
    data = base(itemData, *a, **k)
    data['icon'] = fixIconPath(data['icon'])
    return data


@overrideMethod(ProgressiveItemsView, '__setEachLevelInfo')
def new_setEachLevelInfo(base, self, model, item):
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
@dependency.replace_none_kwargs(service=ICustomizationService)
def new_onSelectItem(base, self, args=None, service=None):
    if not g_config.data['enabled']:
        return base(self)
    if args is not None:
        BigWorld_callback(0, service.getCtx().changeModeWithProgressionDecal, int(args['intCD']), int(args['level']))
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
def new_initialize(base, self, *args, **kwargs):
    base(self, *args, **kwargs)
    if not g_config.data['enabled']:
        return
    events = self._StageSwitcherView__ctx.events
    events.onModeChanged += self.updateCSInfo
    events.onTabChanged += self.updateCSInfo
    events.onSeasonChanged += self.updateCSInfo
    events.onChangesCanceled += self.updateCSInfo
    events.onItemsRemoved += self.updateCSInfo
    events.onItemInstalled += self.updateCSInfo


@overrideMethod(StageSwitcherView, '_finalize')
def new_finalize(base, self):
    if not g_config.data['enabled']:
        return base(self)
    events = self._StageSwitcherView__ctx.events
    events.onItemInstalled -= self.updateCSInfo
    events.onItemsRemoved -= self.updateCSInfo
    events.onChangesCanceled -= self.updateCSInfo
    events.onSeasonChanged -= self.updateCSInfo
    events.onTabChanged -= self.updateCSInfo
    events.onModeChanged -= self.updateCSInfo
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


@overrideMethod(StageSwitcherView, '__onChange')
def new_onChange(_, self, *args):
    if not args or args[0]['selectedLevel'] is None:
        return
    selectedLevel = int(args[0]['selectedLevel'])
    with self.viewModel.transaction() as tx:
        tx.setSelectedLevel(args[0]['selectedLevel'])
    ctx = self._StageSwitcherView__ctx
    if ctx is not None and ctx.mode.tabId == CustomizationTabs.STYLES:
        ctx.mode.changeStyleProgressionLevel(selectedLevel)
    else:
        self._StageSwitcherView__customizationService.changeStyleProgressionLevelPreview(selectedLevel)


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


@overrideMethod(vas.Anchor, 'updateState')
def new_updateState(_, self):
    ctx = self._Anchor__ctx
    outfit = ctx.mode.getModifiedOutfit(ctx.season)
    if isSlotFilled(outfit, self.slotId):
        newState = vas.UnselectedFilledState(self)
    elif isSlotLocked(outfit, self.slotId):
        newState = vas.LockedState(self)
    else:
        newState = vas.UnselectedEmptyState(self)
    if self.stateID != newState.stateID:
        self.changeState(newState)


# noinspection PyUnusedLocal
@overrideMethod(vau.VehicleAnchorsUpdater, '__onItemInstalled')
def new_onItemInstalled(base, self, item, slotId, season, component):
    processedAnchors = self._VehicleAnchorsUpdater__processedAnchors
    anchor = processedAnchors.get(slotId)
    if anchor is not None:
        anchor.state.onItemInstalled()
    outfit = self._VehicleAnchorsUpdater__ctx.mode.currentOutfit
    for slotId, anchor in processedAnchors.iteritems():
        if isSlotLocked(outfit, slotId):
            anchor.state.onLocked()
        else:
            anchor.state.onUnlocked()

    self._VehicleAnchorsUpdater__changeAnchorsStates()
    self._VehicleAnchorsUpdater__updateAnchorsVisability()
