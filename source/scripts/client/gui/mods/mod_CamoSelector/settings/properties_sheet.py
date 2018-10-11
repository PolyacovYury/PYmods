from gui.Scaleform.daapi.view.lobby.customization.customization_properties_sheet import CustomizationPropertiesSheet as CPS
from gui.Scaleform.genConsts.CUSTOMIZATION_ALIASES import CUSTOMIZATION_ALIASES
from gui.Scaleform.genConsts.SEASONS_CONSTANTS import SEASONS_CONSTANTS
from gui.Scaleform.locale.RES_ICONS import RES_ICONS
from gui.Scaleform.locale.VEHICLE_CUSTOMIZATION import VEHICLE_CUSTOMIZATION
from gui.customization.shared import getCustomizationTankPartName
from gui.shared.formatters import text_styles
from gui.shared.gui_items import GUI_ITEM_TYPE, GUI_ITEM_TYPE_NAMES
from helpers import i18n
from .shared import ACTION_ALIASES, CSMode, tabToItem
from .. import g_config
from ..constants import RandMode


class CustomizationPropertiesSheet(CPS):
    def onActionBtnClick(self, actionType, actionData):
        if actionType == ACTION_ALIASES.CHANGE_ALLY:
            self.__ctx.changeAlly(actionData)
        elif actionType == ACTION_ALIASES.CHANGE_ENEMY:
            self.__ctx.changeEnemy(actionData)
        elif (actionType - 8) in SEASONS_CONSTANTS.INDICES:
            self.__ctx.toggleSeason(actionType - 8)
        else:
            super(CustomizationPropertiesSheet, self).onActionBtnClick(actionType, actionData)

    def __applyToOtherAreas(self, installItem):
        if self.__ctx.currentTab not in (self.__ctx.tabsData.PAINT, self.__ctx.tabsData.CAMOUFLAGE):
            return
        currentSeason = self.__ctx.currentSeason
        if installItem:
            self.__ctx.installItemToAllTankAreas(currentSeason, self._slotID, self._currentSlotData)
        else:
            self.__ctx.removeItemFromAllTankAreas(currentSeason, self._slotID)
        self.__update()

    def __applyToOtherSeasons(self, installItem):
        if self.__ctx.currentTab not in (
                self.__ctx.tabsData.EFFECT, self.__ctx.tabsData.EMBLEM, self.__ctx.tabsData.INSCRIPTION,
                self.__ctx.tabsData.PROJECTION_DECAL):
            return
        if installItem:
            self.__ctx.installItemForAllSeasons(self._areaID, self._slotID, self._regionID, self._currentSlotData)
        else:
            self.__ctx.removeItemForAllSeasons(self._areaID, self._slotID, self._regionID)
        self.__update()

    def __updateItemAppliedToAllFlag(self):
        if self.__ctx.mode != CSMode.SETUP:
            # noinspection PyUnresolvedReferences
            super(CustomizationPropertiesSheet, self)._CustomizationPropertiesSheet__updateItemAppliedToAllFlag()

    def __makeRenderersVOs(self):
        if self.__ctx.mode != CSMode.SETUP:
            # noinspection PyUnresolvedReferences
            return super(CustomizationPropertiesSheet, self)._CustomizationPropertiesSheet__makeRenderersVOs()
        renderers = [self.makeModeRendererVO()]
        if self.__ctx.getRandMode() == RandMode.TEAM:
            renderers.extend(self.makeTeamRendererVOs())
        renderers.extend(self.makeSeasonRendererVOs())
        return renderers

    def makeModeRendererVO(self):
        btnBlockVO = []
        for idx in RandMode.NAMES:
            btnBlockVO.append({'paletteIcon': '', 'selected': self.__ctx.getRandMode() == idx,
                               'label': g_config.i18n['UI_flash_randMode_' + RandMode.NAMES[idx]], 'value': idx})

        return {'titleText': text_styles.standard(g_config.i18n['UI_flashCol_randMode_label']),
                'iconSrc': RES_ICONS.MAPS_ICONS_CUSTOMIZATION_PROPERTY_SHEET_SCALE,
                'isAppliedToAll': False,
                'actionType': CUSTOMIZATION_ALIASES.CUSTOMIZATION_SHEET_ACTION_SCALE_CHANGE,
                'rendererLnk': CUSTOMIZATION_ALIASES.CUSTOMIZATION_SHEET_SCALE_COLOR_RENDERER_UI,
                'btnsBlockVO': btnBlockVO,
                'btnsGroupName': CUSTOMIZATION_ALIASES.SCALE_BTNS_GROUP}

    def makeTeamRendererVOs(self):
        result = []
        for team in ('ally', 'enemy'):
            if not getattr(self.__ctx, 'useFor_' + team):
                titleText = g_config.i18n['UI_flashCol_teamMode_%s_apply_label' % team]
                actionBtnLabel = g_config.i18n['UI_flash_teamMode_%s_apply_btn' % team]
                actionBtnIconSrc = ''
            else:
                titleText = g_config.i18n['UI_flashCol_teamMode_%s_applied_label' % team]
                actionBtnLabel = g_config.i18n['UI_flash_teamMode' + (
                    ('_%s_applied_btn' % team) if getattr(self.__ctx, 'useFor_' + (
                        'enemy' if team == 'ally' else 'ally')) else '_remove_btn')]
                actionBtnIconSrc = RES_ICONS.MAPS_ICONS_LIBRARY_ASSET_1
            result.append({
                'titleText': text_styles.standard(titleText),
                'iconSrc': RES_ICONS.MAPS_ICONS_CUSTOMIZATION_PROPERTY_SHEET_TANK,
                'actionBtnLabel': actionBtnLabel,
                'actionBtnIconSrc': actionBtnIconSrc,
                'isAppliedToAll': False,
                'rendererLnk': CUSTOMIZATION_ALIASES.CUSTOMIZATION_SHEET_BTN_RENDERER_UI,
                'actionType': getattr(ACTION_ALIASES, 'CHANGE_' + team.upper())})
        return result

    def makeSeasonRendererVOs(self):
        result = []
        for idx in SEASONS_CONSTANTS.INDICES:
            season = SEASONS_CONSTANTS.SEASONS[idx]
            if idx not in self.__ctx.getSeasonIndices():
                titleText = g_config.i18n['UI_flashCol_season_%s_apply_label' % season]
                actionBtnLabel = g_config.i18n['UI_flash_season_%s_apply_btn' % season]
                actionBtnIconSrc = ''
            else:
                titleText = g_config.i18n['UI_flashCol_season_%s_applied_label' % season]
                actionBtnLabel = g_config.i18n['UI_flash_season_%s_applied_btn' % season]
                actionBtnIconSrc = RES_ICONS.MAPS_ICONS_LIBRARY_ASSET_1
            result.append({
                'titleText': text_styles.standard(titleText),
                'iconSrc': getattr(RES_ICONS, 'MAPS_ICONS_CUSTOMIZATION_PROPERTY_SHEET_%s_SEASON_ICON' % season.upper()),
                'actionBtnLabel': actionBtnLabel,
                'actionBtnIconSrc': actionBtnIconSrc,
                'isAppliedToAll': False,
                'rendererLnk': CUSTOMIZATION_ALIASES.CUSTOMIZATION_SHEET_BTN_RENDERER_UI,
                'actionType': getattr(ACTION_ALIASES, 'CHANGE_' + season.upper())})
        return result
