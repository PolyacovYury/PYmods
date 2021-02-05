import Event
import adisp
from CurrentVehicle import g_currentVehicle
from PYmodsCore import overrideMethod, loadJson
from gui import SystemMessages
from gui.Scaleform.daapi.view.lobby.customization.context.context import CustomizationContext as WGCtx
from gui.Scaleform.daapi.view.lobby.customization.shared import (
    CustomizationTabs, CustomizationModes, getCustomPurchaseItems, getStylePurchaseItems,
    OutfitInfo, AdditionalPurchaseGroups)
from gui.Scaleform.locale.MESSENGER import MESSENGER
from gui.SystemMessages import SM_TYPE
from gui.customization.shared import (
    C11nId, __isTurretCustomizable as isTurretCustom, SEASON_TYPE_TO_NAME)
from gui.shared.gui_items import GUI_ITEM_TYPE, GUI_ITEM_TYPE_NAMES
from gui.shared.utils.decorators import process
from items.components.c11n_constants import SeasonType
from items.customizations import EmptyComponent
from vehicle_outfit.outfit import Area
from .custom_mode import CustomMode
from .editable_style_mode import EditableStyleMode
from .mod_impl import CSModImpl
from .styled_mode import StyledMode
from ..shared import CSMode
from ... import g_config
from ...processors import deleteEmpty, applyOutfitCache


