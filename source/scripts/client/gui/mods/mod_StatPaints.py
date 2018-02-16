import BigWorld
import PYmodsCore
import json
import threading
import urllib2
from ClientArena import ClientArena
from functools import partial
from gui.Scaleform.battle_entry import BattleEntry
from gui.shared.gui_items import GUI_ITEM_TYPE
from gui.shared.gui_items.customization.c11n_items import Paint
from items.vehicles import g_cache
from vehicle_systems.CompoundAppearance import CompoundAppearance
from vehicle_systems.tankStructure import TankPartNames

try:
    import gui.mods.mod_camoselector  # camouflage removal should work even with CamoSelector, so it has to be imported first
except ImportError:
    pass


class ConfigInterface(PYmodsCore.PYmodsConfigInterface):
    def __init__(self):
        self.dossiers = {}
        self.pendingIDs = set()
        self.threadArray = []
        super(ConfigInterface, self).__init__()

    def init(self):
        self.ID = '%(mod_ID)s'
        self.version = '1.0.0 (%(file_compile_date)s)'
        self.data = {'enabled': True,
                     'ignorePresentPaints': False,
                     'removeCamouflages': True,
                     'paint_chassis': False,
                     'paint_hull': False,
                     'paint_turret': True,
                     'paint_gun': True,
                     'scale': {'2020': 264, '4185': 225, '6340': 203, '8525': 224, '9930': 204, '99999': 200}}
        self.i18n = {
            'UI_description': 'Statistics vehicle painter',
            'UI_setting_ignorePresentPaints_text': 'Ignore present paints',
            'UI_setting_ignorePresentPaints_tooltip':
                'Enable - vehicles will be coloured into stat colors ignoring present paints or styles.\n'
                'Disable - if a vehicle has a paint or style applied to it - it will be kept.',
            'UI_setting_colorScales_text': 'Color scales are edited via config file.',
            'UI_setting_removeCamouflages_text': 'Remove camouflages before repainting',
            'UI_setting_removeCamouflages_tooltip': 'Remove camouflages from the parts which will be recolored.',
            'UI_setting_parts_text': 'These vehicle parts will be painted:',
            'UI_setting_paint_chassis_text': 'Chassis',
            'UI_setting_paint_hull_text': 'Hulls',
            'UI_setting_paint_turret_text': 'Turrets',
            'UI_setting_paint_gun_text': 'Guns'}
        super(ConfigInterface, self).init()

    def createTemplate(self):
        return {'modDisplayName': self.i18n['UI_description'],
                'settingsVersion': sum(int(x) * (10 ** i) for i, x in enumerate(reversed(self.version.split(' ')[0].split(
                    '.')))),
                'enabled': self.data['enabled'],
                'column1': [
                    self.tb.createControl('ignorePresentPaints'),
                    self.tb.createControl('removeCamouflages'),
                    self.tb.createLabel('colorScales')
                ],
                'column2': [
                    self.tb.createLabel('parts'),
                    self.tb.createControl('paint_chassis'),
                    self.tb.createControl('paint_hull'),
                    self.tb.createControl('paint_turret'),
                    self.tb.createControl('paint_gun')
                ]}

    def loadPlayerStats(self, databaseIDs):
        regions = {}
        for databaseID in databaseIDs:
            if databaseID not in self.pendingIDs and databaseID not in self.dossiers:
                self.pendingIDs.add(databaseID)
                regions.setdefault(userRegion(int(databaseID)), []).append(databaseID)
        results = []
        for region in regions:
            try:
                results.append(json.loads(urllib2.urlopen((
                    'https://api.worldoftanks.{'
                    'region}/wot/account/info/?application_id=demo&fields=global_rating&account_id={id}').format(
                    region=region, id=','.join(regions[region]))).read()).get('data', None))
            except IOError:
                for databaseID in regions[region]:
                    self.pendingIDs.discard(databaseID)
        for result in results:
            if result:
                for databaseID in result:
                    dossier = result[databaseID]
                    self.dossiers[databaseID] = {'wgr': dossier['global_rating']}
                    self.pendingIDs.discard(databaseID)
        for databaseID in databaseIDs:
            self.pendingIDs.discard(databaseID)
        BigWorld.callback(0, partial(self.updatePaints, databaseIDs))

    def updatePaints(self, databaseIDs):
        for databaseID in databaseIDs:
            vehicleID = BigWorld.player().guiSessionProvider.getCtx().getArenaDP().getVehIDByAccDBID(int(databaseID))
            vehicle = BigWorld.entity(vehicleID)
            if vehicle is not None and vehicle.appearance is not None:
                vehicle.appearance.setVehicle(vehicle)

    def thread(self, databaseIDs):
        try:
            self.threadArray.append(threading.Thread(target=self.loadPlayerStats, args=(databaseIDs,)))
            self.threadArray[-1].start()
        except StandardError:
            pass

    def loadStats(self):
        arena = BigWorld.player().arena
        if arena is not None and arena.bonusType != 6:  # If it isn't tutorial battle
            self.thread([str(pl['accountDBID']) for pl in arena.vehicles.values()])

    def resetStats(self):
        self.threadArray[:] = []
        self.dossiers.clear()
        self.pendingIDs.clear()


