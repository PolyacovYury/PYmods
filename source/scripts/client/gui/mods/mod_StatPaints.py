import datetime

import BigWorld
import PYmodsCore
import json
import threading
import urllib2
from ClientArena import ClientArena
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

    def loadPlayerStats(self, databaseID):
        if databaseID in self.dossiers:
            if (datetime.datetime.utcnow() - self.dossiers[databaseID]['time']).total_seconds() < 3600:
                return self.dossiers[databaseID]
        try:
            url = 'https://api.worldoftanks.{region}/wot/account/info/?application_id=demo&fields=global_rating&account_id' \
                  '={id}'.format(region=userRegion(int(databaseID)), id=databaseID)
            request = json.loads(urllib2.urlopen(url, timeout=1).read()).get('data', None)
        except IOError:
            request = None
        if request:
            for databaseID in request:
                dossier = request[databaseID]
                self.dossiers[databaseID] = {'time': datetime.datetime.utcnow(), 'wgr': dossier['global_rating']}
                vehicleID = BigWorld.player().guiSessionProvider.getCtx().getArenaDP().getVehIDByAccDBID(int(databaseID))
                vehicle = BigWorld.entity(vehicleID)
                if vehicle is not None:
                    vehicle.appearance.setVehicle(vehicle)

    def thread(self, databaseID):
        try:
            self.threadArray.append(threading.Thread(target=self.loadPlayerStats, args=(databaseID,)))
            self.threadArray[-1].start()
        except StandardError:
            pass

    def loadStats(self):
        arena = BigWorld.player().arena
        if arena is not None:
            if arena.bonusType != 6:  # If it isn't tutorial battle
                for dbID in [str(pl['accountDBID']) for pl in arena.vehicles.values()]:
                    self.thread(dbID)

    def resetStats(self):
        self.dossiers.clear()


def userRegion(databaseID):
    if databaseID < 500000000:
        return 'ru'
    if databaseID < 1000000000:
        return 'eu'
    if databaseID < 2000000000:
        return 'na'
    return 'asia'


g_config = ConfigInterface()


@PYmodsCore.overrideMethod(ClientArena, '_ClientArena__onVehicleListUpdate')
def new__onVehicleListUpdate(base, self, *args, **kwargs):
    base(self, *args, **kwargs)
    g_config.loadStats()


@PYmodsCore.overrideMethod(BattleEntry, 'beforeDelete')
def new_BattleEntry_beforeDelete(base, self, *args, **kwargs):
    base(self, *args, **kwargs)
    g_config.resetStats()


@PYmodsCore.overrideMethod(CompoundAppearance, '_CompoundAppearance__getVehicleOutfit')
def new__getVehicleOutfit(base, self, *args, **kwargs):
    outfit = base(self, *args, **kwargs)
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
        g_config.thread(accountID)
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
    return outfit
