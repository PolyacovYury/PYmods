import struct

from CurrentVehicle import g_currentVehicle
from PYmodsCore import overrideMethod
from gui.Scaleform.daapi.view.lobby.customization.main_view import MainView, CustomizationSlotIdVO, \
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

MainView.ctx = property(lambda self: self._MainView__ctx)


@overrideMethod(MainView, '_MainView__onTabChanged')
def new_onTabChanged(_, self, tabIndex):
    self.soundManager.playInstantSound(SOUNDS.TAB_SWITCH)
    self.service.stopHighlighter()
    if self.ctx.mode == CSMode.BUY:
        if tabIndex in C11nTabs.REGIONS:
            self.service.startHighlighter(chooseMode(TABS_ITEM_MAPPING[tabIndex], g_currentVehicle.item))
    elif self.ctx.mode == CSMode.INSTALL:
        self.service.startHighlighter(HighlightingMode.WHOLE_VEHICLE)
    elif tabIndex in CSTabs.REGIONS:
        self.service.startHighlighter(chooseMode(tabToItem(tabIndex), g_currentVehicle.item))
    self._MainView__setAnchorsInitData()
    if self._MainView__locatedOnEmbelem and self.hangarSpace.spaceInited:
        space = self.hangarSpace.space
        space.clearSelectedEmblemInfo()
        space.locateCameraToCustomizationPreview()
    self._MainView__updateAnchorPositions()
    if tabIndex == self.ctx.tabsData.STYLE:
        slotIdVO = CustomizationSlotIdVO(0, GUI_ITEM_TYPE.STYLE, 0)._asdict()
    elif tabIndex == self.ctx.tabsData.EFFECT:
        slotIdVO = CustomizationSlotIdVO(Area.MISC, GUI_ITEM_TYPE.MODIFICATION, 0)._asdict()
    else:
        slotIdVO = None
    self.as_updateSelectedRegionsS(slotIdVO)
    self.as_enableDNDS(tabIndex not in (
            self.ctx.mode == CSMode.BUY and DRAG_AND_DROP_INACTIVE_TABS or (CSTabs.STYLE, CSTabs.EFFECT)))
    self._MainView__hidePropertiesSheet()


@overrideMethod(MainView, 'onLobbyClick')
def onLobbyClick(_, self):
    if self.ctx.currentTab in (self.ctx.tabsData.EMBLEM, self.ctx.tabsData.INSCRIPTION):
        self._MainView__clearItem()


@overrideMethod(MainView, 'onAnchorsShown')
def onAnchorsShown(_, self, anchors):
    if self._vehicleCustomizationAnchorsUpdater is not None:
        self._vehicleCustomizationAnchorsUpdater.setAnchors(anchors, self.ctx.currentTab in self.ctx.tabsData.REGIONS)


@overrideMethod(MainView, '_getUpdatedAnchorsData')
def _getUpdatedAnchorsData(_, self):
    tabIndex = self.ctx.currentTab
    cType = TABS_ITEM_MAPPING[tabIndex] if self.ctx.mode == CSMode.BUY else tabToItem(tabIndex)
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


@overrideMethod(MainView, '_MainView__onRegionHighlighted')
def __onRegionHighlighted(_, self, slotType, areaId, regionIdx, selected, hovered):
    region = None
    if hovered:
        self.soundManager.playInstantSound(SOUNDS.HOVER)
        return
    if self.ctx.currentTab == self.ctx.tabsData.EFFECT:
        areaId = Area.MISC
        slotType = GUI_ITEM_TYPE.MODIFICATION
    if areaId != -1 and regionIdx != -1:
        region = CustomizationSlotIdVO(areaId, slotType, regionIdx)._asdict()
        if selected:
            self.soundManager.playInstantSound(SOUNDS.CHOOSE)
    else:
        self._MainView__hidePropertiesSheet()
    self.ctx.regionSelected(slotType, areaId, regionIdx)
    if self.ctx.isRegionSelected():
        self.as_onRegionHighlightedS(region)
        self._MainView__showPropertiesSheet(areaId, slotType, regionIdx)
    else:
        self._MainView__clearItem()


@overrideMethod(MainView, '_MainView__onCaruselItemSelected')
def __onCaruselItemSelected(_, self, index, intCD):
    tabIndex = self.ctx.currentTab
    if tabIndex in (self.ctx.tabsData.STYLE, self.ctx.tabsData.EFFECT):
        slotType, areaId, regionIdx = self.ctx.selectedRegion
        self._MainView__onRegionHighlighted(slotType, areaId, regionIdx, True, False)
    if not self._MainView__propertiesSheet.isVisible and not self.itemIsPicked:
        self.soundManager.playInstantSound(SOUNDS.PICK)
        self.itemIsPicked = True


@overrideMethod(MainView, '_MainView__setSeasonData')
def __setSeasonData(_, self, forceAnim=False):
    seasonRenderersList = []
    filledSeasonSlots = 0
    for season in SEASONS_ORDER:
        seasonName = SEASON_TYPE_TO_NAME.get(season)
        if self.ctx.mode in (CSMode.BUY, CSMode.INSTALL):
            isFilled = self.ctx.checkSlotsFillingForSeason(season) or self.ctx.modifiedStyle is not None
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


@overrideMethod(MainView, '_MainView__setAnchorsInitData')
def __setAnchorsInitData(_, self, update=False):
    def customizationSlotIdToUid(customizationSlotIdVO):
        s = struct.pack('bbh', customizationSlotIdVO.areaId, customizationSlotIdVO.slotId, customizationSlotIdVO.regionId)
        return struct.unpack('I', s)[0]

    tabIndex = self.ctx.currentTab
    anchorVOs = []
    cType = TABS_ITEM_MAPPING[tabIndex] if self.ctx.mode == CSMode.BUY else tabToItem(tabIndex)
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

    doRegions = tabIndex in self.ctx.tabsData.REGIONS
    if update:
        self.as_updateAnchorDataS(CustomizationAnchorInitVO(anchorVOs, doRegions)._asdict())
    else:
        self.as_setAnchorInitS(CustomizationAnchorInitVO(anchorVOs, doRegions)._asdict())


@overrideMethod(MainView, 'getItemTabsData')
def getItemTabsData(_, self):
    data = []
    pluses = []
    for tabIdx in self.ctx.visibleTabs:
        itemTypeID = TABS_ITEM_MAPPING[tabIdx]
        typeName = GUI_ITEM_TYPE_NAMES[itemTypeID]
        showPlus = not self.__ctx.checkSlotsFilling(itemTypeID, self.__ctx.currentSeason)
        data.append(
            {'label': i18n.makeString(ITEM_TYPES.customizationPlural(typeName)),
             'tooltip': makeTooltip(ITEM_TYPES.customizationPlural(typeName), TOOLTIPS.customizationItemTab(typeName)),
             'id': tabIdx})
        pluses.append(showPlus)

    return (data, pluses)


@overrideMethod(MainView, '_MainView__clearItem')
def __clearItem(_, self):
    self._MainView__hidePropertiesSheet()
    if self.ctx.currentTab in (self.ctx.tabsData.EMBLEM, self.ctx.tabsData.INSCRIPTION):
        self._MainView__resetCameraFocus()
    slotType, _, _ = self.ctx.selectedRegion
    self.ctx.regionSelected(slotType, -1, -1)
    self._MainView__resetUIFocus()
