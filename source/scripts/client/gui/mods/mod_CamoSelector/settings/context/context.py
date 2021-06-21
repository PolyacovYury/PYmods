import BigWorld
import Event
import adisp
from BWUtil import AsyncReturn
from CurrentVehicle import g_currentVehicle
from PYmodsCore import overrideMethod
from async import await, async
from contextlib import contextmanager
from gui.Scaleform.daapi.view.lobby.customization.context.context import CustomizationContext as WGCtx, _logger
from gui.Scaleform.daapi.view.lobby.customization.shared import (
    CustomizationTabs, CustomizationModes)
from gui.hangar_cameras.hangar_camera_common import CameraRelatedEvents
from gui.shared import EVENT_BUS_SCOPE, g_eventBus
from gui.shared.utils.decorators import process
from shared_utils import first
from .custom_mode import CustomMode
from .mod_impl import CSModImpl
from .styled_mode import StyledMode
from ..shared import CSMode
from ... import g_config


def ModdedMode(ctx, modeId, baseMode):
    if modeId == CustomizationModes.CUSTOM:
        return CustomMode(ctx, baseMode)
    if modeId == CustomizationModes.STYLED:
        return StyledMode(ctx, baseMode)


class CustomizationContext(WGCtx, CSModImpl):
    def __init__(self):
        CSModImpl.__init__(self)
        self.purchaseMode = CSMode.PURCHASE
        self.__startModeIds = {CSMode.PURCHASE: None, CSMode.INSTALL: None}
        self.__currentModeIds = {CSMode.PURCHASE: None, CSMode.INSTALL: None}
        WGCtx.__init__(self)
        self.__moddedModes = {
            modeId: ModdedMode(self, modeId, self.__origModes[modeId])
            for modeId in (CustomizationModes.CUSTOM, CustomizationModes.STYLED)}

    @property
    def isPurchase(self):
        return self.purchaseMode == CSMode.PURCHASE

    @property
    def __modeId(self):
        return self.__currentModeIds[self.purchaseMode]

    @__modeId.setter
    def __modeId(self, value):
        self.__currentModeIds[self.purchaseMode] = value

    @property
    def __startModeId(self):
        return self.__startModeIds[self.purchaseMode]

    @__startModeId.setter
    def __startModeId(self, value):
        for key in self.__startModeIds:
            self.__startModeIds[key] = value
            self.__currentModeIds[key] = value

    @property
    def __modes(self):
        return self.getMode(self.purchaseMode)

    @__modes.setter
    def __modes(self, value):
        self.__origModes = value

    def getMode(self, purchaseMode, modeId=None):
        if modeId is not None:
            return self.getMode(purchaseMode)[modeId]
        return (self.__origModes, self.__moddedModes)[purchaseMode]

    @property
    def mode(self):
        return self.getMode(self.purchaseMode, self.modeId)

    @property
    def isItemsOnAnotherVeh(self):
        return self.isPurchase and self.__isItemsOnAnotherVeh

    def init(self, season=None, modeId=None, tabId=None):
        WGCtx.init(self, season, modeId, tabId)
        self.events.onPurchaseModeChanged = Event.Event(self.events._eventsManager)
        outfitCache = g_config.getOutfitCache()
        applied = outfitCache.get('style', {}).get('applied', False)
        isStyleInstalled = self._service.isStyleInstalled()
        for purchaseMode in CSMode.PURCHASE, CSMode.INSTALL:
            self.purchaseMode = purchaseMode
            self.getMode(purchaseMode, CustomizationModes.STYLED).start()
            custom = self.getMode(purchaseMode, CustomizationModes.CUSTOM)
            tabId = first(custom._tabs) if self.isPurchase else CustomizationTabs.CAMOUFLAGES
            if not custom.isInited:
                custom.start(tabId)
            else:
                custom.changeTab(tabId)
            self.__currentModeIds[purchaseMode] = self.__startModeIds[purchaseMode] = (
                CustomizationModes.STYLED if (
                    isStyleInstalled if self.isPurchase else (not outfitCache and isStyleInstalled) or applied
                ) else CustomizationModes.CUSTOM
            )
        self.purchaseMode = CSMode.INSTALL
        self.refreshOutfit()
        onLoaded = lambda e: (BigWorld.callback(0, self.refreshOutfit), g_eventBus.removeListener(
            CameraRelatedEvents.VEHICLE_LOADING, onLoaded, EVENT_BUS_SCOPE.DEFAULT) if not e.ctx['started'] else None)
        g_eventBus.addListener(CameraRelatedEvents.VEHICLE_LOADING, onLoaded, EVENT_BUS_SCOPE.DEFAULT)

    def fini(self):
        WGCtx.fini(self)
        for purchaseMode in CSMode.ALL:
            modes = self.getMode(purchaseMode)
            for mode in modes.values():
                mode.fini()
            modes.clear()

    def changePurchaseMode(self, purchaseMode, source=None):
        if self.purchaseMode == purchaseMode and self.modeId != CustomizationModes.EDITABLE_STYLE:
            return
        prevMode = self.mode
        prevMode.unselectItem()
        prevMode.unselectSlot()
        prevMode.stop()
        self.purchaseMode = purchaseMode
        if self.modeId == CustomizationModes.EDITABLE_STYLE:
            self.__modeId = CustomizationModes.STYLED
        newMode = self.mode
        newMode.start(self.mode.tabId, source=source)
        self.refreshOutfit()
        self.events.onBeforeModeChange()
        self.events.onPurchaseModeChanged()
        self.events.onModeChanged(newMode.modeId, prevMode.modeId)
        self.events.onTabChanged(self.mode.tabId)

    @contextmanager
    def overridePurchaseMode(self, desired=CSMode.PURCHASE):
        purchaseMode = self.purchaseMode
        self.purchaseMode = desired
        try:
            yield
        finally:
            self.purchaseMode = purchaseMode

    @async
    def editStyle(self, intCD, source=None):
        if self.isPurchase:
            WGCtx.editStyle(self, intCD, source)
            return
        targetMode = self.getMode(CSMode.INSTALL, CustomizationModes.CUSTOM)
        proceed = True
        if not targetMode.isOutfitsEmpty():
            proceed = yield await(self.createConfirmDialog('flashCol_propertySheet_edit'))
        if not proceed:
            raise AsyncReturn(False)
        self.getMode(CSMode.INSTALL, CustomizationModes.CUSTOM).installStyleItemsToModifiedOutfit(
            self.getMode(CSMode.INSTALL, CustomizationModes.STYLED).getModifiedOutfits())
        self.changeMode(CustomizationModes.CUSTOM, CustomizationTabs.CAMOUFLAGES)
        raise AsyncReturn(True)

    def canEditStyle(self, itemCD):
        if self.isPurchase:
            return WGCtx.canEditStyle(self, itemCD)
        if self.__modeId == CustomizationModes.STYLED:
            outfit = self.mode.getModifiedOutfit()
            if outfit is not None and outfit.style is not None:
                return not outfit.modelsSet
        return False

    @async
    def changeModeWithProgressionDecal(self, itemCD, level):
        goToEditableStyle = self.canEditStyle(itemCD)
        result = True
        if not self.isPurchase and self.modeId == CustomizationModes.STYLED and goToEditableStyle:
            result = yield await(self.editStyle(None))
        if not result:
            return
        if self.modeId in (CustomizationModes.STYLED, CustomizationModes.EDITABLE_STYLE) and not goToEditableStyle:
            result = yield await(self.createConfirmDialog('flashCol_progressionDecal_changeMode'))
        if not result:
            return
        WGCtx.changeModeWithProgressionDecal(self, itemCD)
        item = self._service.getItemByCD(itemCD)
        self.events.onGetItemBackToHand(item, level, scrollToItem=True)
        if not self.isPurchase:
            return
        noveltyCount = self._vehicle.getC11nItemNoveltyCounter(proxy=self._itemsCache.items, item=item)
        if noveltyCount:
            BigWorld.callback(0.0, lambda: self.resetItemsNovelty([item.intCD]))

    def getPurchaseItems(self):
        with self.overridePurchaseMode():
            return self.mode.getPurchaseItems() if self.mode.isOutfitsModified() else []

    @adisp.async
    @process('customizationApply')
    def applyItems(self, purchaseItems, callback):
        self._itemsCache.onSyncCompleted -= self.__onCacheResync
        self.mode.unselectSlot()
        for purchaseMode in CSMode.PURCHASE, CSMode.INSTALL:
            with self.overridePurchaseMode(purchaseMode):
                if not self.isPurchase or (purchaseItems and WGCtx.isOutfitsModified(self)):
                    yield self.mode.applyItems(purchaseItems, self.isModeChanged)
        self.applySettings()
        self.__onCacheResync()
        self._itemsCache.onSyncCompleted += self.__onCacheResync
        callback(None)

    def cancelChanges(self):
        CSModImpl.cancelChanges(self)
        for mode in self.__origModes.values() + self.__moddedModes.values():
            if mode.isInited:
                mode.cancelChanges()
        prevModeId = self.modeId
        self.__currentModeIds = self.__startModeIds.copy()
        self.events.onModeChanged(self.modeId, prevModeId)
        self.events.onTabChanged(self.mode.tabId)
        self.refreshOutfit()

    def isOutfitsModified(self):
        result = CSModImpl.isOutfitsModified(self)
        for purchaseMode in CSMode.PURCHASE, CSMode.INSTALL:
            with self.overridePurchaseMode(purchaseMode):
                result |= WGCtx.isOutfitsModified(self)
        return result

    def __onCacheResync(self, *_):
        if g_currentVehicle.isPresent():
            for purchaseMode in CSMode.ALL:
                modes = self.getMode(purchaseMode)
                for mode in modes.values():
                    if mode.isInited:
                        mode.updateOutfits(preserve=True)
            self.refreshOutfit()
        self.events.onCacheResync()

    def __onVehicleChanged(self):
        if self._vehicle is None or not g_currentVehicle.isPresent():
            _logger.error('There is no vehicle in hangar for customization.')
            return
        preserve = self._vehicle.intCD == g_currentVehicle.item.intCD
        self._vehicle = g_currentVehicle.item
        for purchaseMode in CSMode.ALL:
            modes = self.getMode(purchaseMode)
            for mode in modes.values():
                if mode.isInited:
                    mode.updateOutfits(preserve=preserve)
        self.refreshOutfit()

    def __onVehicleChangeStarted(self):
        if self._vehicle is None or not g_currentVehicle.isPresent():
            _logger.error('There is no vehicle in hangar for customization.')
            return
        elif self._vehicle.intCD == g_currentVehicle.item.intCD:
            return
        for purchaseMode in CSMode.ALL:
            modes = self.getMode(purchaseMode)
            for mode in modes.values():
                if mode.isInited:
                    mode.onVehicleChangeStarted()


@overrideMethod(WGCtx, '__new__')
def new(base, cls, *a, **kw):
    if not g_config.data['enabled']:
        return base(cls, *a, **kw)
    return base(CustomizationContext, *a, **kw)
