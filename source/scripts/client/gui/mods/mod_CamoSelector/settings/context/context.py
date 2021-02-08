import Event
import adisp
from CurrentVehicle import g_currentVehicle
from PYmodsCore import overrideMethod, loadJson
from gui import SystemMessages, makeHtmlString, DialogsInterface
from gui.Scaleform.daapi.view.dialogs import PMConfirmationDialogMeta
from gui.Scaleform.daapi.view.lobby.customization.context.context import CustomizationContext as WGCtx
from gui.Scaleform.daapi.view.lobby.customization.customization_properties_sheet import _APPLY_TO_OTHER_SEASONS_DIALOG
from gui.Scaleform.daapi.view.lobby.customization.shared import (
    CustomizationTabs, CustomizationModes, getCustomPurchaseItems, getStylePurchaseItems,
    OutfitInfo, AdditionalPurchaseGroups)
from gui.Scaleform.locale.MESSENGER import MESSENGER
from gui.Scaleform.locale.RES_ICONS import RES_ICONS
from gui.SystemMessages import SM_TYPE
from gui.customization.shared import __isTurretCustomizable as isTurretCustom, SEASON_TYPE_TO_NAME
from gui.shared.gui_items import GUI_ITEM_TYPE, GUI_ITEM_TYPE_NAMES
from gui.shared.utils.decorators import process
from items.customizations import EmptyComponent
from vehicle_outfit.outfit import Area
from .custom_mode import CustomMode
from .mod_impl import CSModImpl
from .styled_mode import StyledMode
from ..shared import CSMode
from ... import g_config
from ...processors import deleteEmpty


def ModdedMode(ctx, modeId, baseMode):
    if modeId == CustomizationModes.CUSTOM:
        return CustomMode(ctx, baseMode)
    if modeId == CustomizationModes.STYLED:
        return StyledMode(ctx, baseMode)
    return None


