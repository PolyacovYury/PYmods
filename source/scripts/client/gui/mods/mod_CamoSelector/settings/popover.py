from frameworks.wulf import WindowLayer
from gui.Scaleform.daapi.view.lobby.customization.popovers.editable_style_popover import EditableStylePopover as \
    WGStylePopover
from gui.Scaleform.framework import GroupedViewSettings, ScopeTemplates, g_entitiesFactories
from gui.shared import EVENT_BUS_SCOPE, g_eventBus
from gui.shared.events import ViewEventType
from gui.shared.personality import ServicesLocator as SL
from .. import g_config
from ..constants import VIEW_ALIAS


class EditableStylePopover(WGStylePopover):
    def __init__(self, ctx):
        print g_config.ID + ': inject successful'
        WGStylePopover.__init__(self, ctx)


popoverAlias = VIEW_ALIAS.CAMO_SELECTOR_KIT_POPOVER
g_entitiesFactories.addSettings(GroupedViewSettings(
    popoverAlias, EditableStylePopover, 'customizationEditedKitPopover.swf', WindowLayer.WINDOW, popoverAlias, popoverAlias,
    ScopeTemplates.DEFAULT_SCOPE))
g_eventBus.addListener(ViewEventType.LOAD_VIEW, lambda event: SL.appLoader.getApp().loadView(
    event.loadParams, event.ctx) if event.alias == popoverAlias else None, EVENT_BUS_SCOPE.LOBBY)
