from PYmodsCore import overrideMethod
from gui import makeHtmlString
from gui.Scaleform.daapi.view.lobby.customization.customization_properties_sheet import \
    CustomizationPropertiesSheet as WGPropertiesSheet
from gui.Scaleform.genConsts.CUSTOMIZATION_ALIASES import CUSTOMIZATION_ALIASES as CA
from gui.customization.constants import CustomizationModes as C11nModes
from gui.impl import backport
from gui.impl.gen import R
from .shared import CSMode
from .. import g_config


class CustomizationPropertiesSheet(WGPropertiesSheet):
    def __makeStyleRenderersVOs(self):
        # noinspection PyUnresolvedReferences
        renderers = super(CustomizationPropertiesSheet, self)._CustomizationPropertiesSheet__makeStyleRenderersVOs()
        if not self.__ctx.isBuy:
            renderers[1:] = [self.__makeStyleEditRendererVO()]
        return renderers

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


@overrideMethod(WGPropertiesSheet, '__new__')
def new(base, cls, *a, **kw):
    if not g_config.data['enabled']:
        return base(cls, *a, **kw)
    return base(CustomizationPropertiesSheet, *a, **kw)