class CustomizationContext(WGCtx, CSModImpl):
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

    def __init__(self):
        CSModImpl.__init__(self)
        self.actualMode = CSMode.INSTALL
        self.__startModeIds = {CSMode.BUY: None, CSMode.INSTALL: None}
        self.__currentModeIds = {CSMode.BUY: None, CSMode.INSTALL: None}
        WGCtx.__init__(self)
        self.__moddedModes = {modeId: ModdedMode(self, modeId, self.__origModes[modeId]) for modeId in self.__origModes}
        self.__switcherIgnored = False

    def fini(self):
        super(CustomizationContext, self).fini()
        for actualMode in CSMode.NAMES:
            modes = self.getMode(actualMode)
            for mode in modes.values():
                mode.fini()
            modes.clear()

    @property
    def isItemsOnAnotherVeh(self):
        return self.isBuy and self.__isItemsOnAnotherVeh

    def editStyle(self, intCD, source=None):
        if self.isBuy:
            return super(CustomizationContext, self).editStyle(intCD, source)
        if not (self.getMode(CSMode.INSTALL, CustomizationModes.CUSTOM).getModdedPurchaseItems()
                or g_config.getOutfitCache().get(SEASON_TYPE_TO_NAME[self.season])):
            self.installStyleItemsToModifiedOutfit(True)
            return
        message = makeHtmlString('html_templates:lobby/customization/dialog', 'decal', {
            'value': g_config.i18n['flashCol_propertySheet_edit_message']})
        DialogsInterface.showDialog(
            PMConfirmationDialogMeta(_APPLY_TO_OTHER_SEASONS_DIALOG, messageCtx={
                'message': message, 'icon': RES_ICONS.MAPS_ICONS_LIBRARY_ICON_ALERT_90X84}),
            self.installStyleItemsToModifiedOutfit)

    def installStyleItemsToModifiedOutfit(self, proceed):
        if not proceed:
            return
        self.__moddedModes[CustomizationModes.CUSTOM].installStyleItemsToModifiedOutfit(
            self.season, self.__moddedModes[CustomizationModes.STYLED].getModifiedOutfit(self.season).copy())
        self.changeMode(CustomizationModes.CUSTOM, CustomizationTabs.CAMOUFLAGES)

    def getModdedModifiedCustomOutfits(self):
        return self.__moddedModes[CustomizationModes.CUSTOM].getModifiedOutfits()

    def getModdedModifiedStyle(self):
        return self.__moddedModes[CustomizationModes.STYLED].getModifiedStyle()

    def getModdedPurchaseItems(self):
        if self.__currentModeIds[CSMode.INSTALL] != CustomizationModes.STYLED:
            return getCustomPurchaseItems(self.season, self.getModdedModifiedCustomOutfits())
        return getStylePurchaseItems(self.getModdedModifiedStyle(), OutfitInfo(self._originalModdedStyle, self._modifiedModdedStyle))

    def applyModdedStuff(self):
        self.applySettings()
        self.applyModdedItems()

    def applyModdedItems(self):
        vDesc = g_currentVehicle.item.descriptor
        nation, vehName = vDesc.name.split(':')
        isTurretCustomisable = isTurretCustom(vDesc)
        vehCache = g_config.outfitCache.setdefault(nation, {}).setdefault(vehName, {})
        anything = False
        for p in (x for x in self.getModdedPurchaseItems() if x.selected):
            anything = True
            if p.group == AdditionalPurchaseGroups.STYLES_GROUP_ID:
                vehCache.setdefault('style', {}).update(intCD=p.item.intCD if not p.isDismantling else None, applied=True)
                if p.item is not None and not p.isDismantling:
                    g_config.getHangarCache().clear()
                break  # there will only ever be one, but just to make sure...
            else:
                vehCache.get('style', {}).update(applied=False)
            typeName = GUI_ITEM_TYPE_NAMES[p.slot]
            seasonName = SEASON_TYPE_TO_NAME[p.group]
            area = Area.getName(p.areaID) if p.areaID != Area.MISC else 'misc'
            conf = vehCache.setdefault(seasonName, {}).setdefault(typeName, {}).setdefault(area, {})
            origComponent = None
            origOutfit = self.getMode(CSMode.INSTALL, CustomizationModes.CUSTOM).getOriginalOutfit(p.group)
            if origOutfit:
                origComponent = origOutfit.getContainer(p.areaID).slotFor(p.slot).getComponent(p.regionID)
            reg = str(p.regionID)
            if p.slot == GUI_ITEM_TYPE.CAMOUFLAGE:
                seasonCache = g_config.getHangarCache().get(seasonName, {})
                seasonCache.get(typeName, {}).get(area, {}).pop(reg, None)
                deleteEmpty(seasonCache, isTurretCustomisable)
            if not origComponent if p.isDismantling else p.component.weak_eq(origComponent):
                conf.pop(reg, None)
            else:
                conf[reg] = (({f: getattr(p.component, f) for f, fd in p.component.fields.items() if not fd.weakEqualIgnored}
                              if not isinstance(p.component, EmptyComponent) else {'id': p.item.id})
                             if not p.isDismantling else {'id': None})
        if not anything and self.modeId != self.__startMode:
            vehCache.get('style', {}).update(applied=False)  # if an "empty" style is applied - 'anything' is already true
            anything = True
        if vehCache.get('style', {}) == {'intCD': None, 'applied': False}:
            vehCache.pop('style', None)
        if anything:
            SystemMessages.pushI18nMessage(
                MESSENGER.SERVICECHANNELMESSAGES_SYSMSG_CONVERTER_CUSTOMIZATIONS, type=SM_TYPE.Information)
        deleteEmpty(g_config.outfitCache, isTurretCustomisable)
        loadJson(g_config.ID, 'outfitCache', g_config.outfitCache, g_config.configPath, True)

    def cancelChanges(self):
        self._currentSettings = {'custom': {}, 'remap': {}}
        for mode in self.__origModes.values() + self.__moddedModes.values():
            if mode.isInited:
                mode.cancelChanges()
        prevModeId = self.modeId
        self.__currentModeIds = self.__startModeIds.copy()
        self.events.onModeChanged(self.modeId, prevModeId)
        self.events.onTabChanged(self.mode.tabId)
        self.refreshOutfit()

    @adisp.async
    @process('customizationApply')
    def applyItems(self, purchaseItems, callback):
        if purchaseItems:
            mode = self.actualMode
            self.actualMode = CSMode.BUY
            vehCache = g_config.getHangarCache()
            isTurretCustomisable = isTurretCustom(g_currentVehicle.item.descriptor)
            for p in (p for p in purchaseItems if p.selected):
                if p.group == AdditionalPurchaseGroups.STYLES_GROUP_ID:
                    if p.item is not None and not p.isDismantling:
                        vehCache.clear()
                elif p.slot == GUI_ITEM_TYPE.CAMOUFLAGE:
                    sCache = vehCache.get(SEASON_TYPE_TO_NAME[p.group], {})
                    sCache.get(GUI_ITEM_TYPE_NAMES[p.slot], {}).get(Area.getName(p.areaID), {}).pop(str(p.regionID), None)
                    deleteEmpty(sCache, isTurretCustomisable)
            self._itemsCache.onSyncCompleted -= self.__onCacheResync
            isModeChanged = self.modeId != self.__startMode
            yield self.mode.applyItems(purchaseItems, isModeChanged)
            self.actualMode = mode
        else:
            self.events.onItemsBought([], [], [])
        mode = self.actualMode
        self.actualMode = CSMode.INSTALL
        self.applyModdedStuff()
        self.actualMode = mode
        self.__onCacheResync()
        self._itemsCache.onSyncCompleted += self.__onCacheResync
        callback(None)

    def init(self, season=None, modeId=None, tabId=None):
        super(CustomizationContext, self).init(season, modeId, tabId)
        self.events.onActualModeChanged = Event.Event(self.events._eventsManager)
        origMode = self.actualMode
        for mode in CSMode.BUY, CSMode.INSTALL:
            self.actualMode = mode
            self.getMode(mode, CustomizationModes.STYLED).start()
            custom = self.getMode(mode, CustomizationModes.CUSTOM)
            tabId = None if self.isBuy else CustomizationTabs.CAMOUFLAGES
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
        self.actualMode = origMode
        self.refreshOutfit()
        # from functools import partial
        # import BigWorld
        # BigWorld.callback(0, partial(self.onCustomizationModeChanged, self._mode))  # because bottom_panel updates too early

    def isOutfitsModified(self):
        self._cleanSettings()
        if any(self._currentSettings.itervalues()):
            return True
        result = False
        origActualMode = self.actualMode
        for actualMode in CSMode.BUY, CSMode.INSTALL:
            self.actualMode = actualMode
            result |= super(CustomizationContext, self).isOutfitsModified()
        self.actualMode = origActualMode
        return result

    def changeActualMode(self, modeId, source=None):
        if self.actualMode == modeId and self.modeId != CustomizationModes.EDITABLE_STYLE:
            return
        prevMode = self.mode
        prevMode.unselectItem()
        prevMode.unselectSlot()
        prevMode.stop()
        self.actualMode = modeId
        if not self.isBuy and self.modeId == CustomizationModes.EDITABLE_STYLE:
            self.__modeId = CustomizationModes.STYLED
        newMode = self.mode
        newMode.start(source=source)
        self.refreshOutfit()
        self.events.onBeforeModeChange()
        self.events.onActualModeChanged()
        self.events.onModeChanged(newMode.modeId, prevMode.modeId)
        self.events.onTabChanged(self.mode.tabId)


@overrideMethod(WGCtx, '__new__')
def new(base, cls, *a, **kw):
    if not g_config.data['enabled']:
        return base(cls, *a, **kw)
    return base(CustomizationContext, *a, **kw)
