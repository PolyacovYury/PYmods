import anchor_properties
import cm_handler
import season_buttons_component
from gui.Scaleform.framework import ScopeTemplates, ViewSettings, ViewTypes, g_entitiesFactories
from .main_view import CamoSelectorMainView

__all__ = ['CamoSelectorMainView']

# noinspection PyArgumentList
g_entitiesFactories.addSettings(ViewSettings('CamoSelectorMainView', CamoSelectorMainView, 'customizationMainView.swf',
                                             ViewTypes.LOBBY_SUB, None, ScopeTemplates.LOBBY_SUB_SCOPE))
