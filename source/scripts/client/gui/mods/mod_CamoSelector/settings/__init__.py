from PYmodsCore import overrideMethod
from gui.Scaleform.daapi.settings.views import VIEW_ALIAS
from gui.Scaleform.framework import EntitiesFactories
from .. import g_config
from . import bottom_panel, carousel, cm_handlers, context, main_view, properties_sheet, shared


# views = {VIEW_ALIAS.CUSTOMIZATION_BOTTOM_PANEL: bottom_panel.CustomizationBottomPanel,
#          VIEW_ALIAS.LOBBY_CUSTOMIZATION: main_view.MainView,
#          VIEW_ALIAS.CUSTOMIZATION_PROPERTIES_SHEET: properties_sheet.CustomizationPropertiesSheet}
backups = {}


# @overrideMethod(EntitiesFactories, 'addSettings')
# def addSettings(base, self, settings):
#     alias = settings.alias
#     if g_config.data['enabled'] and alias in views:
#         backups[alias] = settings
#         settings = settings.replaceSettings({'clazz': views[alias]})
#     return base(self, settings)
