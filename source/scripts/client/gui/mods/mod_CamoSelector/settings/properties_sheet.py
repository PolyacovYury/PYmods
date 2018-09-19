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
    def onActionBtnClick(self, actionType, applyToAll):
        if actionType == ACTION_ALIASES.CHANGE_ALLY:
            self.__ctx.changeAlly(applyToAll)
        elif actionType == ACTION_ALIASES.CHANGE_ENEMY:
            self.__ctx.changeEnemy(applyToAll)
        elif (actionType - 8) in SEASONS_CONSTANTS.INDICES:
            self.__ctx.toggleSeason(actionType - 8)
        else:
            super(CustomizationPropertiesSheet, self).onActionBtnClick(actionType, applyToAll)

    def setCamouflageColor(self, paletteIdx):
        self.__ctx.changeCamouflageColor(self._areaID, self._regionID, paletteIdx)

    # noinspection PyUnusedLocal
    def setCamouflageScale(self, scale, scaleIndex):
        self.__ctx.changeCamouflageScale(self._areaID, self._regionID, scale)

    def __updateItemAppliedToAllFlag(self):
        if self.__ctx.mode != CSMode.SETUP:
            # noinspection PyUnresolvedReferences
            super(CustomizationPropertiesSheet, self)._CustomizationPropertiesSheet__updateItemAppliedToAllFlag()

    def __getTitleDescrTexts(self, currentElement):
        if self._slotID == GUI_ITEM_TYPE.STYLE:
            if not currentElement:
                titleText = VEHICLE_CUSTOMIZATION.PROPERTYSHEET_ELEMENTTYPE_ALL
            else:
                titleText = currentElement.userName
        elif self._slotID == GUI_ITEM_TYPE.MODIFICATION:
            titleText = VEHICLE_CUSTOMIZATION.PROPERTYSHEET_ELEMENTTYPE_ALL
        elif self._slotID == GUI_ITEM_TYPE.INSCRIPTION:
            titleText = VEHICLE_CUSTOMIZATION.PROPERTYSHEET_ELEMENTTYPE_INSCRIPTION
        elif self._slotID == GUI_ITEM_TYPE.EMBLEM:
            titleText = VEHICLE_CUSTOMIZATION.PROPERTYSHEET_ELEMENTTYPE_EMBLEM
        else:
            titleText = VEHICLE_CUSTOMIZATION.getSheetVehPartName(getCustomizationTankPartName(self._areaID, self._regionID))
        if not currentElement:
            itemTypeID = tabToItem(self.__ctx.currentTab, self.__ctx.mode)
            itemTypeName = GUI_ITEM_TYPE_NAMES[itemTypeID]
            descrText = text_styles.neutral(VEHICLE_CUSTOMIZATION.getSheetEmptyDescription(itemTypeName))
        elif self._slotID == GUI_ITEM_TYPE.STYLE:
            descrText = text_styles.main(currentElement.userType)
        elif self._slotID == GUI_ITEM_TYPE.CAMOUFLAGE:
            descrText = text_styles.main(currentElement.userName)
        else:
            descrText = text_styles.main(
                i18n.makeString(VEHICLE_CUSTOMIZATION.PROPERTYSHEET_DESCRIPTION, itemType=currentElement.userType,
                                itemName=currentElement.userName))
        return text_styles.highTitle(titleText), descrText

    def __makeRemoveRendererVO(self, separatorVisible=True):
        iconSrc = RES_ICONS.MAPS_ICONS_CUSTOMIZATION_PROPERTY_SHEET_CROSS
        if self._slotID == GUI_ITEM_TYPE.STYLE:
            titleText = ''
            iconSrc = ''
            actionBtnLabel = VEHICLE_CUSTOMIZATION.PROPERTYSHEET_ACTIONBTN_REMOVESTYLE
        else:
            itemTypeID = tabToItem(self.__ctx.currentTab, self.__ctx.mode)
            itemTypeName = GUI_ITEM_TYPE_NAMES[itemTypeID]
            titleText = VEHICLE_CUSTOMIZATION.getSheetRemoveText(itemTypeName)
            if self._slotID == GUI_ITEM_TYPE.MODIFICATION:
                actionBtnLabel = VEHICLE_CUSTOMIZATION.PROPERTYSHEET_ACTIONBTN_REMOVE_TANK
            elif self._slotID == GUI_ITEM_TYPE.EMBLEM:
                actionBtnLabel = VEHICLE_CUSTOMIZATION.PROPERTYSHEET_ACTIONBTN_REMOVE_EMBLEM
            elif self._slotID == GUI_ITEM_TYPE.INSCRIPTION:
                actionBtnLabel = VEHICLE_CUSTOMIZATION.PROPERTYSHEET_ACTIONBTN_REMOVE_INSCRIPTION
            else:
                actionBtnLabel = VEHICLE_CUSTOMIZATION.getSheetBtnRemoveText(
                    getCustomizationTankPartName(self._areaID, self._regionID))
        return {'titleText': text_styles.standard(titleText),
                'iconSrc': iconSrc,
                'actionBtnLabel': actionBtnLabel,
                'actionBtnIconSrc': RES_ICONS.MAPS_ICONS_LIBRARY_ASSET_1,
                'isAppliedToAll': False,
                'separatorVisible': separatorVisible,
                'rendererLnk': CUSTOMIZATION_ALIASES.CUSTOMIZATION_SHEET_BTN_RENDERER_UI,
                'actionType': CUSTOMIZATION_ALIASES.CUSTOMIZATION_SHEET_ACTION_REMOVE_ONE}

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
