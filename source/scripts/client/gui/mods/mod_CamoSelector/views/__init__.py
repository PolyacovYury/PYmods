from gui.Scaleform.framework import g_entitiesFactories, ViewSettings, ScopeTemplates, ViewTypes
from .main_view import CamoSelectorMainView
from .settings import CamoSelectorUI

# noinspection PyArgumentList
g_entitiesFactories.initSettings((
    ViewSettings('CamoSelectorUI', CamoSelectorUI, 'CamoSelector.swf', ViewTypes.WINDOW, None,
                 ScopeTemplates.GLOBAL_SCOPE, False),
    ViewSettings('CamoSelectorMainView', CamoSelectorMainView, 'customizationMainView.swf',
                 ViewTypes.LOBBY_SUB, None, ScopeTemplates.LOBBY_SUB_SCOPE),))
