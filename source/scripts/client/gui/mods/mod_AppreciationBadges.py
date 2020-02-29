import ResMgr
import os
import traceback
from PYmodsCore import overrideMethod, remDups, Analytics
from gui.Scaleform.locale.RES_ICONS import RES_ICONS
from gui.Scaleform.settings import getBadgeIconPath, ICONS_SIZES
from gui.battle_control.arena_info.arena_vos import VehicleArenaInfoVO
from gui.battle_results.components.vehicles import BadgeBlock
from gui.doc_loaders.badges_loader import getSelectedByLayout, getAvailableBadges
from gui.prb_control.items import PlayerPrbInfo, PlayerUnitInfo
from gui.prb_control.items.prb_seqs import PrbListItem

badges_dir = ResMgr.openSection('gui/AppreciationBadges/')
if badges_dir is not None:
    g_badges = {}
    badges_data = getAvailableBadges()
    message = 'initialised.'
    badges = remDups(os.path.splitext(x)[0] for x in badges_dir.keys())
    for badge_name in badges:
        if '_' not in badge_name:
            print 'AppreciationBadges: wrong badge format:', badge_name
            continue
        strAccID, strBadgeID = badge_name.split('_', 1)
        try:
            accID = int(strAccID)
        except ValueError:
            print 'AppreciationBadges: unrecognized account ID:', strAccID
            continue
        try:
            badgeID = int(strBadgeID)
        except ValueError:
            print 'AppreciationBadges: wrong battle badge ID:', strBadgeID
            continue
        badges_data[badge_name] = dict(badges_data[badgeID], id=badge_name)
        g_badges[accID] = {'battle': badgeID, 'lobby': badge_name}


    @overrideMethod(PrbListItem, '__init__')
    @overrideMethod(PlayerPrbInfo, '__init__')
    @overrideMethod(PlayerUnitInfo, '__init__')
    def new_PPUI_init(base, self, *a, **kw):
        base(self, *a, **kw)
        dbID = getattr(self, 'creatorDbId', getattr(self, 'dbID', None))
        if dbID in g_badges:
            old_badges = self.badges._BadgesHelper__badgesRawData
            if old_badges:
                old_badges[0].append(g_badges[dbID]['lobby'])
            else:
                self.badges._BadgesHelper__badgesRawData = ([g_badges[dbID]['lobby']], [0])
            self.badges._BadgesHelper__prefixBadgeID = None


    @overrideMethod(VehicleArenaInfoVO, '__init__')
    def new_VAIVO_init(base, self, *a, **kw):
        base(self, *a, **kw)
        if self.player.accountDBID in g_badges:
            self.badges = (list(self.badges[0]) + [g_badges[self.player.accountDBID]['battle']], self.badges[1])
            self._VehicleArenaInfoVO__prefixBadge, self._VehicleArenaInfoVO__suffixBadge = getSelectedByLayout(self.badges[0])


    @overrideMethod(BadgeBlock, 'setRecord')
    def new_BadgeBlock_setRecord(base, self, result, reusable):
        base(self, result, reusable)
        if result.player.dbID in g_badges:
            self.icon = getBadgeIconPath(ICONS_SIZES.X24, g_badges[result.player.dbID]['lobby'])
            self.sizeContent = ICONS_SIZES.X24


    @overrideMethod(RES_ICONS, 'getBadgeIcon')
    def new_getBadgeIcon(base, _, size, value):
        if isinstance(value, int) or '_' not in value:
            return base(size, value)
        outcome = '../AppreciationBadges/{}.png'.format(value)
        normOutcome = os.path.normpath('gui/flash/' + outcome).replace(os.sep, '/')
        if ResMgr.openSection(normOutcome) is None:
            print 'WARNING: not found icon:', normOutcome
            traceback.print_stack()
            return ''
        return outcome
else:
    message = 'folder not found!'
    badges = []
print 'AppreciationBadges v.1.0.2 by Polyacov_Yury:', message
analytics = Analytics('AppreciationBadges', 'v.1.0.2', 'UA-76792179-17', badges)
