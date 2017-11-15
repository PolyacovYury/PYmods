class DummyTemplateBuilder(object):
    def __init__(self, i18n):
        self.i18n = i18n

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
        return {'type': 'Label', 'text': self.getLabel(varName, ctx), 'tooltip': self.createTooltip(varName, ctx),
                'label': self.getLabel(varName, ctx)}  # because Stepper needs label instead of text

    def createControl(self, varName, value, contType='CheckBox', width=200, empty=False, button=None):
        result = self.createLabel(varName) if not empty else {}
        result.update({'type': contType, 'value': value, 'varName': varName, 'width': width})
        if button is not None:
            result['button'] = button
        return result

    def createOptions(self, varName, options, value, contType='Dropdown', width=200, empty=False, button=None):
        result = self.createControl(varName, value, contType, width, empty, button)
        result.update({'width': width, 'itemRenderer': 'DropDownListItemRendererSound',
                       'options': [{'label': x} for x in options]})
        return result

    def createHotKey(self, varName, value, defaultValue, empty=False):
        result = self.createControl(varName, value, 'HotKey', empty=empty)
        result['defaultValue'] = defaultValue
        return result

    def _createNumeric(self, varName, contType, value, vMin=0, vMax=0, width=200, empty=False, button=None):
        result = self.createControl(varName, value, contType, width, empty, button)
        result.update({'minimum': vMin, 'maximum': vMax})
        return result

    def createStepper(self, varName, vMin, vMax, step, value, manual=False, width=200, empty=False, button=None):
        result = self._createNumeric(varName, 'NumericStepper', value, vMin, vMax, width, empty, button)
        result.update({'stepSize': step, 'canManualInput': manual})
        return result

    def createSlider(self, varName, vMin, vMax, step, value, formatStr='{{value}}', width=200, empty=False, button=None):
        result = self._createNumeric(varName, 'Slider', value, vMin, vMax, width, empty, button)
        result.update({'snapInterval': step, 'format': formatStr})
        return result

    def createRangeSlider(self, varName, vMin, vMax, labelStep, divStep, step, minRange, value, width=200, empty=False,
                          button=None):
        result = self._createNumeric(varName, 'RangeSlider', value, vMin, vMax, width, empty, button)
        result.update(
            {'snapInterval': step, 'divisionLabelStep': labelStep, 'divisionStep': divStep, 'minRangeDistance': minRange})
        return result


class TemplateBuilder(object):
    def __init__(self, data, i18n, defaultKeys):
        self.dummy = DummyTemplateBuilder(i18n)
        self.data = data
        self.defaultKeys = defaultKeys

    def createEmpty(self):
        return self.dummy.createEmpty()

    def getLabel(self, varName, ctx='setting'):
        return self.dummy.getLabel(varName, ctx)

    def createLabel(self, varName, ctx='setting'):
        return self.dummy.createLabel(varName, ctx)

    def createTooltip(self, varName, ctx='setting'):
        return self.dummy.createTooltip(varName, ctx)

    def createControl(self, varName, contType='CheckBox', width=200, empty=False, button=None):
        return self.dummy.createControl(varName, self.data[varName], contType, width, empty, button)

    def createOptions(self, varName, options, contType='Dropdown', width=200, empty=False, button=None):
        return self.dummy.createOptions(varName, options, self.data[varName], contType, width, empty, button)

    def createHotKey(self, varName, empty=False):
        return self.dummy.createHotKey(varName, self.data[varName], self.defaultKeys[varName], empty)

    def _createNumeric(self, varName, contType, vMin=0, vMax=0, width=200, empty=False, button=None):
        return self.dummy._createNumeric(varName, contType, self.data[varName], vMin, vMax, width, empty, button)

    def createStepper(self, varName, vMin, vMax, step, manual=False, width=200, empty=False, button=None):
        return self.dummy.createStepper(varName, vMin, vMax, step, self.data[varName], manual, width, empty, button)

    def createSlider(self, varName, vMin, vMax, step, formatStr='{{value}}', width=200, empty=False, button=None):
        return self.dummy.createSlider(varName, vMin, vMax, step, self.data[varName], formatStr, width, empty, button)

    def createRangeSlider(self, varName, vMin, vMax, labelStep, divStep, step, minRange, width=200, empty=False,
                          button=None):
        return self.dummy.createRangeSlider(varName, vMin, vMax, labelStep, divStep, step, minRange, self.data[varName],
                                            width, empty, button)


