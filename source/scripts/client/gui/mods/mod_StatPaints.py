__appID__ = '216060d4797ff99153c400922baeed6f'
import BigWorld
import json
import threading
import traceback
import urllib2
from ClientArena import ClientArena
from PYmodsCore import PYmodsConfigInterface, Analytics, overrideMethod
from functools import partial
from gui.Scaleform.battle_entry import BattleEntry
from gui.shared.gui_items import GUI_ITEM_TYPE
from vehicle_systems.CompoundAppearance import CompoundAppearance
from vehicle_systems.tankStructure import TankPartNames


class CustomPaint(object):
    def __init__(self, color, gloss, metallic):
        self.itemTypeID = GUI_ITEM_TYPE.PAINT
        self.__color = color[0] + (color[1] << 8) + (color[2] << 16) + (color[3] << 24)
        self.__gloss = gloss
        self.__metallic = metallic

    @property
    def color(self):
        return self.__color

    @property
    def gloss(self):
        return self.__gloss

    @property
    def metallic(self):
        return self.__metallic


class ConfigInterface(PYmodsConfigInterface):
    def __init__(self):
        self.paintItems = {}
        self.dossier = {}
        self.pending = set()
        self.attempts = {}
        self.failed = set()
        super(ConfigInterface, self).__init__()

    def init(self):
        self.ID = '%(mod_ID)s'
        self.version = '1.2.0 (%(file_compile_date)s)'
        self.data = {'enabled': True,
                     'ignorePresentPaints': True,
                     'removeCamouflages': True,
                     'paint_player_chassis': False,
                     'paint_player_hull': False,
                     'paint_player_turret': True,
                     'paint_player_gun': True,
                     'paint_ally_chassis': False,
                     'paint_ally_hull': False,
                     'paint_ally_turret': True,
                     'paint_ally_gun': True,
                     'paint_enemy_chassis': False,
                     'paint_enemy_hull': False,
                     'paint_enemy_turret': True,
                     'paint_enemy_gun': True,
                     'scale': {'2020': {'color': [133, 30, 27, 255], 'gloss': 0.509, 'metallic': 0.203},
                               '4185': {'color': [119, 84, 19, 255], 'gloss': 0.509, 'metallic': 0.23},
                               '6340': {'color': [118, 106, 20, 255], 'gloss': 0.509, 'metallic': 0.23},
                               '8525': {'color': [51, 111, 51, 255], 'gloss': 0.509, 'metallic': 0.23},
                               '9930': {'color': [51, 94, 94, 255], 'gloss': 0.509, 'metallic': 0.23},
                               '99999': {'color': [75, 47, 79, 255], 'gloss': 0.509, 'metallic': 0.23}}}
        self.i18n = {
            'UI_description': 'Statistics vehicle painter',
            'UI_setting_empty_text': '',
            'UI_setting_ignorePresentPaints_text': 'Ignore present paints',
            'UI_setting_ignorePresentPaints_tooltip':
                'Enable - vehicles will be coloured into stat colors ignoring present paints or styles.\n'
                'Disable - if a vehicle has a paint or style applied to it - it will be kept.',
            'UI_setting_colorScales_text': 'Color scales are edited via config file.',
            'UI_setting_removeCamouflages_text': 'Remove camouflages before repainting',
            'UI_setting_removeCamouflages_tooltip': 'Remove camouflages from the parts which will be recolored.',
            'UI_setting_parts_player_text': 'Painted player vehicle parts:',
            'UI_setting_parts_ally_text': 'Painted ally vehicle parts:',
            'UI_setting_parts_enemy_text': 'Painted enemy vehicle parts:',
            'UI_setting_paint_chassis_text': 'Chassis',
            'UI_setting_paint_hull_text': 'Hull',
            'UI_setting_paint_turret_text': 'Turret',
            'UI_setting_paint_gun_text': 'Gun'}
        super(ConfigInterface, self).init()

    def createPartsTemplate(self, team):
        return [self.tb.createLabel('parts_' + team)] + [
            dict(self.tb.createLabel('paint_' + part), **self.tb.createControl('paint_' + team + '_' + part, empty=True))
            for part in TankPartNames.ALL]

    def createTemplate(self):
        return {'modDisplayName': self.i18n['UI_description'],
                'enabled': self.data['enabled'],
                'column1': self.createPartsTemplate('player') + [
                    self.tb.createLabel('empty'),
                    self.tb.createControl('ignorePresentPaints'),
                    self.tb.createControl('removeCamouflages'),
                    self.tb.createLabel('colorScales'),
                ],
                'column2': [
                ] + self.createPartsTemplate('ally')
                  + self.createPartsTemplate('enemy')}

    def readCurrentSettings(self, quiet=True):
        super(ConfigInterface, self).readCurrentSettings(quiet)
        self.paintItems.clear()
        for value, data in self.data['scale'].iteritems():
            self.paintItems[int(value)] = CustomPaint(**data)

    def loadPlayerStats(self, databaseIDs):
        regions = {}
        for databaseID in databaseIDs:
            if databaseID not in self.pending and databaseID not in self.dossier and databaseID not in self.failed:
                if databaseID not in self.attempts:
                    self.attempts[databaseID] = 0
                self.attempts[databaseID] += 1
                if self.attempts[databaseID] > 100:
                    print self.ID + ': could not load info for databaseID', databaseID
                    self.failed.add(databaseID)
                    del self.attempts[databaseID]
                    continue
                self.pending.add(databaseID)
                regions.setdefault(userRegion(int(databaseID)), []).append(databaseID)
        results = []
        for region in regions:
            try:
                results.append(json.loads(urllib2.urlopen((
                    'https://api.worldoftanks.{'
                    'region}/wot/account/info/?application_id={aid}&fields=global_rating&account_id={id}').format(
                    region=region, id=','.join(regions[region]), aid=__appID__)).read()).get('data', None))
            except IOError:
                for databaseID in regions[region]:
                    self.pending.discard(databaseID)
        for result in results:
            if result:
                for databaseID in result:
                    dossier = result[databaseID]
                    if dossier is not None:
                        self.dossier[databaseID] = {'wgr': dossier['global_rating']}
                    self.pending.discard(databaseID)
        for databaseID in databaseIDs:
            self.pending.discard(databaseID)
        BigWorld.callback(0, partial(self.updatePaints, databaseIDs))

    def updatePaints(self, databaseIDs):
        player = BigWorld.player()
        if not hasattr(player, 'guiSessionProvider'):
            return BigWorld.callback(1, partial(self.updatePaints, databaseIDs))
        for databaseID in databaseIDs:
            vehicleID = player.guiSessionProvider.getCtx().getArenaDP().getVehIDByAccDBID(int(databaseID))
            vehicle = BigWorld.entity(vehicleID)
            if vehicle is not None and vehicle.appearance is not None:
                vehicle.appearance.setVehicle(vehicle)

    def thread(self, databaseIDs):
        try:
            databaseIDs = [x for x in databaseIDs if x not in self.pending and x not in self.failed]
            if databaseIDs:
                thread = threading.Thread(target=self.loadPlayerStats, args=(databaseIDs,))
                thread.setDaemon(True)
                thread.start()
        except StandardError:
            traceback.print_exc()

    def loadStats(self):
        arena = BigWorld.player().arena
        if arena is not None and arena.bonusType != 6:  # If it isn't tutorial battle
            self.thread([str(pl['accountDBID']) for pl in arena.vehicles.values()])

    def resetStats(self):
        self.attempts.clear()
        self.dossier.clear()
        self.pending.clear()


