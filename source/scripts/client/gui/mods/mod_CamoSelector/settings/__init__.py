import cm_handler
from gui.Scaleform.framework import ScopeTemplates, ViewSettings, ViewTypes, g_entitiesFactories
from .main_view import CamoSelectorMainView
from .settings import CamoSelectorUI

__all__ = ['CamoSelectorUI', 'CamoSelectorMainView']

# noinspection PyArgumentList
g_entitiesFactories.initSettings((
    ViewSettings('CamoSelectorUI', CamoSelectorUI, 'CamoSelector.swf', ViewTypes.WINDOW, None,
                 ScopeTemplates.GLOBAL_SCOPE, False),
    ViewSettings('CamoSelectorMainView', CamoSelectorMainView, 'customizationMainView.swf',
                 ViewTypes.LOBBY_SUB, None, ScopeTemplates.LOBBY_SUB_SCOPE),))