def ModdedMode(ctx, modeId, baseMode):
    if modeId == CustomizationModes.CUSTOM:
        return CustomMode(ctx, baseMode)
    if modeId == CustomizationModes.STYLED:
        return StyledMode(ctx, baseMode)
    return EditableStyleMode(ctx, baseMode)


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
        for mode in self.__moddedModes.itervalues():
            mode.fini()
        self.__moddedModes.clear()

    def installStyleItemsToModifiedOutfit(self, proceed):
        if not proceed:
            return
        self.__moddedModes[CustomizationModes.CUSTOM].installStyleItemsToModifiedOutfit(
            self.season, self.__moddedModes[CustomizationModes.STYLED].modifiedStyle.getOutfit(self.season).copy())
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
                    g_config.hangarCamoCache.get(nation, {}).get(vehName, {}).clear()
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
                seasonCache = g_config.hangarCamoCache.get(nation, {}).get(vehName, {}).get(seasonName, {})
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

    # noinspection PyMethodOverriding
    def tabChanged(self, tabIndex):
        self._tabIndex = tabIndex
        mode = self._mode
        if self._tabIndex == CustomizationTabs.EFFECT:
            self._selectedAnchor = C11nId(areaId=Area.MISC, slotType=GUI_ITEM_TYPE.MODIFICATION, regionIdx=0)
        elif self._tabIndex == CustomizationTabs.STYLE:
            self._selectedAnchor = C11nId(areaId=Area.MISC, slotType=GUI_ITEM_TYPE.STYLE, regionIdx=0)
        else:
            # noinspection PyArgumentList
            self._selectedAnchor = C11nId()
        self._selectedCarouselItem = CaruselItemData()  # noqa
        self._lastTab[self.actualMode] = self._tabIndex
        if self._mode != mode:
            self.refreshOutfit()
        self.onCustomizationTabChanged(tabIndex)
        if self._mode != mode:
            self.onCustomizationModeChanged(self._mode)

    def isPossibleToInstallToAllTankAreas(self, season, slotType, currentSlotData):
        return not self.isBuy or super(CustomizationContext, self).isPossibleToInstallToAllTankAreas(
            season, slotType, currentSlotData)

    def isPossibleToInstallItemForAllSeasons(self, areaID, slotType, regionIdx, currentSlotData):
        return not self.isBuy or super(CustomizationContext, self).isPossibleToInstallItemForAllSeasons(
            areaID, slotType, regionIdx, currentSlotData)

    def removeStyle(self, intCD):
        if self.isBuy:
            if self.__modifiedStyle and self.__modifiedStyle.intCD == intCD:
                self.__modifiedStyle = None
        elif self.actualMode == CSMode.INSTALL:
            if self._modifiedModdedStyle and self._modifiedModdedStyle.intCD == intCD:
                self._modifiedModdedStyle = None
        self.refreshOutfit()
        self.onCustomizationItemsRemoved()

    def switchToCustom(self):
        self.switchToStyle()

    def switchToStyle(self):
        if self.__switcherIgnored:
            self.__switcherIgnored = False
            return
        self.__switcherIgnored = True
        self._lastTab[self.actualMode] = self._tabIndex
        self.actualMode = (self.actualMode + 1) % len(CSMode.NAMES)
        self.onActualModeChanged()  # this will cause the carousel to update, which will call onTabChanged anyway
        self.refreshOutfit()

    def cancelChanges(self):
        self._currentSettings = {'custom': {}, 'remap': {}}
        for mode in self.__origModes.values():
            mode.cancelChanges()
        for mode in self.__moddedModes.values():
            mode.cancelChanges()
        self.__currentModeIds = self.__startModeIds.copy()
        self.refreshOutfit()

    @adisp.async
    @process('customizationApply')
    def applyItems(self, purchaseItems, callback):
        if purchaseItems:
            mode = self.actualMode
            self.actualMode = CSMode.BUY
            vDesc = g_currentVehicle.item.descriptor
            nation, vehName = vDesc.name.split(':')
            vehCache = g_config.hangarCamoCache.get(nation, {}).get(vehName, {})
            isTurretCustomisable = isTurretCustom(vDesc)
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
        nation, vehName = g_currentVehicle.item.descriptor.name.split(':')
        for mode in CSMode.BUY, CSMode.INSTALL:
            self.actualMode = mode
            self.getMode(mode, CustomizationModes.STYLED).start()
            self.getMode(mode, CustomizationModes.CUSTOM).start(None if self.isBuy else CustomizationTabs.CAMOUFLAGES)
            applied = g_config.outfitCache.get(nation, {}).get(vehName, {}).get('style', {}).get('applied', False)
            if self._service.isStyleInstalled() if self.isBuy else applied:
                self.__startModeIds[mode] = CustomizationModes.STYLED
                self.__currentModeIds[mode] = CustomizationModes.STYLED
            else:
                self.__startModeIds[mode] = CustomizationModes.CUSTOM
        for season in SeasonType.COMMON_SEASONS:
            outfit = self.getMode(CSMode.INSTALL, CustomizationModes.CUSTOM).getModifiedOutfit(season)
            seasonName = SEASON_TYPE_TO_NAME[season]
            applyOutfitCache(outfit, g_config.hangarCamoCache.get(nation, {}).get(vehName, {}).get(seasonName, {}))
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
        if self.actualMode == modeId or modeId not in CSMode.NAMES:
            return
        prevMode = self.mode
        prevMode.unselectItem()
        prevMode.unselectSlot()
        prevMode.stop()
        self.actualMode = modeId
        newMode = self.mode
        newMode.start(source=source)
        self.refreshOutfit()
        self.events.onBeforeModeChange()
        self.events.onModeChanged(newMode.modeId, prevMode.modeId)
        self.events.onTabChanged(self.mode.tabId)


    '''
    def __carveUpOutfits(self):
        origMode = self.actualMode
        self.actualMode = CSMode.BUY
        # noinspection PyUnresolvedReferences
        super(CustomizationContext, self)._CustomizationContext__carveUpOutfits()
        self.actualMode = origMode
        nation, vehName = g_currentVehicle.item.descriptor.name.split(':')
        vehCache = g_config.outfitCache.get(nation, {}).get(vehName, {})
        styleCache = vehCache.get('style', {'intCD': None, 'applied': False})
        for season in SeasonType.COMMON_SEASONS:
            fromOutfit = self.service.getOutfit(season)
            outfit = self.service.getEmptyOutfit()
            if fromOutfit and not fromOutfit.modelsSet:
                self.updateOutfitByVehicleSlots(fromOutfit, outfit)
            applyOutfitCache(outfit, vehCache.get(SEASON_TYPE_TO_NAME[season], {}), False)
            outfit._isInstalled = (outfit.isInstalled() or not outfit.isEmpty()) and not styleCache['applied']
            self._originalModdedOutfits[season] = outfit.copy()
            self._modifiedModdedOutfits[season] = outfit.copy()
        origStyle = self.service.getCurrentStyle()
        moddedStyle = None if styleCache['intCD'] is None else self.service.getItemByCD(styleCache['intCD'])
        if not moddedStyle and not styleCache['applied'] and self.service.isCurrentStyleInstalled():
            self._originalModdedStyle = origStyle
            self._modifiedModdedStyle = origStyle
        elif moddedStyle:
            self._modifiedModdedStyle = moddedStyle
            self._originalModdedStyle = moddedStyle if styleCache['applied'] else None
        if self._modifiedStyle:
            self._currentOutfit = self._modifiedStyle.getOutfit(self._currentSeason)
        else:
            self._currentOutfit = self._modifiedOutfits[self._currentSeason]

    def __preserveState(self):
        self._state.update(
            modifiedStyle=self.__modifiedStyle,
            modifiedOutfits={season: outfit.copy() for season, outfit in self.__modifiedOutfits.iteritems()},
            modifiedModdedStyle=self._modifiedModdedStyle,
            modifiedModdedOutfits={season: outfit.copy() for season, outfit in self._modifiedModdedOutfits.iteritems()})

    def __restoreState(self):
        self.__modifiedStyle = self._state.get('modifiedStyle')
        self.__modifiedOutfits = self._state.get('modifiedOutfits')
        if self.__modifiedStyle:
            self.__modifiedStyle = self.service.getItemByCD(self.__modifiedStyle.intCD)
        self._modifiedModdedStyle = self._state.get('modifiedModdedStyle')
        self._modifiedModdedOutfits = self._state.get('modifiedModdedOutfits')
        if self._modifiedModdedStyle:
            self._modifiedModdedStyle = self.service.getItemByCD(self._modifiedModdedStyle.intCD)
        self._state.clear()
    '''


@overrideMethod(WGCtx, '__new__')
def new(base, cls, *a, **kw):
    print 'running new'
    if not g_config.data['enabled']:
        print 'mod disabled'
        return base(cls, *a, **kw)
    print 'mod enabled'
    return base(CustomizationContext, *a, **kw)
