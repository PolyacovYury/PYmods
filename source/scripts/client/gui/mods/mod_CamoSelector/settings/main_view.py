import struct
from CurrentVehicle import g_currentVehicle
from account_helpers import AccountSettings
from account_helpers.AccountSettings import CUSTOMIZATION_SECTION, CAROUSEL_ARROWS_HINT_SHOWN_FIELD
from adisp import process as adisp_process
from gui import DialogsInterface
from gui.Scaleform.daapi.view.dialogs.confirm_customization_item_dialog_meta import ConfirmC11nBuyMeta, ConfirmC11nSellMeta
from gui.Scaleform.daapi.view.lobby.customization.customization_cm_handlers import CustomizationOptions
from gui.Scaleform.daapi.view.lobby.customization.main_view import MainView as WGMainView, CustomizationSlotIdVO, \
    CustomizationAnchorPositionVO, CustomizationAnchorsSetVO, CustomizationSlotUpdateVO, CustomizationAnchorInitVO
from gui.Scaleform.daapi.view.lobby.customization.shared import TABS_SLOT_TYPE_MAPPING, DRAG_AND_DROP_INACTIVE_TABS as \
    DND_INACTIVE_TABS, C11nTabs, SEASONS_ORDER, SEASON_TYPE_TO_NAME
from gui.Scaleform.daapi.view.lobby.customization.sound_constants import SOUNDS
from gui.Scaleform.genConsts.CUSTOMIZATION_ALIASES import CUSTOMIZATION_ALIASES
from gui.Scaleform.locale.RES_ICONS import RES_ICONS
from gui.Scaleform.locale.VEHICLE_CUSTOMIZATION import VEHICLE_CUSTOMIZATION
from gui.customization.shared import chooseMode, getAppliedRegionsForCurrentHangarVehicle, HighlightingMode, \
    appliedToFromSlotsIds, QUANTITY_LIMITED_CUSTOMIZATION_TYPES, C11nId
from gui.shared.formatters import text_styles
from gui.shared.gui_items import GUI_ITEM_TYPE, GUI_ITEM_TYPE_NAMES
from gui.shared.gui_items.customization.outfit import Area
from gui.shared.utils.functions import makeTooltip
from helpers import i18n, int2roman
from items.components.c11n_constants import ApplyArea, SeasonType
from .shared import CSMode, tabToItem


