from CurrentVehicle import g_currentVehicle
from PYmodsCore import overrideMethod
from gui.Scaleform.daapi.view.lobby.customization.customization_properties_sheet import (
    CustomizationCamoSwatchVO, CustomizationPropertiesSheet as WGPropertiesSheet,
)
from gui.Scaleform.daapi.view.lobby.customization.shared import CustomizationTabs
from gui.Scaleform.genConsts.CUSTOMIZATION_ALIASES import CUSTOMIZATION_ALIASES, CUSTOMIZATION_ALIASES as CA
from gui.customization.constants import CustomizationModes
from gui.customization.shared import SEASON_IDX_TO_TYPE, SEASON_TYPE_TO_NAME
from gui.impl.backport import image, text
from gui.impl.gen import R
from gui.shared.gui_items import GUI_ITEM_TYPE
from items.vehicles import g_cache
from .shared import isStyleSeasoned
from .. import g_config


class CustomizationPropertiesSheet(WGPropertiesSheet):
    def __init__(self):
        WGPropertiesSheet.__init__(self)
        self._isItemAppliedToAllSeasons = False
        self._isItemAppliedToAllParts = False

    def onActionBtnClick(self, actionType, actionData):
        if not self.__ctx.isPurchase and actionType == CA.CUSTOMIZATION_SHEET_ACTION_SWITCH_PROGRESSION_LVL:
            currentProgressionLevel = self._currentItem.getMaxProgressionLevel()
            self.__displayedProgressionLevel -= 1
            if actionData == 0:
                self.__displayedProgressionLevel += 1
            elif actionData == 1:
                self.__displayedProgressionLevel -= 1
            self.__displayedProgressionLevel %= currentProgressionLevel
            self.__displayedProgressionLevel += 1
            self.__ctx.mode.changeItemProgression(self._attachedAnchor, self.__displayedProgressionLevel)
            self.as_setDataAndShowS(self.__makeVO())
            return
        WGPropertiesSheet.onActionBtnClick(self, actionType, actionData)

    @property
    def _currentSlotData(self):
        if not self.attached:
            return
        if self._attachedAnchor.slotType == GUI_ITEM_TYPE.STYLE:
            return self.__ctx.mode.getSlotDataFromSlot(self._attachedAnchor)
        # noinspection PyArgumentList
        return WGPropertiesSheet._currentSlotData.fget(self)

    def __applyToOtherAreas(self, installItem):
        installItem = self._isItemAppliedToAllParts = not self._isItemAppliedToAllParts
        # noinspection PyUnresolvedReferences
        WGPropertiesSheet._CustomizationPropertiesSheet__applyToOtherAreas(self, installItem)

    def __applyToOtherSeasons(self):
        self._isItemAppliedToAll = self._isItemAppliedToAllSeasons  # restoration handled by __update
        # noinspection PyUnresolvedReferences
        WGPropertiesSheet._CustomizationPropertiesSheet__applyToOtherSeasons(self)

    def __updateItemAppliedToAllFlag(self):
        # noinspection PyUnresolvedReferences
        WGPropertiesSheet._CustomizationPropertiesSheet__updateItemAppliedToAllFlag(self)
        if self.__ctx.mode.tabId in CustomizationTabs.MODES[CustomizationModes.CUSTOM]:
            self._isItemAppliedToAllSeasons = self.__isItemAppliedToAllSeasons()
            self._isItemAppliedToAllParts = self.__isItemAppliedToAllRegions()
        else:
            self._isItemAppliedToAllSeasons = not self.__ctx.isPurchase and self.__isItemAppliedToAllSeasons()
            self._isItemAppliedToAllParts = False

    def __makeRenderersVOs(self):
        slotType = self._attachedAnchor.slotType
        if slotType != GUI_ITEM_TYPE.INSIGNIA:
            # noinspection PyUnresolvedReferences
            return WGPropertiesSheet._CustomizationPropertiesSheet__makeRenderersVOs(self)
        itemTypeText = text(R.strings.vehicle_customization.propertySheet.actionBtn.forCurrentItem.modification())
        seasonsVO = self.__makeSetOnOtherSeasonsRendererVO()
        removeVO = self.__makeRemoveRendererVO()
        removeVO['enabled'] = bool(self._currentItem) and self._currentItem.id != g_cache.customization20(
        ).defaultInsignias[g_currentVehicle.item.descriptor.type.customizationNationID]
        if self._isItemAppliedToAllSeasons:
            seasonTooltip = R.strings.vehicle_customization.propertySheet.actionBtn.removeFromAllMapsDisabled()
            seasonsVO['enabled'] = removeVO['enabled']
        else:
            seasonTooltip = R.strings.vehicle_customization.propertySheet.actionBtn.applyToAllMapsDisabled()
        seasonsVO['disableTooltip'] = text(seasonTooltip, itemType=itemTypeText)
        removeVO['disableTooltip'] = text(
            R.strings.vehicle_customization.propertySheet.actionBtn.removeDisabled(), itemType=itemTypeText)
        return [seasonsVO, removeVO, self.__makeCloseRendererVO()]

    def __makePaintRenderersVOs(self):
        if self.__ctx.isPurchase:
            # noinspection PyUnresolvedReferences
            return WGPropertiesSheet._CustomizationPropertiesSheet__makePaintRenderersVOs(self)
        return [
            self.__makeSetOnOtherSeasonsRendererVO(), self.__makeSetOnOtherTankPartsRendererVO()
        ]

    def __makeCamouflageRenderersVOs(self):
        if self.__ctx.isPurchase:
            # noinspection PyUnresolvedReferences
            return WGPropertiesSheet._CustomizationPropertiesSheet__makeCamouflageRenderersVOs(self)
        return [
            self.__makeCamoColorRendererVO(), self.__makeScaleRendererVO(),
            self.__makeSetOnOtherSeasonsRendererVO(), self.__makeSetOnOtherTankPartsRendererVO()
        ]

    def __makeStyleRenderersVOs(self):
        # noinspection PyUnresolvedReferences
        renderers = WGPropertiesSheet._CustomizationPropertiesSheet__makeStyleRenderersVOs(self)
        if not self.__ctx.isPurchase:
            renderers[1:] = []
            if self._currentStyle:
                if isStyleSeasoned(self._currentStyle):
                    renderers.append(self.__makeChangeSeasonRendererVO())
                renderers.append(self.__makeSetOnOtherSeasonsRendererVO())
        return renderers

    def __makeSetOnOtherTankPartsRendererVO(self):
        backup = self._isItemAppliedToAll
        self._isItemAppliedToAll = self._isItemAppliedToAllParts
        # noinspection PyUnresolvedReferences
        result = WGPropertiesSheet._CustomizationPropertiesSheet__makeSetOnOtherTankPartsRendererVO(self)
        self._isItemAppliedToAll = backup
        return result

    def __makeSetOnOtherSeasonsRendererVO(self):
        backup = self._isItemAppliedToAll
        self._isItemAppliedToAll = self._isItemAppliedToAllSeasons
        # noinspection PyUnresolvedReferences
        result = WGPropertiesSheet._CustomizationPropertiesSheet__makeSetOnOtherSeasonsRendererVO(self)
        self._isItemAppliedToAll = backup
        return result

    def __makeSwitchProgressionLevelRendererVO(self):
        # noinspection PyUnresolvedReferences
        VO = WGPropertiesSheet._CustomizationPropertiesSheet__makeSwitchProgressionLevelRendererVO(self)
        if not self.__ctx.isPurchase:
            VO['enabled'] = True
            VO['actionBtnLabel'] = text(
                R.strings.vehicle_customization.propertySheet.actionBtn.switchProgression(),
                current=self.__displayedProgressionLevel, total=self._currentItem.getMaxProgressionLevel())
        return VO

    def __makeChangeSeasonRendererVO(self):
        return {
            'iconSrc': image(R.images.gui.maps.icons.customization.property_sheet.idle.icon_season()),
            'iconHoverSrc': image(R.images.gui.maps.icons.customization.property_sheet.idle.icon_season_hover()),
            'iconDisableSrc': image(R.images.gui.maps.icons.customization.property_sheet.disable.icon_season_disable()),
            'actionType': CUSTOMIZATION_ALIASES.CUSTOMIZATION_SHEET_ACTION_COLOR_CHANGE,
            'rendererLnk': CUSTOMIZATION_ALIASES.CUSTOMIZATION_SHEET_SCALE_COLOR_RENDERER_UI,
            'btnsBlockVO': [CustomizationCamoSwatchVO(
                'CamoSelector/%s16x16.png' % SEASON_TYPE_TO_NAME[season], season == self.__ctx.mode.modifiedStyleSeason
            )._asdict() for _, season in sorted(SEASON_IDX_TO_TYPE.items())],
            'disableTooltip': '',
            'enabled': True}


@overrideMethod(WGPropertiesSheet, '__new__')
def new(base, cls, *a, **kw):
    if not g_config.data['enabled']:
        return base(cls, *a, **kw)
    return base(CustomizationPropertiesSheet, *a, **kw)
