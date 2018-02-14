from config import g_config
from gui.Scaleform.framework import ScopeTemplates, ViewSettings, ViewTypes, g_entitiesFactories
from . import anchor_properties, cm_handler, season_buttons_component
from .main_view import CamoSelectorMainView

__all__ = ['CamoSelectorMainView']

# noinspection PyArgumentList
g_entitiesFactories.addSettings(ViewSettings('CamoSelectorMainView', CamoSelectorMainView, 'customizationMainView.swf',
                                ViewTypes.LOBBY_SUB, None, ScopeTemplates.LOBBY_SUB_SCOPE))
