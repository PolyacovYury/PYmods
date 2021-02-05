from gui.Scaleform.daapi.view.lobby.customization.context.editable_style_mode import EditableStyleMode as WGEditableMode


class EditableStyleMode(WGEditableMode):
    def __init__(self, ctx, baseMode):
        super(EditableStyleMode, self).__init__(ctx)
        self._baseMode = baseMode