def userRegion(databaseID):
    if databaseID < 500000000:
        return 'ru'
    if databaseID < 1000000000:
        return 'eu'
    if databaseID < 2000000000:
        return 'na'
    return 'asia'


g_config = ConfigInterface()
statistic_mod = PYmodsCore.Analytics(g_config.ID, g_config.version, 'UA-76792179-15')


@PYmodsCore.overrideMethod(ClientArena, '_ClientArena__onVehicleListUpdate')
def new__onVehicleListUpdate(base, self, *args, **kwargs):
    base(self, *args, **kwargs)
    g_config.loadStats()


@PYmodsCore.overrideMethod(BattleEntry, 'beforeDelete')
def new_BattleEntry_beforeDelete(base, self, *args, **kwargs):
    base(self, *args, **kwargs)
    g_config.resetStats()


@PYmodsCore.overrideMethod(CompoundAppearance, '_CompoundAppearance__prepareOutfit')
def new_prepareOutfit(base, self, *args, **kwargs):
    base(self, *args, **kwargs)
    outfit = self._CompoundAppearance__outfit
    vehicle = self._CompoundAppearance__vehicle
    fashions = self._CompoundAppearance__fashions
    if not vehicle:
        return outfit
    paintItems = {}
    paints = g_cache.customization20().paints
    for paintID in g_config.data['scale'].itervalues():
        paintItem = Paint(paints[paintID].compactDescr)
        if paintItem.descriptor.filter and not paintItem.descriptor.filter.matchVehicleType(vehicle.typeDescriptor.type):
            return outfit
        paintItems[paintID] = paintItem
    accountID = str(BigWorld.player().arena.vehicles[vehicle.id]['accountDBID'])
    if accountID not in g_config.dossiers:
        if accountID not in g_config.pendingIDs:
            g_config.thread([accountID])
        return outfit
    paintID = None
    rating = g_config.dossiers[accountID]['wgr']
    for value in sorted(int(x) for x in g_config.data['scale']):
        if rating < value:
            paintID = g_config.data['scale'][str(value)]
            break
    for fashionIdx, descId in enumerate(TankPartNames.ALL):
        if not g_config.data['paint_%s' % descId]:
            continue
        removeCamo = False
        container = outfit.getContainer(fashionIdx)
        paintSlot = container.slotFor(GUI_ITEM_TYPE.PAINT)
        camoSlot = container.slotFor(GUI_ITEM_TYPE.CAMOUFLAGE)
        if paintSlot is not None:
            for idx in xrange(paintSlot.capacity()):
                if g_config.data['ignorePresentPaints'] or paintSlot.getItem(idx) is None:
                    paintSlot.set(paintItems[paintID], idx)
                    removeCamo = True
        if camoSlot is not None:
            if g_config.data['removeCamouflages'] and removeCamo:
                camoSlot.clear()
                fashion = fashions[fashionIdx]
                if fashion is None:
                    continue
                fashion.removeCamouflage()
    self._CompoundAppearance__outfit = outfit
