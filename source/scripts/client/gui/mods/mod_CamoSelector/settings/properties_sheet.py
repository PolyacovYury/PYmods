from PYmodsCore import overrideMethod
from gui.Scaleform.daapi.view.lobby.customization import CAMOUFLAGES_KIND_TEXTS
from gui.Scaleform.daapi.view.lobby.customization.customization_properties_sheet import CustomizationPropertiesSheet
from gui.Scaleform.genConsts.CUSTOMIZATION_ALIASES import CUSTOMIZATION_ALIASES
from gui.Scaleform.genConsts.SEASONS_CONSTANTS import SEASONS_CONSTANTS
from gui.Scaleform.locale.RES_ICONS import RES_ICONS
from gui.shared.formatters import text_styles
from .shared import ACTION_ALIASES, CSMode
from .. import g_config
from ..constants import RandMode

CustomizationPropertiesSheet.ctx = property(lambda self: self._CustomizationPropertiesSheet__ctx)


@overrideMethod(CustomizationPropertiesSheet, 'onActionBtnClick')
def onActionBtnClick(base, self, actionType, applyToAll):
    if actionType == ACTION_ALIASES.CHANGE_ALLY:
        self.ctx.changeAlly(applyToAll)
    elif actionType == ACTION_ALIASES.CHANGE_ENEMY:
        self.ctx.changeEnemy(applyToAll)
    else:
        base(self, actionType, applyToAll)


@overrideMethod(CustomizationPropertiesSheet, 'setCamouflageColor')
def setCamouflageColor(self, paletteIdx):
    self.ctx.changeCamouflageColor(self._areaID, self._regionID, paletteIdx)


@overrideMethod(CustomizationPropertiesSheet, 'setCamouflageScale')
def setCamouflageScale(self, scale, scaleIndex):
    self.ctx.changeCamouflageScale(self._areaID, self._regionID, scale, scaleIndex)


@overrideMethod(CustomizationPropertiesSheet, '_CustomizationPropertiesSheet__makeRenderersVOs')
def __makeRenderersVOs(base, self):
    if self.ctx.mode != CSMode.SETUP:
        return base(self)
    renderers = [makeModeRendererVO(self)]
    if self.ctx.getRandMode() == RandMode.TEAM:
        renderers.extend((makeAllyRendererVO(self), makeEnemyRendererVO(self)))
    renderers.append(makeSeasonRendererVO(self))
    return renderers


def makeModeRendererVO(self):
    btnBlockVO = []
    for idx in RandMode.NAMES:
        btnBlockVO.append({'paletteIcon': '', 'selected': self.ctx.getRandMode() == idx,
                           'label': g_config.i18n['UI_flash_randMode_' + RandMode.NAMES[idx]], 'value': idx})

    return {'titleText': text_styles.standard(g_config.i18n['UI_flashCol_randMode_label']),
            'iconSrc': RES_ICONS.MAPS_ICONS_CUSTOMIZATION_PROPERTY_SHEET_SCALE,
            'isAppliedToAll': False,
            'actionType': CUSTOMIZATION_ALIASES.CUSTOMIZATION_SHEET_ACTION_SCALE_CHANGE,
            'rendererLnk': CUSTOMIZATION_ALIASES.CUSTOMIZATION_SHEET_SCALE_COLOR_RENDERER_UI,
            'btnsBlockVO': btnBlockVO,
            'btnsGroupName': CUSTOMIZATION_ALIASES.SCALE_BTNS_GROUP}


def makeAllyRendererVO(self):
    if not self.ctx.useForAlly:
        titleText = g_config.i18n['UI_flashCol_teamMode_ally_apply_label']
        actionBtnLabel = g_config.i18n['UI_flashCol_teamMode_ally_apply_btn']
        actionBtnIconSrc = ''
    else:
        titleText = g_config.i18n['UI_flashCol_teamMode_ally_applied_label']
        actionBtnLabel = g_config.i18n[
            'UI_flashCol_teamMode' + ('_ally_applied_btn' if self.ctx.useForEnemy else '_remove_btn')]
        actionBtnIconSrc = RES_ICONS.MAPS_ICONS_LIBRARY_ASSET_1
    return {'titleText': text_styles.standard(titleText),
            'iconSrc': RES_ICONS.MAPS_ICONS_CUSTOMIZATION_PROPERTY_SHEET_TANK,
            'actionBtnLabel': actionBtnLabel,
            'actionBtnIconSrc': actionBtnIconSrc,
            'isAppliedToAll': False,
            'rendererLnk': CUSTOMIZATION_ALIASES.CUSTOMIZATION_SHEET_BTN_RENDERER_UI,
            'actionType': ACTION_ALIASES.CHANGE_ALLY}


def makeEnemyRendererVO(self):
    if not self.ctx.useForEnemy:
        titleText = g_config.i18n['UI_flashCol_teamMode_enemy_apply_label']
        actionBtnLabel = g_config.i18n['UI_flashCol_teamMode_enemy_apply_btn']
        actionBtnIconSrc = ''
    else:
        titleText = g_config.i18n['UI_flashCol_teamMode_enemy_applied_label']
        actionBtnLabel = g_config.i18n[
            'UI_flashCol_teamMode' + ('_enemy_applied_btn' if self.ctx.useForAlly else '_remove_btn')]
        actionBtnIconSrc = RES_ICONS.MAPS_ICONS_LIBRARY_ASSET_1
    return {'titleText': text_styles.standard(titleText),
            'iconSrc': RES_ICONS.MAPS_ICONS_CUSTOMIZATION_PROPERTY_SHEET_TANK,
            'actionBtnLabel': actionBtnLabel,
            'actionBtnIconSrc': actionBtnIconSrc,
            'isAppliedToAll': False,
            'rendererLnk': CUSTOMIZATION_ALIASES.CUSTOMIZATION_SHEET_BTN_RENDERER_UI,
            'actionType': ACTION_ALIASES.CHANGE_ENEMY}


def makeSeasonRendererVO(self):
    btnBlockVO = []
    for idx in SEASONS_CONSTANTS.INDICES:
        btnBlockVO.append({'paletteIcon': '', 'selected': idx in self.ctx.getSeasonIndices(),
                           'label': CAMOUFLAGES_KIND_TEXTS[idx], 'value': idx})

    return {'titleText': text_styles.standard(g_config.i18n['UI_flashCol_season_label']),
            'iconSrc': RES_ICONS.MAPS_ICONS_CUSTOMIZATION_PROPERTY_SHEET_COLORS,
            'isAppliedToAll': False,
            'actionType': CUSTOMIZATION_ALIASES.CUSTOMIZATION_SHEET_ACTION_COLOR_CHANGE,
            'rendererLnk': CUSTOMIZATION_ALIASES.CUSTOMIZATION_SHEET_SCALE_COLOR_RENDERER_UI,
            'btnsBlockVO': btnBlockVO,
            'btnsGroupName': CUSTOMIZATION_ALIASES.SCALE_BTNS_GROUP}
