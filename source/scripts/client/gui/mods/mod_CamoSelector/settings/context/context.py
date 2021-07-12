from collections import OrderedDict
from contextlib import contextmanager

import adisp
from PYmodsCore import BigWorld_callback, overrideMethod
from async import async, await, await_callback
from gui import SystemMessages
from gui.Scaleform.daapi.view.lobby.customization.context.context import CustomizationContext as WGCtx
from gui.Scaleform.daapi.view.lobby.customization.shared import CustomizationModes, CustomizationTabs, removeItemsFromOutfit
from gui.customization.shared import SEASON_TYPE_TO_NAME
from gui.impl.backport import text
from gui.impl.gen import R
from gui.shared.gui_items import GUI_ITEM_TYPE
from gui.shared.gui_items.processors.common import OutfitApplier
from gui.shared.utils.decorators import process
from items.components.c11n_constants import CUSTOM_STYLE_POOL_ID, EMPTY_ITEM_ID, SeasonType
from .customization_mode import CustomMode as CamoSelectorMode
from ..shared import createConfirmDialog, onVehicleLoadedOnce
from ... import g_config


class CustomizationContext(WGCtx):
    def __init__(self):
        WGCtx.__init__(self)
        self.__modes = OrderedDict(self.__modes)  # make sure that we get updated last
        self.__modes[CustomizationModes.CAMO_SELECTOR] = CamoSelectorMode(self)
        self.__purchaseModeId = None

    @property
    def isPurchase(self):
        return self.modeId != CustomizationModes.CAMO_SELECTOR

    @property
    def purchaseModeId(self):
        return self.__purchaseModeId

    def getMode(self, modeId=None):
        return self.__modes[modeId or self.purchaseModeId]

    @property
    def isItemsOnAnotherVeh(self):
        return self.isPurchase and self.__isItemsOnAnotherVeh

    @property
    def isModeChanged(self):
        return self.isPurchase and self.modeId != self.startModeId

    def init(self, season=None, modeId=None, tabId=None):
        WGCtx.init(self, season, modeId, tabId)
        self.__purchaseModeId = self.modeId
        if modeId is None and tabId is None:
            self.mode.stop()
            self.__modeId = CustomizationModes.CAMO_SELECTOR
            outfitCache = g_config.getOutfitCache()
            style_id = outfitCache.get(SEASON_TYPE_TO_NAME[self.season], {}).get('style', {}).get('id', EMPTY_ITEM_ID)
            isStyleInstalled = self._service.isStyleInstalled()
            self.mode.start(
                CustomizationTabs.STYLES if isStyleInstalled or style_id != EMPTY_ITEM_ID else CustomizationTabs.CAMOUFLAGES)
        self.refreshOutfit()
        onVehicleLoadedOnce(BigWorld_callback, 0, self.refreshOutfit)

    def changeMode(self, modeId, tabId=None, source=None):
        if modeId != CustomizationModes.CAMO_SELECTOR:
            self.__purchaseModeId = modeId
        WGCtx.changeMode(self, modeId, tabId, source)
        onVehicleLoadedOnce(BigWorld_callback, 0, self.refreshOutfit)

    @contextmanager
    def overrideMode(self, desired=CustomizationModes.CAMO_SELECTOR):
        modeId = self.modeId
        self.__modeId = desired
        try:
            yield
        finally:
            self.__modeId = modeId

    @async
    def changeModeWithProgressionDecal(self, itemCD, level):
        goToEditableStyle = self.canEditStyle(itemCD)
        result = True
        if self.modeId in (CustomizationModes.STYLED, CustomizationModes.EDITABLE_STYLE) and not goToEditableStyle:
            result = yield await(createConfirmDialog('flashCol_progressionDecal_changeMode'))
        if not result:
            return
        WGCtx.changeModeWithProgressionDecal(self, itemCD)
        yield await_callback(lambda callback: onVehicleLoadedOnce(BigWorld_callback, 0, callback, None))()
        item = self._service.getItemByCD(itemCD)
        self.events.onGetItemBackToHand(item, level, scrollToItem=True)
        if not self.isPurchase:
            return
        noveltyCount = self._vehicle.getC11nItemNoveltyCounter(proxy=self._itemsCache.items, item=item)
        if noveltyCount:
            BigWorld_callback(0, self.resetItemsNovelty, [item.intCD])

    def getPurchaseItems(self):
        mode = self.__modes[self.__purchaseModeId]
        return mode.getPurchaseItems() if mode.isOutfitsModified() else []

    @adisp.async
    @process('customizationApply')
    def applyItems(self, purchaseItems, callback):
        self._itemsCache.onSyncCompleted -= self.__onCacheResync
        self.mode.unselectItem()
        self.mode.unselectSlot()
        for modeId in (self.__purchaseModeId, CustomizationModes.CAMO_SELECTOR):
            with self.overrideMode(modeId):
                if not self.isPurchase or (purchaseItems or WGCtx.isOutfitsModified(self)):
                    yield self.mode.applyItems(purchaseItems, self.isModeChanged)
        self.__onCacheResync()
        self._itemsCache.onSyncCompleted += self.__onCacheResync
        callback(None)

    def cancelChanges(self):
        for mode in self.__modes.values():
            if mode.isInited:
                mode.cancelChanges()
        self.__purchaseModeId = self.__startModeId
        if self.isPurchase:
            self.changeMode(self.__purchaseModeId)
        self.refreshOutfit()

    def isOutfitsModified(self):
        result = False
        for modeId in (self.__purchaseModeId, CustomizationModes.CAMO_SELECTOR):
            with self.overrideMode(modeId):
                result |= WGCtx.isOutfitsModified(self)
        return result

    def getCustomOutfit(self, vehicleCD, season):  # from service
        outfitsPool = self._itemsCache.items.inventory.getC11nOutfitsFromPool(vehicleCD)
        if not outfitsPool:
            return self._service.getEmptyOutfit()
        styleId, outfits = outfitsPool[0]
        if styleId != CUSTOM_STYLE_POOL_ID:
            return self._service.getEmptyOutfit()
        return self._service.itemsFactory.createOutfit(
            strCompactDescr=outfits.get(season, ''),
            vehicleCD=self._itemsCache.items.inventory.getItemData(vehicleCD).compDescr)

    @process('customizationApply')
    def removeFromOtherVehicle(self, vehicleCD, item):
        self._itemsCache.onSyncCompleted -= self.__onCacheResync
        try:
            vehicle = self._itemsCache.items.getItemByCD(vehicleCD)
            if item.itemTypeID == GUI_ITEM_TYPE.STYLE:
                result = yield OutfitApplier(vehicle, ((self._service.getEmptyOutfit(), SeasonType.ALL),)).request()
                self.handleResult(result)
                return
            requestData = []
            for season in SeasonType.COMMON_SEASONS:
                originalOutfit = self.getCustomOutfit(vehicleCD, season)
                outfit = originalOutfit.copy()
                removeItemsFromOutfit(outfit, lambda i: i.intCD == item.intCD)
                if not outfit.isEqual(originalOutfit):
                    requestData.append((outfit, season))
            if requestData:
                result = yield OutfitApplier(vehicle, requestData).request()
                self.handleResult(result)
        finally:
            self.__onCacheResync()
            self._itemsCache.onSyncCompleted += self.__onCacheResync

    def handleResult(self, result):
        if result.userMsg:
            SystemMessages.pushI18nMessage(result.userMsg, type=result.sysMsgType)
        if result.success:
            return SystemMessages.pushMessage(text(
                R.strings.messenger.serviceChannelMessages.sysMsg.customization.remove()), SystemMessages.SM_TYPE.Information)
        print g_config.ID + ': failed to purchase customization outfits.'


@overrideMethod(WGCtx, '__new__')
def new(base, cls, *a, **kw):
    if not g_config.data['enabled']:
        return base(cls, *a, **kw)
    return base(CustomizationContext, *a, **kw)
