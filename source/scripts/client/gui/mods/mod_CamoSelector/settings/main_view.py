import struct
from CurrentVehicle import g_currentVehicle
from gui.Scaleform.daapi.view.lobby.customization.main_view import MainView as WGMainView, CustomizationSlotIdVO, \
    CustomizationAnchorPositionVO, CustomizationAnchorsSetVO, CustomizationSlotUpdateVO, CustomizationAnchorInitVO
from gui.Scaleform.daapi.view.lobby.customization.shared import TABS_ITEM_MAPPING, DRAG_AND_DROP_INACTIVE_TABS as \
    DND_INACTIVE_TABS, C11nTabs, SEASONS_ORDER, SEASON_TYPE_TO_NAME
from gui.Scaleform.daapi.view.lobby.customization.sound_constants import SOUNDS
from gui.Scaleform.genConsts.CUSTOMIZATION_ALIASES import CUSTOMIZATION_ALIASES
from gui.Scaleform.locale.ITEM_TYPES import ITEM_TYPES
from gui.Scaleform.locale.RES_ICONS import RES_ICONS
from gui.Scaleform.locale.TOOLTIPS import TOOLTIPS
from gui.Scaleform.locale.VEHICLE_CUSTOMIZATION import VEHICLE_CUSTOMIZATION
from gui.customization.shared import chooseMode, getAppliedRegionsForCurrentHangarVehicle, HighlightingMode, \
    appliedToFromSlotsIds, QUANTITY_LIMITED_CUSTOMIZATION_TYPES, C11nId
from gui.shared.gui_items import GUI_ITEM_TYPE, GUI_ITEM_TYPE_NAMES
from gui.shared.gui_items.customization.outfit import Area
from gui.shared.utils.functions import makeTooltip
from helpers import i18n
from items.components.c11n_constants import ApplyArea
from .shared import CSMode, CSTabs, tabToItem
from .. import g_config


