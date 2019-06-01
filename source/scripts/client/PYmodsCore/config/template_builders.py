import copy


class CONTAINER(object):
    CheckBox = 'CheckBox'
    Label = 'Label'
    ColorChoice = 'ColorChoice'
    TextInput = 'TextInput'
    Dropdown = 'Dropdown'
    RadioButtonGroup = 'RadioButtonGroup'
    HotKey = 'HotKey'
    NumericStepper = 'NumericStepper'
    Slider = 'Slider'
    RangeSlider = 'RangeSlider'


class DummyTemplateBuilder(object):
    types = CONTAINER

    def __init__(self, i18n):
        self.i18n = i18n
        self._blockID = None

    def __call__(self, blockID):
        self._blockID = blockID
        return self

    def getValue(self, varName, value):
        return value

    @staticmethod
    def createEmpty():
        return {'type': 'Empty'}

    def getLabel(self, varName, ctx='setting'):
        return self.i18n['UI_%s_%s_text' % (ctx, varName)]

    def createTooltip(self, varName, ctx='setting'):
        return ('{HEADER}%s{/HEADER}{BODY}%s{/BODY}' % tuple(
            self.i18n['UI_%s_%s_%s' % (ctx, varName, strType)] for strType in ('text', 'tooltip'))) if self.i18n.get(
            'UI_%s_%s_tooltip' % (ctx, varName), '') else ''

    def createLabel(self, varName, ctx='setting'):
        if self._blockID is not None:
            varName = self._blockID + '_' + varName
        return {'type': 'Label', 'text': self.getLabel(varName, ctx), 'tooltip': self.createTooltip(varName, ctx)}

    def createControl(self, varName, contType=CONTAINER.CheckBox, width=200, empty=False, button=None, value=None):
        result = self.createLabel(varName) if not empty else {}  # contType: 'ColorChoice', 'TextInput'
        result.update({'type': contType, 'value': self.getValue(varName, value), 'varName': varName, 'width': width})
        if button is not None:
            result['button'] = button
        return result

    def createOptions(self, varName, options, contType=CONTAINER.Dropdown, width=200, empty=False, button=None, value=None):
        result = self.createControl(varName, contType, width, empty, button, value)  # contType: 'RadioButtonGroup'
        result['options'] = [{'label': x} for x in options]
        return result

    def createHotKey(self, varName, empty=False, value=None):
        result = self.createControl(varName, CONTAINER.HotKey, empty=empty, value=value)
        return result

    def _createNumeric(self, varName, contType, step, vMin=0, vMax=0, width=200, empty=False, button=None, value=None):
        result = self.createControl(varName, contType, width, empty, button, value)
        result.update({'minimum': vMin, 'maximum': vMax, 'snapInterval': step})
        return result

    def createStepper(self, varName, vMin, vMax, step, manual=False, width=200, empty=False, button=None, value=None):
        result = self._createNumeric(varName, CONTAINER.NumericStepper, step, vMin, vMax, width, empty, button, value)
        result['canManualInput'] = manual
        return result

    def createSlider(self, varName, vMin, vMax, step, formatStr='{{value}}', width=200, empty=False, button=None, value=None):
        result = self._createNumeric(varName, CONTAINER.Slider, step, vMin, vMax, width, empty, button, value)
        result['format'] = formatStr
        return result

    def createRangeSlider(
            self, varName, vMin, vMax, labelStep, divStep, step, minRange, width=200, empty=False, button=None, value=None):
        result = self._createNumeric(varName, CONTAINER.RangeSlider, step, vMin, vMax, width, empty, button, value)
        result.update({'divisionLabelStep': labelStep, 'divisionStep': divStep, 'minRangeDistance': minRange})
        return result


class TemplateBuilder(DummyTemplateBuilder):
    def __init__(self, data, i18n):
        super(TemplateBuilder, self).__init__(i18n)
        self.data = copy.deepcopy(data)

    def getValue(self, varName, value):
        return value if value is not None else (
            self.data[varName] if self._blockID is None else self.data[self._blockID][varName])
