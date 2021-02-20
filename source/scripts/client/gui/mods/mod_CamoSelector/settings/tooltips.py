from PYmodsCore import overrideMethod
from gui.Scaleform.daapi.view.lobby.customization.tooltips import ElementTooltip as WGTooltip
from .. import g_config


class ElementTooltip(WGTooltip):
    def _packItemBlocks(self, statsConfig):
        if self.__ctx and not self.__ctx.isBuy:
            statsConfig.buyPrice = False
            statsConfig.sellPrice = False
            statsConfig.inventoryCount = False
            statsConfig.showBonus = False
            if self._item.isProgressive:
                self._progressionLevel = self._progressionLevel or 1
        return super(ElementTooltip, self)._packItemBlocks(statsConfig)

    def _packIconBlock(self, isHistorical=False, isDim=False):
        data = super(ElementTooltip, self)._packIconBlock(isHistorical, isDim)
        if (data and 'data' in data and 'imagePath' in data['data']
                and '4278190335,4278255360,4294901760,4278190080' in data['data']['imagePath']):
            data['data']['imagePath'] = '../../' + data['data']['imagePath'].split('"', 2)[1]
        return data

    def _packAppliedBlock(self):
        return None if self.__ctx and not self.__ctx.isBuy else super(ElementTooltip, self)._packAppliedBlock()

    def _packSpecialBlock(self):
        return None if self.__ctx and not self.__ctx.isBuy else super(ElementTooltip, self)._packSpecialBlock()


@overrideMethod(WGTooltip, '__new__')
def new(base, cls, *a, **kw):
    if not g_config.data['enabled']:
        return base(cls, *a, **kw)
    return base(ElementTooltip, *a, **kw)

