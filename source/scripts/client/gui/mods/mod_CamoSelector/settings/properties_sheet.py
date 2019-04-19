from CurrentVehicle import g_currentVehicle
from PYmodsCore import overrideMethod
from gui import makeHtmlString, DialogsInterface
from gui.Scaleform.daapi.view.dialogs import PMConfirmationDialogMeta
from gui.Scaleform.daapi.view.lobby.customization.customization_properties_sheet import \
    CustomizationPropertiesSheet as WGPropertiesSheet, _APPLY_TO_OTHER_SEASONS_DIALOG
from gui.Scaleform.daapi.view.lobby.customization.shared import getCustomPurchaseItems, SEASONS_ORDER, C11nTabs
from gui.Scaleform.genConsts.CUSTOMIZATION_ALIASES import CUSTOMIZATION_ALIASES as CA
from gui.Scaleform.locale.RES_ICONS import RES_ICONS
from gui.shared.gui_items import GUI_ITEM_TYPE
from .. import g_config


class CustomizationPropertiesSheet(WGPropertiesSheet):
    def onActionBtnClick(self, actionType, actionData):
        if not self.__ctx.isBuy and self._slotID == GUI_ITEM_TYPE.STYLE and actionType == CA.CUSTOMIZATION_SHEET_ACTION_EDIT:
            nation, vehicle = g_currentVehicle.item.descriptor.name.split(':')
            if not (getCustomPurchaseItems(self.__ctx.getModdedOutfitsInfo(), SEASONS_ORDER)
                    or any(v for k, v in g_config.outfitCache.get(nation, {}).get(vehicle, {}).iteritems() if k != 'style')):
                self.__ctx.installStyleItemsToModifiedOutfits(True)
                return
            message = makeHtmlString('html_templates:lobby/customization/dialog', 'decal', {
                'value': g_config.i18n['flashCol_propertySheet_edit_message']})
            DialogsInterface.showDialog(PMConfirmationDialogMeta(
                _APPLY_TO_OTHER_SEASONS_DIALOG, messageCtx={
                    'message': message, 'icon': RES_ICONS.MAPS_ICONS_LIBRARY_ICON_ALERT_90X84}),
                self.__ctx.installStyleItemsToModifiedOutfits)
        else:
            super(CustomizationPropertiesSheet, self).onActionBtnClick(actionType, actionData)

    def __makeRenderersVOs(self):
        # noinspection PyUnresolvedReferences
        renderers = super(CustomizationPropertiesSheet, self)._CustomizationPropertiesSheet__makeRenderersVOs()
        if not self.__ctx.isBuy and self._slotID == GUI_ITEM_TYPE.STYLE:
            renderers.insert(0, self.__makeEditRendererVO())
        return renderers

    def __makeEditRendererVO(self):
        nation, vehicle = g_currentVehicle.item.descriptor.name.split(':')
        enabled = not bool(self._currentStyle.modelsSet)
        return {
            'iconSrc': RES_ICONS.MAPS_ICONS_CUSTOMIZATION_PROPERTY_SHEET_IDLE_ICON_OFFSET_02_NORMAL,
            'iconHoverSrc': RES_ICONS.MAPS_ICONS_CUSTOMIZATION_PROPERTY_SHEET_IDLE_ICON_OFFSET_02_HOVER,
            'iconDisableSrc': RES_ICONS.MAPS_ICONS_CUSTOMIZATION_PROPERTY_SHEET_DISABLE_ICON_OFFSET_02_DISABLED,
            'actionBtnLabel': g_config.i18n['flash_propertySheet_edit_action'],
            'actionType': CA.CUSTOMIZATION_SHEET_ACTION_EDIT,
            'rendererLnk': CA.CUSTOMIZATION_SHEET_BTN_RENDERER_UI,
            'animatedTransition': True,
            'disableTooltip': g_config.i18n['flashCol_propertySheet_edit_disabled'],
            'notifyText': makeHtmlString('html_templates:lobby/customization/notify', 'decal', {
                'value': g_config.i18n['flashCol_propertySheet_edit_notify']}),
            'needNotify': enabled and (
                    bool(getCustomPurchaseItems(self.__ctx.getModdedOutfitsInfo(), SEASONS_ORDER))
                    or any(v for k, v in g_config.outfitCache.get(nation, {}).get(vehicle, {}).iteritems() if k != 'style')),
            'enabled': enabled}


@overrideMethod(WGPropertiesSheet, '__new__')
def new(base, cls, *a, **kw):
    if not g_config.data['enabled']:
        return base(cls, *a, **kw)
    return base(CustomizationPropertiesSheet, *a, **kw)
