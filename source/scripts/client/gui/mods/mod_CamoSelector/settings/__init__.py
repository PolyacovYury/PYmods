import cm_handler
from gui.Scaleform.framework import ScopeTemplates, ViewSettings, ViewTypes, g_entitiesFactories
from .anchor_properties import CamoAnchorProperties
from .main_view import CamoSelectorMainView
from .settings import CamoSelectorUI
from .shared import POPOVER_ALIAS

__all__ = ['CamoSelectorUI', 'CamoSelectorMainView']

# noinspection PyArgumentList
g_entitiesFactories.initSettings((
    ViewSettings('CamoSelectorUI', CamoSelectorUI, 'CamoSelector.swf', ViewTypes.WINDOW, None,
                 ScopeTemplates.GLOBAL_SCOPE, False),
    ViewSettings(POPOVER_ALIAS, CamoAnchorProperties, None, ViewTypes.COMPONENT, None, ScopeTemplates.DEFAULT_SCOPE),
    ViewSettings('CamoSelectorMainView', CamoSelectorMainView, 'customizationMainView.swf',
                 ViewTypes.LOBBY_SUB, None, ScopeTemplates.LOBBY_SUB_SCOPE),))
