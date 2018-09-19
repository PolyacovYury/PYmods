import struct
from CurrentVehicle import g_currentVehicle
from gui.Scaleform.daapi.view.lobby.customization.main_view import MainView as WGMainView, CustomizationSlotIdVO, \
    CustomizationAnchorPositionVO, CustomizationAnchorsSetVO, CustomizationSlotUpdateVO, CustomizationAnchorInitVO
from gui.Scaleform.daapi.view.lobby.customization.shared import TABS_ITEM_MAPPING, DRAG_AND_DROP_INACTIVE_TABS, \
    C11nTabs, SEASONS_ORDER, SEASON_TYPE_TO_NAME
from gui.Scaleform.daapi.view.lobby.customization.sound_constants import SOUNDS
from gui.Scaleform.locale.ITEM_TYPES import ITEM_TYPES
from gui.Scaleform.locale.RES_ICONS import RES_ICONS
from gui.Scaleform.locale.TOOLTIPS import TOOLTIPS
from gui.Scaleform.locale.VEHICLE_CUSTOMIZATION import VEHICLE_CUSTOMIZATION
from gui.customization.shared import chooseMode, getAppliedRegionsForCurrentHangarVehicle, HighlightingMode
from gui.shared.gui_items import GUI_ITEM_TYPE, GUI_ITEM_TYPE_NAMES
from gui.shared.gui_items.customization.outfit import Area
from gui.shared.utils.functions import makeTooltip
from helpers import i18n
from .shared import CSMode, CSTabs, tabToItem
from .. import g_config