# noinspection PyMethodOverriding
class DummyBlockTemplateBuilder(DummyTemplateBuilder):
    def __init__(self, i18n):
        super(DummyBlockTemplateBuilder, self).__init__(i18n)
        self.dummy = DummyTemplateBuilder(i18n)

    def createEmpty(self):
        return self.dummy.createEmpty()

    def createLabel(self, varName, blockID, ctx='setting'):
        return self.dummy.createLabel('_'.join((blockID, varName)), ctx)

    def createControl(self, blockID, varName, value, contType='CheckBox', width=200, empty=False, button=None):
        result = self.dummy.createControl(varName, value, contType, width, True, button)
        result.update(self.createLabel(blockID, varName) if not empty else {})
        return result

    def createOptions(self, blockID, varName, options, value, contType='Dropdown', width=200, empty=False, button=None):
        result = self.dummy.createOptions(varName, options, value, contType, width, True, button)
        result.update(self.createLabel(blockID, varName) if not empty else {})
        return result

    def createHotKey(self, blockID, varName, value, defaultValue, empty=False):
        result = self.dummy.createHotKey(varName, value, defaultValue, True)
        result.update(self.createLabel(blockID, varName) if not empty else {})
        return result

    def _createNumeric(self, blockID, varName, contType, value, vMin=0, vMax=0, width=200, empty=False, button=None):
        result = self.dummy._createNumeric(varName, contType, value, vMin, vMax, width, True, button)
        result.update(self.createLabel(blockID, varName) if not empty else {})
        return result

    def createStepper(self, blockID, varName, vMin, vMax, step, value, manual=False, width=200, empty=False, button=None):
        result = self.dummy.createStepper(varName, vMin, vMax, step, value, manual, width, True, button)
        result.update(self.createLabel(blockID, varName) if not empty else {})
        return result

    def createSlider(self, blockID, varName, vMin, vMax, step, value, formatStr='{{value}}', width=200, empty=False,
                     button=None):
        result = self.dummy.createSlider(varName, vMin, vMax, step, value, formatStr, width, True, button)
        result.update(self.createLabel(blockID, varName) if not empty else {})
        return result

    def createRangeSlider(self, blockID, varName, vMin, vMax, labelStep, divStep, step, minRange, value, width=200,
                          empty=False, button=None):
        result = self.dummy.createRangeSlider(
            varName, vMin, vMax, labelStep, divStep, step, minRange, value, width, True, button)
        result.update(self.createLabel(blockID, varName) if not empty else {})
        return result


# noinspection PyMethodOverriding
class BlockTemplateBuilder(object):
    def __init__(self, data, i18n, defaultKeys):
        self.dummy = DummyBlockTemplateBuilder(i18n)
        self.data = data
        self.defaultKeys = defaultKeys

    def createEmpty(self):
        return self.dummy.createEmpty()

    def createControl(self, blockID, varName, contType='CheckBox', width=200, empty=False, button=None):
        return self.dummy.createControl(blockID, varName, self.data[blockID][varName], contType, width, empty, button)

    def createOptions(self, blockID, varName, options, contType='Dropdown', width=200, empty=False, button=None):
        return self.dummy.createOptions(
            blockID, varName, options, self.data[blockID][varName], contType, width, empty, button)

    def createHotKey(self, blockID, varName, empty=False):
        return self.dummy.createHotKey(varName, self.data[blockID][varName], self.defaultKeys[varName], empty)

    def _createNumeric(self, blockID, varName, contType, vMin=0, vMax=0, width=200, empty=False, button=None):
        return self.dummy._createNumeric(
            blockID, varName, contType, self.data[blockID][varName], vMin, vMax, width, empty, button)

    def createStepper(self, blockID, varName, vMin, vMax, step, manual=False, width=200, empty=False, button=None):
        return self.dummy.createStepper(
            blockID, varName, vMin, vMax, step, self.data[blockID][varName], manual, width, empty, button)

    def createSlider(self, blockID, varName, vMin, vMax, step, formatStr='{{value}}', width=200, empty=False,
                     button=None):
        return self.dummy.createSlider(
            blockID, varName, vMin, vMax, step, self.data[blockID][varName], formatStr, width, empty, button)

    def createRangeSlider(self, blockID, varName, vMin, vMax, labelStep, divStep, step, minRange, width=200,
                          empty=False, button=None):
        return self.dummy.createRangeSlider(
            blockID, varName, vMin, vMax, labelStep, divStep, step, minRange, self.data[blockID][varName], width, empty,
            button)
