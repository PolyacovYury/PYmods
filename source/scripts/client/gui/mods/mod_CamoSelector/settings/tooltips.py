from PYmodsCore import overrideMethod
from gui.Scaleform.daapi.view.lobby.customization.tooltips import ElementTooltip


@overrideMethod(ElementTooltip, '_packItemBlocks')
def _packItemBlocks(base, self, statsConfig):
    ctx = self._ElementTooltip__ctx
    if ctx and not ctx.isBuy:
        statsConfig.buyPrice = False
        statsConfig.sellPrice = False
        statsConfig.inventoryCount = False
        statsConfig.showBonus = False
        if self._item.isProgressive:
            self._progressionLevel = self._progressionLevel or 1
    return base(self, statsConfig)


@overrideMethod(ElementTooltip, '_packIconBlock')
def _packIconBlock(base, self, isHistorical=False, isDim=False):
    data = base(self, isHistorical, isDim)
    if (data and 'data' in data and 'imagePath' in data['data']
            and '4278190335,4278255360,4294901760,4278190080' in data['data']['imagePath']):
        data['data']['imagePath'] = '../../' + data['data']['imagePath'].split('"', 2)[1]
    return data


@overrideMethod(ElementTooltip, '_packAppliedBlock')
@overrideMethod(ElementTooltip, '_packSpecialBlock')
def _packBlock(base, self):
    ctx = self._ElementTooltip__ctx
    return None if ctx and not ctx.isBuy else base(self)