class MainView(WGMainView):
    def __onTabChanged(self, tabIndex):
        self.soundManager.playInstantSound(SOUNDS.TAB_SWITCH)
        self.service.stopHighlighter()
        if self.__ctx.isBuy:
            if tabIndex in C11nTabs.REGIONS:
                self.service.startHighlighter(chooseMode(TABS_ITEM_MAPPING[tabIndex], g_currentVehicle.item))
        elif self.__ctx.mode == CSMode.SETUP:
            self.service.startHighlighter(HighlightingMode.WHOLE_VEHICLE)
        elif tabIndex in CSTabs.REGIONS:
            self.service.startHighlighter(chooseMode(tabToItem(tabIndex, self.__ctx.isBuy), g_currentVehicle.item))
        self.__setAnchorsInitData()
        if self.__locatedOnEmbelem and self.__ctx.c11CameraManager is not None:
            self.__ctx.c11CameraManager.clearSelectedEmblemInfo()
            self.__ctx.c11CameraManager.locateCameraToCustomizationPreview()
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

    def onLobbyClick(self):
        if self.__ctx.currentTab in (
                self.__ctx.tabsData.EMBLEM, self.__ctx.tabsData.INSCRIPTION, self.__ctx.tabsData.PROJECTION_DECAL):
            self.__hidePropertiesSheet()
            self.__clearItem()
        if not self.__ctx.isCaruselItemSelected():
            self.as_enableDNDS(True)

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
                        self.soundManager.playInstantSound(SOUNDS.CHOOSE)
                    else:
                        self.service.selectRegions(ApplyArea.NONE)
                        self.__hidePropertiesSheet()
                        self.soundManager.playInstantSound(SOUNDS.CHOOSE)
                else:
                    if slotFilled:
                        self.__locateCameraOnAnchor(areaId, slotType, regionIdx)
                        self.__showPropertiesSheet(areaId, slotType, regionIdx)
                    else:
                        self.__resetCameraFocus()
                        self.__hidePropertiesSheet()
                    self.service.selectRegions(applyArea)
            else:
                self.__clearItem()
        elif highlightingResult:
            self.soundManager.playInstantSound(SOUNDS.HOVER)

    # noinspection PyUnusedLocal
    def __onCaruselItemSelected(self, index, intCD):
        tabIndex = self.__ctx.currentTab
        if tabIndex in (self.__ctx.tabsData.STYLE, self.__ctx.tabsData.EFFECT):
            self.service.selectRegions(ApplyArea.ALL)
            areaId, slotType, regionIdx = self.__ctx.selectedAnchor
            self.onSelectAnchor(areaId, slotType, regionIdx)
        if self.__ctx.mode == CSMode.SETUP:
            self.onSelectAnchor(1, GUI_ITEM_TYPE.CAMOUFLAGE, 0)
        if not self.__propertiesSheet.isVisible and not self.itemIsPicked:
            self.soundManager.playInstantSound(SOUNDS.PICK)
            self.itemIsPicked = True
        if self.__ctx.isAnyAnchorSelected() and not self.__ctx.isCaruselItemSelected():
            areaId, slotType, regionIdx = self.__ctx.selectedAnchor
            self.__showPropertiesSheet(areaId, slotType, regionIdx)

    def __onPropertySheetHidden(self):
        tabIndex = self.__ctx.currentTab
        if tabIndex in self.__ctx.tabsData.REGIONS:
            self.service.resetHighlighting()
        else:
            self.__hideAnchorSwitchers()
        self._isPropertySheetShown = False
        self.__updateDnd()

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
                    self.__ctx.checkSlotsFillingForSeason(season) or self.__ctx.modifiedStyle is not None)
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

    def __setAnchorsInitData(self, update=False):
        def customizationSlotIdToUid(customizationSlotIdVO):
            s = struct.pack('bbh', customizationSlotIdVO.areaId, customizationSlotIdVO.slotId, customizationSlotIdVO.regionId)
            return struct.unpack('I', s)[0]

        tabIndex = self.__ctx.currentTab
        anchorVOs = []
        cType = tabToItem(tabIndex, self.__ctx.isBuy)
        maxItemsReached = False
        if cType == GUI_ITEM_TYPE.STYLE:
            anchorId = CustomizationSlotIdVO(Area.MISC, GUI_ITEM_TYPE.STYLE, 0)
            uid = customizationSlotIdToUid(anchorId)
            anchorVOs.append(CustomizationSlotUpdateVO(
                anchorId._asdict(), self.__ctx.modifiedStyle.intCD if self.__ctx.modifiedStyle is not None else 0, uid, None
            )._asdict())
        else:
            potentialPlaceTooltip = None
            if cType in QUANTITY_LIMITED_CUSTOMIZATION_TYPES:
                outfit = self.__ctx.getModifiedOutfit(self.__ctx.currentSeason)
                if self.__ctx.isC11nItemsQuantityLimitReached(outfit, cType):
                    maxItemsReached = True
                    potentialPlaceTooltip = makeTooltip(
                        VEHICLE_CUSTOMIZATION.CUSTOMIZATION_TOOLTIP_POTENTIALPROJDECALPLACE_TITLE,
                        VEHICLE_CUSTOMIZATION.CUSTOMIZATION_TOOLTIP_POTENTIALPROJDECALPLACE_TEXT)
            for areaId in Area.ALL:
                regionsIndexes = getAppliedRegionsForCurrentHangarVehicle(areaId, cType)
                slot = self.__ctx.currentOutfit.getContainer(areaId).slotFor(cType)
                for regionsIndex in regionsIndexes:
                    anchorId = CustomizationSlotIdVO(areaId, cType, regionsIndex)
                    slotId = self.__ctx.getSlotIdByAnchorId(C11nId(areaId=areaId, slotType=cType, regionIdx=regionsIndex))
                    itemIntCD = 0
                    if slotId is not None:
                        item = slot.getItem(slotId.regionIdx)
                        itemIntCD = item.intCD if item is not None else 0
                    tooltip = None
                    if not itemIntCD:
                        tooltip = potentialPlaceTooltip
                    uid = customizationSlotIdToUid(anchorId)
                    anchorVOs.append(CustomizationSlotUpdateVO(anchorId._asdict(), itemIntCD, uid, tooltip)._asdict())

        if tabIndex in self.__ctx.tabsData.REGIONS:
            typeRegions = CUSTOMIZATION_ALIASES.ANCHOR_TYPE_REGION
        elif tabIndex == C11nTabs.PROJECTION_DECAL:
            typeRegions = CUSTOMIZATION_ALIASES.ANCHOR_TYPE_PROJECTION_DECAL
        else:
            typeRegions = CUSTOMIZATION_ALIASES.ANCHOR_TYPE_DECAL
        if update:
            self.as_updateAnchorDataS(CustomizationAnchorInitVO(anchorVOs, typeRegions, maxItemsReached)._asdict())
        else:
            self.as_setAnchorInitS(CustomizationAnchorInitVO(anchorVOs, typeRegions, maxItemsReached)._asdict())

    def __showPropertiesSheet(self, areaId, slotType, regionIdx):
        if self.__propertiesSheet:
            if self.__ctx.vehicleAnchorsUpdater is not None:
                self.__ctx.vehicleAnchorsUpdater.attachMenuToAnchor(self.__ctx.selectedAnchor)
                if self.__ctx.currentTab in self.__ctx.tabsData.REGIONS:
                    self.__ctx.vehicleAnchorsUpdater.changeAnchorParams(self.__ctx.selectedAnchor, True, False)
            if self.__propertiesSheet.isVisible:
                self.soundManager.playInstantSound(SOUNDS.CHOOSE)
            self.__propertiesSheet.show(areaId, slotType, regionIdx)
            tabIndex = self.__ctx.currentTab
            if tabIndex not in self.__ctx.tabsData.REGIONS:
                self.__showAnchorSwitchers(tabIndex == self.__ctx.tabsData.EMBLEM)

    def __hidePropertiesSheet(self):
        if self.__propertiesSheet:
            if self.__ctx.vehicleAnchorsUpdater is not None and self.__ctx.currentTab in self.__ctx.tabsData.REGIONS:
                self.__ctx.vehicleAnchorsUpdater.changeAnchorParams(self.__ctx.selectedAnchor, True, True)
            self.__propertiesSheet.hide()

    def getItemTabsData(self):
        data = []
        pluses = []
        for tabIdx in self.__ctx.visibleTabs:
            itemTypeID = tabToItem(tabIdx, self.__ctx.isBuy)
            typeName = GUI_ITEM_TYPE_NAMES[itemTypeID]
            showPlus = not self.__checkSlotsFilling(itemTypeID, self._currentSeason)
            data.append(({'label': i18n.makeString(ITEM_TYPES.customizationPlural(typeName)),
                          'tooltip': makeTooltip(ITEM_TYPES.customizationPlural(typeName),
                                                 TOOLTIPS.customizationItemTab(typeName)),
                          'id': tabIdx} if self.__ctx.isBuy else
                         {'label': g_config.i18n['UI_flash_tabs_%s_label' % tabIdx],
                          'tooltip': makeTooltip(g_config.i18n['UI_flashCol_tabs_%s_text' % tabIdx],
                                                 g_config.i18n['UI_flashCol_tabs_%s_tooltip' % tabIdx]),
                          'id': tabIdx}))
            pluses.append(showPlus)

        return data, pluses
