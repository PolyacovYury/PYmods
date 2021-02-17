import Event
import adisp
from CurrentVehicle import g_currentVehicle
from PYmodsCore import overrideMethod
from async import await, async
from contextlib import contextmanager
from frameworks.wulf import WindowLayer
from gui import makeHtmlString
from gui.Scaleform.daapi.view.lobby.customization.context.context import CustomizationContext as WGCtx, _logger
from gui.Scaleform.daapi.view.lobby.customization.shared import (
    CustomizationTabs, CustomizationModes)
from gui.impl.dialogs import dialogs
from gui.impl.dialogs.builders import WarningDialogBuilder
from gui.impl.gen import R
from gui.shared.personality import ServicesLocator as SL
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
        self.actualMode = CSMode.BUY
        self.__startModeIds = {CSMode.BUY: None, CSMode.INSTALL: None}
        self.__currentModeIds = {CSMode.BUY: None, CSMode.INSTALL: None}
        WGCtx.__init__(self)
        self.__moddedModes = {
            modeId: ModdedMode(self, modeId, self.__origModes[modeId])
            for modeId in (CustomizationModes.CUSTOM, CustomizationModes.STYLED)}
        self.__switcherIgnored = False

    @property
    def isBuy(self):
        return self.actualMode == CSMode.BUY

    @property
    def __modeId(self):
        return self.__currentModeIds[self.actualMode]

    @__modeId.setter
    def __modeId(self, value):
        self.__currentModeIds[self.actualMode] = value

    @property
    def __startMode(self):
        return self.__startModeIds[self.actualMode]

    @__startMode.setter
    def __startMode(self, value):
        for key in self.__startModeIds:
            self.__startModeIds[key] = value
            self.__currentModeIds[key] = value

    @property
    def __modes(self):
        return self.getMode(self.actualMode)

    @__modes.setter
    def __modes(self, value):
        self.__origModes = value

    def getMode(self, actualMode, modeId=None):
        if modeId is not None:
            return self.getMode(actualMode)[modeId]
        return (self.__origModes, self.__moddedModes)[actualMode]

    @property
    def mode(self):
        return self.getMode(self.actualMode, self.modeId)

    @property
    def isItemsOnAnotherVeh(self):
        return self.isBuy and self.__isItemsOnAnotherVeh

    def init(self, season=None, modeId=None, tabId=None):
        super(CustomizationContext, self).init(season, modeId, tabId)
        self.events.onActualModeChanged = Event.Event(self.events._eventsManager)
        for mode in CSMode.BUY, CSMode.INSTALL:
            self.actualMode = mode
            self.getMode(mode, CustomizationModes.STYLED).start()
            custom = self.getMode(mode, CustomizationModes.CUSTOM)
            tabId = first(custom._tabs) if self.isBuy else CustomizationTabs.CAMOUFLAGES
            if not custom.isInited:
                custom.start(tabId)
            else:
                custom.changeTab(tabId)
            self.__currentModeIds[mode] = self.__startModeIds[mode] = (
                CustomizationModes.STYLED
                if (
                    self._service.isStyleInstalled() if self.isBuy
                    else g_config.getOutfitCache().get('style', {}).get('applied', False))
                else CustomizationModes.CUSTOM
            )
        self.actualMode = CSMode.INSTALL
        self.refreshOutfit()

    def fini(self):
        super(CustomizationContext, self).fini()
        for actualMode in CSMode.NAMES:
            modes = self.getMode(actualMode)
            for mode in modes.values():
                mode.fini()
            modes.clear()

    def changeActualMode(self, modeId, source=None):
        if self.actualMode == modeId and self.modeId != CustomizationModes.EDITABLE_STYLE:
            return
        prevMode = self.mode
        prevMode.unselectItem()
        prevMode.unselectSlot()
        prevMode.stop()
        self.actualMode = modeId
        if self.modeId == CustomizationModes.EDITABLE_STYLE:
            self.__modeId = CustomizationModes.STYLED
        newMode = self.mode
        newMode.start(self.mode.tabId, source=source)
        self.refreshOutfit()
        self.events.onBeforeModeChange()
        self.events.onActualModeChanged()
        self.events.onModeChanged(newMode.modeId, prevMode.modeId)
        self.events.onTabChanged(self.mode.tabId)

    @contextmanager
    def overrideActualMode(self, desired=CSMode.BUY):
        mode = self.actualMode
        self.actualMode = desired
        try:
            yield
        finally:
            self.actualMode = mode

    @async
    def editStyle(self, intCD, source=None):
        if self.isBuy:
            super(CustomizationContext, self).editStyle(intCD, source)
            return
        if self.getMode(CSMode.INSTALL, CustomizationModes.CUSTOM).getModifiedOutfit(self.season).isEmpty():
            self.installStyleItemsToModifiedOutfit(True)
            return
        message = makeHtmlString('html_templates:lobby/customization/dialog', 'decal', {
            'value': g_config.i18n['flashCol_propertySheet_edit_message']})
        builder = WarningDialogBuilder().setFormattedMessage(message)
        builder.setMessagesAndButtons(R.strings.dialogs.crewSkins.skinWillBeRemoved)  # the most convenient
        subview = SL.appLoader.getDefLobbyApp().containerManager.getContainer(WindowLayer.SUB_VIEW).getView()
        result = yield await(dialogs.showSimple(builder.build(parent=subview)))
        self.installStyleItemsToModifiedOutfit(result)

    def installStyleItemsToModifiedOutfit(self, proceed):
        if not proceed:
            return
        self.__moddedModes[CustomizationModes.CUSTOM].installStyleItemsToModifiedOutfit(
            self.season, self.__moddedModes[CustomizationModes.STYLED].getModifiedOutfit(self.season).copy())
        self.changeMode(CustomizationModes.CUSTOM, CustomizationTabs.CAMOUFLAGES)

    def getOrigModifiedOutfits(self):
        with self.overrideActualMode():
            return self.mode.getModifiedOutfits()

    def getPurchaseItems(self):
        with self.overrideActualMode():
            return self.mode.getPurchaseItems() if self.mode.isOutfitsModified() else []

    @adisp.async
    @process('customizationApply')
    def applyItems(self, purchaseItems, callback):
        self._itemsCache.onSyncCompleted -= self.__onCacheResync
        for mode in CSMode.BUY, CSMode.INSTALL:
            with self.overrideActualMode(mode):
                isModeChanged = self.modeId != self.__startMode
                yield self.mode.applyItems(purchaseItems, isModeChanged)
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
        for mode in CSMode.BUY, CSMode.INSTALL:
            with self.overrideActualMode(mode):
                result |= super(CustomizationContext, self).isOutfitsModified()
        return result

    def __onCacheResync(self, *_):
        if g_currentVehicle.isPresent():
            for actualMode in CSMode.NAMES:
                modes = self.getMode(actualMode)
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
        for actualMode in CSMode.NAMES:
            modes = self.getMode(actualMode)
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
        for actualMode in CSMode.NAMES:
            modes = self.getMode(actualMode)
            for mode in modes.values():
                if mode.isInited:
                    mode.onVehicleChangeStarted()


@overrideMethod(WGCtx, '__new__')
def new(base, cls, *a, **kw):
    if not g_config.data['enabled']:
        return base(cls, *a, **kw)
    return base(CustomizationContext, *a, **kw)