class MainView(WGMainView):
    def __onTabChanged(self, tabIndex):
        self.soundManager.playInstantSound(SOUNDS.TAB_SWITCH)
        self.service.stopHighlighter()
        if self.__ctx.mode == CSMode.SETUP:
            self.service.startHighlighter(HighlightingMode.WHOLE_VEHICLE)
        elif tabIndex in self.__ctx.tabsData.REGIONS:
            self.service.startHighlighter(chooseMode(tabToItem(tabIndex, self.__ctx.isBuy), g_currentVehicle.item))
        self.__setAnchorsInitData()
        if self.__locatedOnEmbelem and self.__ctx.c11CameraManager is not None:
            self.__ctx.c11CameraManager.clearSelectedEmblemInfo()
            self.__ctx.c11CameraManager.locateCameraToCustomizationPreview(preserveAngles=True)
        self.__updateAnchorsData()
        if tabIndex == self.__ctx.tabsData.STYLE:
            slotIdVO = CustomizationSlotIdVO(Area.MISC, GUI_ITEM_TYPE.STYLE, 0)._asdict()
        elif tabIndex == self.__ctx.tabsData.EFFECT:
            slotIdVO = CustomizationSlotIdVO(Area.MISC, GUI_ITEM_TYPE.MODIFICATION, 0)._asdict()
        else:
            slotIdVO = None
        self.as_updateSelectedRegionsS(slotIdVO)
        self.__updateDnd()
        self.__hidePropertiesSheet()
        self.__setHeaderInitData()
        self.__setNotificationCounters()

    def onLobbyClick(self):
        if self.__ctx.currentTab in (
                self.__ctx.tabsData.EMBLEM, self.__ctx.tabsData.INSCRIPTION, self.__ctx.tabsData.PROJECTION_DECAL):
            self.__hidePropertiesSheet()
            self.__clearItem()
        if not self.__ctx.isCaruselItemSelected():
            self.as_enableDNDS(True)

    def onRemoveSelectedItem(self):
        if self.__propertiesSheet.isVisible and not self.__ctx.numberEditModeActive:
            if self.__ctx.currentTab == self.__ctx.tabsData.STYLE:
                self.__ctx.removeStyle(self.__ctx.modifiedStyle.intCD)
            else:
                self.__ctx.removeItemFromSlot(self.__ctx.currentSeason, self.__ctx.selectedSlot)

    @adisp_process
    def _itemCtxMenuSelected(self, ctxMenuID, itemIntCD):
        item = self.itemsCache.items.getItemByCD(itemIntCD)
        if ctxMenuID == CustomizationOptions.BUY:
            yield DialogsInterface.showDialog(ConfirmC11nBuyMeta(itemIntCD))
        elif ctxMenuID == CustomizationOptions.SELL:
            inventoryCount = self.__ctx.getItemInventoryCount(item)
            yield DialogsInterface.showDialog(ConfirmC11nSellMeta(itemIntCD, inventoryCount, self.__ctx.sellItem))
        elif ctxMenuID == CustomizationOptions.REMOVE_FROM_TANK:
            if item.itemType != GUI_ITEM_TYPE.STYLE:
                self.__ctx.removeItems(True, itemIntCD)
            else:
                self.__ctx.removeStyle(itemIntCD)

    def _getUpdatedAnchorsData(self):
        tabIndex = self.__ctx.currentTab
        cType = tabToItem(tabIndex, self.__ctx.isBuy)
        slotIds = []
        if cType == GUI_ITEM_TYPE.STYLE:
            slotId = CustomizationSlotIdVO(Area.MISC, GUI_ITEM_TYPE.STYLE, 0)
            slotIds.append(slotId)
        else:
            for areaId in Area.ALL:
                regionsIndexes = getAppliedRegionsForCurrentHangarVehicle(areaId, cType)
                for regionsIndex in regionsIndexes:
                    slotId = CustomizationSlotIdVO(areaId, cType, regionsIndex)
                    slotIds.append(slotId)

        anchorVOs = []
        for zIdx, slotId in enumerate(slotIds):
            anchorVOs.append(CustomizationAnchorPositionVO(zIdx, slotId._asdict())._asdict())

        return CustomizationAnchorsSetVO(anchorVOs)._asdict()

    def __onRegionHighlighted(self, slotType, areaId, regionIdx, highlightingType, highlightingResult):
        region = None
        if self.__ctx.currentTab == self.__ctx.tabsData.EFFECT:
            areaId = Area.MISC
            slotType = GUI_ITEM_TYPE.MODIFICATION
        elif self.__ctx.currentTab == self.__ctx.tabsData.STYLE:
            areaId = Area.MISC
            slotType = GUI_ITEM_TYPE.STYLE
        if areaId != -1 and regionIdx != -1:
            region = CustomizationSlotIdVO(areaId, slotType, regionIdx)._asdict()
        else:
            self.__hidePropertiesSheet()
        self.as_onRegionHighlightedS(region, highlightingType, highlightingResult)
        if highlightingType:
            if highlightingResult:
                anchorSelected = self.__ctx.isAnchorSelected(slotType=slotType, areaId=areaId, regionIdx=regionIdx)
                itemInstalled = self.__ctx.anchorSelected(slotType, areaId, regionIdx)
                slotFilled = self.__ctx.isSlotFilled(self.__ctx.selectedAnchor)
                if self.__ctx.currentTab in (C11nTabs.EFFECT, C11nTabs.STYLE):
                    applyArea = ApplyArea.ALL
                else:
                    applyArea = appliedToFromSlotsIds([self.__ctx.selectedAnchor])
                if self.__ctx.isCaruselItemSelected():
                    self.service.highlightRegions(self.__ctx.getEmptyRegions())
                    if slotFilled and anchorSelected and not itemInstalled:
                        self.service.selectRegions(applyArea)
                        self.__locateCameraOnAnchor(areaId, slotType, regionIdx)
                        self.__showPropertiesSheet(areaId, slotType, regionIdx)
                    else:
                        self.service.selectRegions(ApplyArea.NONE)
                        self.__hidePropertiesSheet()
                else:
                    if slotFilled:
                        self.__locateCameraOnAnchor(areaId, slotType, regionIdx)
                        self.__showPropertiesSheet(areaId, slotType, regionIdx)
                    else:
                        self.soundManager.playInstantSound(SOUNDS.CHOOSE)
                        self.__resetCameraFocus()
                        self.__hidePropertiesSheet()
                    self.service.selectRegions(applyArea)
                self.__ctx.onSlotSelected(areaId, slotType, regionIdx)
            else:
                self.__clearItem()
        elif highlightingResult:
            self.soundManager.playInstantSound(SOUNDS.HOVER)

    # noinspection PyUnusedLocal
    def __onCarouselItemSelected(self, index, intCD):
        tabIndex = self.__ctx.currentTab
        if tabIndex in (self.__ctx.tabsData.STYLE, self.__ctx.tabsData.EFFECT) or self.__ctx.mode == CSMode.SETUP:
            self.service.selectRegions(ApplyArea.ALL)
            areaId, slotType, regionIdx = self.__ctx.selectedAnchor
            self.onSelectAnchor(areaId, slotType, regionIdx)
        if not self.__ctx.isAnyAnchorSelected() and not self.itemIsPicked:
            self.soundManager.playInstantSound(SOUNDS.PICK)
            self.itemIsPicked = True

    def __onPropertySheetShown(self):
        self._isPropertySheetShown = True
        self.__updateDnd()
        if self.__ctx.currentTab in (self.__ctx.tabsData.INSCRIPTION, self.__ctx.tabsData.EMBLEM):
            self.__setAnchorsInitData()

    def __onPropertySheetHidden(self):
        tabIndex = self.__ctx.currentTab
        if tabIndex in self.__ctx.tabsData.REGIONS:
            self.service.resetHighlighting()
        self._isPropertySheetShown = False
        self.__updateDnd()
        if self.__ctx.currentTab in (self.__ctx.tabsData.INSCRIPTION, self.__ctx.tabsData.EMBLEM):
            self.__setAnchorsInitData()

    def __updateDnd(self):
        isDndEnable = False
        if not self._isPropertySheetShown:
            isDndEnable = self.__ctx.currentTab not in (
                DND_INACTIVE_TABS if self.__ctx.isBuy else (self.__ctx.tabsData.STYLE, self.__ctx.tabsData.EFFECT))
        self.as_enableDNDS(isDndEnable)

    def __setSeasonData(self, forceAnim=False):
        seasonRenderersList = []
        filledSeasonSlots = 0
        for season in SEASONS_ORDER:
            seasonName = SEASON_TYPE_TO_NAME.get(season)
            isFilled = self.__ctx.mode == CSMode.SETUP or (
                    all((count == filledCount for count, filledCount in self.__ctx.checkSlotsFillingForSeason(season)))
                    or self.__ctx.modifiedStyle is not None)
            filledSeasonSlots += int(isFilled)
            seasonRenderersList.append(
                {'nameText': VEHICLE_CUSTOMIZATION.getSeasonName(seasonName),
                 'nameSelectedText': VEHICLE_CUSTOMIZATION.getSeasonSelectedName(seasonName),
                 'seasonImageSrc': RES_ICONS.getSeasonImage(seasonName),
                 'seasonBGImageSrc': RES_ICONS.getSeasonBGImage(seasonName),
                 'seasonShineImageSrc': RES_ICONS.getSeasonShineImage(seasonName),
                 'isFilled': isFilled, 'forceAnim': forceAnim,
                 'tooltip': makeTooltip(body=VEHICLE_CUSTOMIZATION.getSheetSeasonName(seasonName))})

        self.as_setSeasonsBarDataS(seasonRenderersList)
        self._seasonSoundAnimantion.setFilledSeasonSlots(filledSeasonSlots, forceAnim)

    def __setNotificationCounters(self):
        currentSeason = self.__ctx.currentSeason
        newItems = g_currentVehicle.item.getNewC11nItems(g_currentVehicle.itemsCache.items)
        seasonCounters = {season: 0 for season in SEASONS_ORDER}
        if self.__ctx.mode == CSMode.BUY:
            itemTypes = GUI_ITEM_TYPE.CUSTOMIZATIONS
        else:
            itemTypes = ()
        for item in newItems:
            if item.season != SeasonType.ALL and item.itemTypeID in itemTypes and not item.season & currentSeason:
                seasonCounters[item.season] += 1

        self.as_setNotificationCountersS([seasonCounters[season] for season in SEASONS_ORDER])

    def __setAnchorsInitData(self, update=False):
        def customizationSlotIdToUid(customizationSlotIdVO):
            s = struct.pack('bbh', customizationSlotIdVO.areaId, customizationSlotIdVO.slotId, customizationSlotIdVO.regionId)
            return struct.unpack('I', s)[0]

        if not g_currentVehicle.isPresent():
            return
        tabIndex = self.__ctx.currentTab
        anchorVOs = []
        slotType = tabToItem(tabIndex, self.__ctx.isBuy)
        maxItemsReached = False
        visibleAnchors = self.__getVisibleAnchors(slotType)
        if slotType == GUI_ITEM_TYPE.STYLE:
            anchorId = CustomizationSlotIdVO(Area.MISC, GUI_ITEM_TYPE.STYLE, 0)
            uid = customizationSlotIdToUid(anchorId)
            anchorVOs.append(CustomizationSlotUpdateVO(
                anchorId._asdict(), self.__ctx.modifiedStyle.intCD if self.__ctx.modifiedStyle is not None else 0, uid, None
            )._asdict())
        else:
            potentialPlaceTooltip = None
            if slotType in QUANTITY_LIMITED_CUSTOMIZATION_TYPES:
                outfit = self.__ctx.getModifiedOutfit(self.__ctx.currentSeason)
                if self.__ctx.isC11nItemsQuantityLimitReached(outfit, slotType):
                    maxItemsReached = True
                    potentialPlaceTooltip = makeTooltip(
                        body=VEHICLE_CUSTOMIZATION.CUSTOMIZATION_TOOLTIP_POTENTIALPROJDECALPLACE_TOLTIP_TEXT)
            for areaId in Area.ALL:
                slot = self.__ctx.currentOutfit.getContainer(areaId).slotFor(slotType)
                for regionIdx, anchor in g_currentVehicle.item.getAnchors(slotType, areaId).iteritems():
                    if anchor.slotId not in visibleAnchors:
                        continue
                    anchorId = CustomizationSlotIdVO(areaId, slotType, regionIdx)
                    slotId = self.__ctx.getSlotIdByAnchorId(C11nId(areaId=areaId, slotType=slotType, regionIdx=regionIdx))
                    itemIntCD = 0
                    if slotId and slotId.slotType == GUI_ITEM_TYPE.INSCRIPTION:
                        item = slot.getItem(slotId.regionIdx)
                        if not item:
                            slot = self.__ctx.currentOutfit.getContainer(areaId).slotFor(GUI_ITEM_TYPE.PERSONAL_NUMBER)
                            item = slot.getItem(slotId.regionIdx)
                        itemIntCD = item.intCD if item is not None else 0
                    elif slotId:
                        item = slot.getItem(slotId.regionIdx)
                        itemIntCD = item.intCD if item is not None else 0
                    tooltip = None
                    if not itemIntCD:
                        tooltip = potentialPlaceTooltip
                    uid = customizationSlotIdToUid(anchorId)
                    anchorVOs.append(CustomizationSlotUpdateVO(anchorId._asdict(), itemIntCD, uid, tooltip)._asdict())

        isRegions = tabIndex in self.__ctx.tabsData.REGIONS
        if isRegions:
            typeRegions = CUSTOMIZATION_ALIASES.ANCHOR_TYPE_REGION
        elif tabIndex == C11nTabs.PROJECTION_DECAL:
            typeRegions = CUSTOMIZATION_ALIASES.ANCHOR_TYPE_PROJECTION_DECAL
        else:
            typeRegions = CUSTOMIZATION_ALIASES.ANCHOR_TYPE_DECAL
        if update and isRegions:
            self.as_updateAnchorDataS(CustomizationAnchorInitVO(anchorVOs, typeRegions, maxItemsReached)._asdict())
        else:
            self.as_setAnchorInitS(CustomizationAnchorInitVO(anchorVOs, typeRegions, maxItemsReached)._asdict())
            if self.__propertiesSheet.isVisible:
                self.__ctx.vehicleAnchorsUpdater.changeAnchorParams(self.__ctx.selectedAnchor, isDisplayed=isRegions,
                                                                    isAutoScalable=False)

    def __setHeaderInitData(self):
        vehicle = g_currentVehicle.item
        currentTab = self.__ctx.currentTab
        if currentTab == self.__ctx.tabsData.STYLE:
            if self.__ctx.modifiedStyle:
                itemsCounter = text_styles.bonusPreviewText(
                    VEHICLE_CUSTOMIZATION.CUSTOMIZATION_HEADER_COUNTER_STYLE_INSTALLED)
            else:
                itemsCounter = text_styles.stats(VEHICLE_CUSTOMIZATION.CUSTOMIZATION_HEADER_COUNTER_STYLE_NOTINSTALLED)
        else:
            itemTypeID = TABS_SLOT_TYPE_MAPPING[currentTab]
            typeName = GUI_ITEM_TYPE_NAMES[itemTypeID]
            slotsCount, filledSlotsCount = self.__ctx.checkSlotsFilling(itemTypeID, self.__ctx.currentSeason)
            textStyle = text_styles.bonusPreviewText if slotsCount == filledSlotsCount else text_styles.stats
            itemsCounter = textStyle(i18n.makeString('#vehicle_customization:customization/header/counter/' + typeName,
                                                     filled=filledSlotsCount, available=slotsCount))
        self.as_setHeaderDataS({'tankTier': str(int2roman(vehicle.level)),
                                'tankName': vehicle.shortUserName,
                                'tankInfo': itemsCounter,
                                'tankType': '{}_elite'.format(vehicle.type) if vehicle.isElite else vehicle.type,
                                'isElite': vehicle.isElite,
                                'closeBtnTooltip': VEHICLE_CUSTOMIZATION.CUSTOMIZATION_HEADERCLOSEBTN})

    def __showPropertiesSheet(self, areaId, slotType, regionIdx, forceUpdate=False):
        if self.__propertiesSheet:
            if self.__ctx.vehicleAnchorsUpdater is not None:
                self.__ctx.vehicleAnchorsUpdater.attachMenuToAnchor(self.__ctx.selectedAnchor)
                tabIndex = self.__ctx.currentTab
                self.__propertiesSheet.show(areaId, slotType, regionIdx, tabIndex not in self.__ctx.tabsData.REGIONS,
                                            tabIndex == self.__ctx.tabsData.EMBLEM, forceUpdate)
                custSett = AccountSettings.getSettings(CUSTOMIZATION_SECTION)
                if not custSett.get(CAROUSEL_ARROWS_HINT_SHOWN_FIELD, False) and not self.__ctx.numberEditModeActive:
                    self.as_showCarouselsArrowsNotificationS(VEHICLE_CUSTOMIZATION.PROPERTYSHEET_KEYBOARD_HINT)
                    custSett[CAROUSEL_ARROWS_HINT_SHOWN_FIELD] = True
                    AccountSettings.setSettings(CUSTOMIZATION_SECTION, custSett)

    def __hidePropertiesSheet(self):
        if self.__propertiesSheet:
            self.__propertiesSheet.hide()