class MainView(WGMainView):
    def __onTabChanged(self, tabIndex):
        self.soundManager.playInstantSound(SOUNDS.TAB_SWITCH)
        self.service.stopHighlighter()
        if self.__ctx.mode == CSMode.BUY:
            if tabIndex in C11nTabs.REGIONS:
                self.service.startHighlighter(chooseMode(TABS_ITEM_MAPPING[tabIndex], g_currentVehicle.item))
        elif self.__ctx.mode == CSMode.SETUP:
            self.service.startHighlighter(HighlightingMode.WHOLE_VEHICLE)
        elif tabIndex in CSTabs.REGIONS:
            self.service.startHighlighter(chooseMode(tabToItem(tabIndex, self.__ctx.mode), g_currentVehicle.item))
        self.__setAnchorsInitData()
        if self.__locatedOnEmbelem and self.hangarSpace.spaceInited:
            space = self.hangarSpace.space
            space.clearSelectedEmblemInfo()
            space.locateCameraToCustomizationPreview()
        self.__updateAnchorPositions()
        if tabIndex == self.__ctx.tabsData.STYLE:
            slotIdVO = CustomizationSlotIdVO(0, GUI_ITEM_TYPE.STYLE, 0)._asdict()
        elif tabIndex == self.__ctx.tabsData.EFFECT:
            slotIdVO = CustomizationSlotIdVO(Area.MISC, GUI_ITEM_TYPE.MODIFICATION, 0)._asdict()
        else:
            slotIdVO = None
        self.as_updateSelectedRegionsS(slotIdVO)
        self.as_enableDNDS(tabIndex not in (
                self.__ctx.mode == CSMode.BUY and DRAG_AND_DROP_INACTIVE_TABS or (CSTabs.STYLE, CSTabs.EFFECT)))
        self.__hidePropertiesSheet()

    def onLobbyClick(self):
        if self.__ctx.currentTab in (self.__ctx.tabsData.EMBLEM, self.__ctx.tabsData.INSCRIPTION):
            self.__clearItem()

    def onAnchorsShown(self, anchors):
        if self._vehicleCustomizationAnchorsUpdater is not None:
            self._vehicleCustomizationAnchorsUpdater.setAnchors(anchors, self.__ctx.currentTab in self.__ctx.tabsData.REGIONS)

    def _getUpdatedAnchorsData(self):
        tabIndex = self.__ctx.currentTab
        cType = tabToItem(tabIndex, self.__ctx.mode)
        slotIds = []
        if cType == GUI_ITEM_TYPE.STYLE:
            slotId = CustomizationSlotIdVO(0, GUI_ITEM_TYPE.STYLE, 0)
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

    def __onRegionHighlighted(self, slotType, areaId, regionIdx, selected, hovered):
        region = None
        if hovered:
            self.soundManager.playInstantSound(SOUNDS.HOVER)
            return
        if self.__ctx.currentTab == self.__ctx.tabsData.EFFECT:
            areaId = Area.MISC
            slotType = GUI_ITEM_TYPE.MODIFICATION
        if areaId != -1 and regionIdx != -1:
            region = CustomizationSlotIdVO(areaId, slotType, regionIdx)._asdict()
            if selected:
                self.soundManager.playInstantSound(SOUNDS.CHOOSE)
        else:
            self.__hidePropertiesSheet()
        self.__ctx.regionSelected(slotType, areaId, regionIdx)
        if self.__ctx.isRegionSelected():
            self.as_onRegionHighlightedS(region)
            slotType, areaId, regionIdx = self.__ctx.selectedRegion
            self.__showPropertiesSheet(areaId, slotType, regionIdx)
        else:
            self.__clearItem()

    # noinspection PyUnusedLocal
    def __onCaruselItemSelected(self, index, intCD):
        tabIndex = self.__ctx.currentTab
        if tabIndex in (self.__ctx.tabsData.STYLE, self.__ctx.tabsData.EFFECT):
            slotType, areaId, regionIdx = self.__ctx.selectedRegion
            self.__onRegionHighlighted(slotType, areaId, regionIdx, True, False)
        if self.__ctx.mode == CSMode.SETUP:
            self.__onRegionHighlighted(GUI_ITEM_TYPE.CAMOUFLAGE, 1, 0, True, False)
        elif not self.__propertiesSheet.isVisible and not self.itemIsPicked:
            self.soundManager.playInstantSound(SOUNDS.PICK)
            self.itemIsPicked = True

    def __setSeasonData(self, forceAnim=False):
        seasonRenderersList = []
        filledSeasonSlots = 0
        for season in SEASONS_ORDER:
            seasonName = SEASON_TYPE_TO_NAME.get(season)
            if self.__ctx.mode in (CSMode.BUY, CSMode.INSTALL):
                isFilled = self.__ctx.checkSlotsFillingForSeason(season) or self.__ctx.modifiedStyle is not None
            else:
                isFilled = True
            filledSeasonSlots += int(isFilled)
            seasonRenderersList.append(
                {'nameText': VEHICLE_CUSTOMIZATION.getSeasonName(seasonName),
                 'nameSelectedText': VEHICLE_CUSTOMIZATION.getSeasonSelectedName(seasonName),
                 'seasonImageSrc': RES_ICONS.getSeasonImage(seasonName),
                 'seasonBGImageSrc': RES_ICONS.getSeasonBGImage(seasonName),
                 'isFilled': isFilled, 'forceAnim': forceAnim})

        self.as_setSeasonsBarDataS(seasonRenderersList)
        self._seasonSoundAnimantion.setFilledSeasonSlots(filledSeasonSlots, forceAnim)

    def __setAnchorsInitData(self, update=False):
        def customizationSlotIdToUid(customizationSlotIdVO):
            s = struct.pack('bbh', customizationSlotIdVO.areaId, customizationSlotIdVO.slotId, customizationSlotIdVO.regionId)
            return struct.unpack('I', s)[0]

        tabIndex = self.__ctx.currentTab
        anchorVOs = []
        cType = tabToItem(tabIndex, self.__ctx.mode)
        if cType == GUI_ITEM_TYPE.STYLE:
            slotId = CustomizationSlotIdVO(0, cType, 0)
            uid = customizationSlotIdToUid(slotId)
            anchorVOs.append(CustomizationSlotUpdateVO(slotId._asdict(), -1, uid)._asdict())
        else:
            for areaId in Area.ALL:
                regionsIndexes = getAppliedRegionsForCurrentHangarVehicle(areaId, cType)
                slot = self.__ctx.currentOutfit.getContainer(areaId).slotFor(cType)
                for regionsIndex in regionsIndexes:
                    slotId = CustomizationSlotIdVO(areaId, cType, regionsIndex)
                    item = slot.getItem(regionsIndex)
                    itemIntCD = item.intCD if item is not None else 0
                    uid = customizationSlotIdToUid(slotId)
                    anchorVOs.append(CustomizationSlotUpdateVO(slotId._asdict(), itemIntCD, uid)._asdict())

        doRegions = tabIndex in self.__ctx.tabsData.REGIONS
        if update:
            self.as_updateAnchorDataS(CustomizationAnchorInitVO(anchorVOs, doRegions)._asdict())
        else:
            self.as_setAnchorInitS(CustomizationAnchorInitVO(anchorVOs, doRegions)._asdict())

    def getItemTabsData(self):
        data = []
        pluses = []
        for tabIdx in self.__ctx.visibleTabs:
            itemTypeID = tabToItem(tabIdx, self.__ctx.mode)
            typeName = GUI_ITEM_TYPE_NAMES[itemTypeID]
            showPlus = not self.__ctx.checkSlotsFilling(itemTypeID, self.__ctx.currentSeason)
            data.append(({'label': i18n.makeString(ITEM_TYPES.customizationPlural(typeName)),
                          'tooltip': makeTooltip(ITEM_TYPES.customizationPlural(typeName),
                                                 TOOLTIPS.customizationItemTab(typeName)),
                          'id': tabIdx} if self.__ctx.mode == CSMode.BUY else
                         {'label': g_config.i18n['UI_flash_tabs_%s_label' % tabIdx],
                          'tooltip': makeTooltip(g_config.i18n['UI_flashCol_tabs_%s_text' % tabIdx],
                                                 g_config.i18n['UI_flashCol_tabs_%s_tooltip' % tabIdx]),
                          'id': tabIdx}))
            pluses.append(showPlus)

        return data, pluses

    def __clearItem(self):
        self.__hidePropertiesSheet()
        if self.__ctx.currentTab in (self.__ctx.tabsData.EMBLEM, self.__ctx.tabsData.INSCRIPTION):
            self.__resetCameraFocus()
        slotType, _, _ = self.__ctx.selectedRegion
        self.__ctx.regionSelected(slotType, -1, -1)
        self.__resetUIFocus()
