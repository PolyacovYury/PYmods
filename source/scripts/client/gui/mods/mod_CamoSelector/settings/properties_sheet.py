from CurrentVehicle import g_currentVehicle
from PYmodsCore import overrideMethod
from gui.Scaleform.daapi.view.lobby.customization.customization_properties_sheet import (
    CustomizationPropertiesSheet as WGPropertiesSheet,
)
from gui.Scaleform.daapi.view.lobby.customization.shared import CustomizationTabs
from gui.Scaleform.genConsts.CUSTOMIZATION_ALIASES import CUSTOMIZATION_ALIASES as CA
from gui.customization.constants import CustomizationModes
from gui.impl.backport import text
from gui.impl.gen import R
from gui.shared.gui_items import GUI_ITEM_TYPE
from items.vehicles import g_cache
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
            self._isItemAppliedToAllSeasons = False
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
        return VO


@overrideMethod(WGPropertiesSheet, '__new__')
def new(base, cls, *a, **kw):
    if not g_config.data['enabled']:
        return base(cls, *a, **kw)
    return base(CustomizationPropertiesSheet, *a, **kw)
