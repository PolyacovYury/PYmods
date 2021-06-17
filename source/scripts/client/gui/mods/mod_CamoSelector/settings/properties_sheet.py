from PYmodsCore import overrideMethod
from gui import makeHtmlString
from gui.Scaleform.daapi.view.lobby.customization.customization_properties_sheet import (
    CustomizationPropertiesSheet as WGPropertiesSheet)
from gui.Scaleform.daapi.view.lobby.customization.shared import CustomizationTabs
from gui.Scaleform.genConsts.CUSTOMIZATION_ALIASES import CUSTOMIZATION_ALIASES as CA
from gui.customization.constants import CustomizationModes as C11nModes, CustomizationModes
from gui.impl import backport
from gui.impl.gen import R
from .shared import CSMode
from .. import g_config


class CustomizationPropertiesSheet(WGPropertiesSheet):
    def __init__(self):
        WGPropertiesSheet.__init__(self)
        self._isItemAppliedToAllSeasons = False
        self._isItemAppliedToAllParts = False

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
            renderers[1:] = [self.__makeStyleEditRendererVO()]
        return renderers

    def __makeSetOnOtherTankPartsRendererVO(self):
        backup = self._isItemAppliedToAll
        self._isItemAppliedToAll = self._isItemAppliedToAllParts
        # noinspection PyUnresolvedReferences
        result = WGPropertiesSheet._CustomizationPropertiesSheet__makeSetOnOtherTankPartsRendererVO(self)
        self._isItemAppliedToAll = backup
        return result

    def __makeStyleEditRendererVO(self):
        enabled = not bool(self._currentStyle.modelsSet)
        return {
            'iconSrc': backport.image(R.images.gui.maps.icons.customization.property_sheet.idle.edit_style()),
            'iconHoverSrc': backport.image(R.images.gui.maps.icons.customization.property_sheet.idle.edit_style_hover()),
            'iconDisableSrc': backport.image(
                R.images.gui.maps.icons.customization.property_sheet.disable.edit_style_disable()),
            'actionBtnLabel': backport.text(R.strings.vehicle_customization.propertySheet.actionBtn.edit.style()),
            'actionType': CA.CUSTOMIZATION_SHEET_ACTION_EDIT_STYLE,
            'rendererLnk': CA.CUSTOMIZATION_SHEET_BTN_RENDERER_UI,
            'animatedTransition': True,
            'disableTooltip': g_config.i18n['flashCol_propertySheet_edit_disabled'],
            'notifyText': makeHtmlString('html_templates:lobby/customization/notify', 'decal', {
                'value': g_config.i18n['flashCol_propertySheet_edit_notify']}),
            'needNotify': enabled and (
                not self.__ctx.getMode(CSMode.INSTALL, C11nModes.CUSTOM).getModifiedOutfit(self.__ctx.season).isEmpty()),
            'enabled': enabled}

    def __makeSetOnOtherSeasonsRendererVO(self):
        backup = self._isItemAppliedToAll
        self._isItemAppliedToAll = self._isItemAppliedToAllSeasons
        # noinspection PyUnresolvedReferences
        result = WGPropertiesSheet._CustomizationPropertiesSheet__makeSetOnOtherSeasonsRendererVO(self)
        self._isItemAppliedToAll = backup
        return result


@overrideMethod(WGPropertiesSheet, '__new__')
def new(base, cls, *a, **kw):
    if not g_config.data['enabled']:
        return base(cls, *a, **kw)
    return base(CustomizationPropertiesSheet, *a, **kw)