def userRegion(databaseID):
    if databaseID < 500000000:
        return 'ru'
    if databaseID < 1000000000:
        return 'eu'
    if databaseID < 2000000000:
        return 'na'
    return 'asia'


g_config = ConfigInterface()
analytics = Analytics(g_config.ID, g_config.version, 'UA-76792179-15')


@overrideMethod(ClientArena, '_ClientArena__onVehicleListUpdate')
def new__onVehicleListUpdate(base, self, *args, **kwargs):
    base(self, *args, **kwargs)
    g_config.loadStats()


@overrideMethod(BattleEntry, 'beforeDelete')
def new_BattleEntry_beforeDelete(base, self, *args, **kwargs):
    base(self, *args, **kwargs)
    g_config.resetStats()


@overrideMethod(CompoundAppearance, '_CompoundAppearance__applyVehicleOutfit')
def new_applyVehicleOutfit(base, self, *a, **kw):
    outfit = self.outfit
    vID = self.id
    vDesc = self.typeDescriptor
    if not vDesc or not g_config.data['enabled']:
        return base(self, *a, **kw)
    player = BigWorld.player()
    team = 'player' if vID == player.playerVehicleID else \
        'ally' if player.arena.vehicles[vID]['team'] == player.team else 'enemy'
    if not (any(g_config.data['paint_' + team + '_' + part] for part in TankPartNames.ALL)):
        return base(self, *a, **kw)
    accID = player.arena.vehicles[vID]['accountDBID']
    if not accID:
        return base(self, *a, **kw)
    strAccID = str(accID)
    if strAccID not in g_config.dossier:
        if strAccID not in g_config.pending:
            g_config.thread([strAccID])
        return base(self, *a, **kw)
    paintItem = None
    rating = g_config.dossier[strAccID]['wgr']
    for value in sorted(g_config.paintItems):
        if rating < value:
            paintItem = g_config.paintItems[value]
            break
    for fashionIdx, part in enumerate(TankPartNames.ALL):
        if not g_config.data['paint_' + team + '_' + part]:
            continue
        removeCamo = False
        container = outfit.getContainer(fashionIdx)
        paintSlot = container.slotFor(GUI_ITEM_TYPE.PAINT)
        camoSlot = container.slotFor(GUI_ITEM_TYPE.CAMOUFLAGE)
        if paintSlot is not None:
            for idx in xrange(paintSlot.capacity()):
                if g_config.data['ignorePresentPaints'] or paintSlot.getItem(idx) is None:
                    paintSlot.set(paintItem, idx)
                    removeCamo = True
        if camoSlot is not None and g_config.data['removeCamouflages'] and removeCamo:
            camoSlot.clear()
            fashion = self.fashions[fashionIdx]
            if fashion is None:
                continue
            fashion.removeCamouflage()
    self._CommonTankAppearance__outfit = outfit
    return base(self, *a, **kw)
