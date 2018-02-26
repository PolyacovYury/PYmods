import ResMgr
import os
from gui.Scaleform.locale.RES_ICONS import RES_ICONS
from PYmodsCore import overrideMethod, overrideClassMethod, overrideStaticMethod, remDups, Analytics
from gui.battle_control.arena_info.arena_vos import VehicleArenaInfoVO
from gui.battle_results.components import style
from gui.battle_results.components.vehicles import RegularVehicleStatsBlock
from gui.prb_control.invites import PrbInviteWrapper
from gui.prb_control.items import PlayerPrbInfo, PlayerUnitInfo
from gui.prb_control.items.prb_seqs import PrbListItem

badges_dir = ResMgr.openSection('gui/AppreciationBadges/')
if badges_dir is not None:
    g_badges = {}
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
        g_badges[accID] = {'battle': badgeID, 'lobby': badge_name}


    def addLobbyBadge(dbID, badgesList):
        if dbID in g_badges:
            badgesList.append(g_badges[dbID]['lobby'])


    @overrideMethod(PrbListItem, '__init__')
    def new_PLI_init(base, self, *a, **kw):
        base(self, *a, **kw)
        addLobbyBadge(self.creatorDbId, self.badges._BadgesHelper__badges)


    @overrideStaticMethod(PrbInviteWrapper, '__new__')
    def new_PIW_new(base, *a, **kw):
        result = base(*a, **kw)
        addLobbyBadge(result.creatorDBID, result.creatorBadges._BadgesHelper__badges)
        return result


    @overrideMethod(PlayerPrbInfo, '__init__')
    def new_PPI_init(base, self, *a, **kw):
        base(self, *a, **kw)
        addLobbyBadge(self.dbID, self.badges._BadgesHelper__badges)


    @overrideMethod(PlayerUnitInfo, '__init__')
    def new_PUI_init(base, self, *a, **kw):
        base(self, *a, **kw)
        addLobbyBadge(self.dbID, self.badges._BadgesHelper__badges)


    @overrideMethod(VehicleArenaInfoVO, '__init__')
    def new_VAIVO_init(base, self, *a, **kw):
        base(self, *a, **kw)
        if self.player.accountDBID in g_badges:
            self.ranked.badges += (g_badges[self.player.accountDBID]['battle'],)


    @overrideMethod(RegularVehicleStatsBlock, 'setRecord')
    def new_RVSB_setRecord(base, self, result, reusable):
        base(self, result, reusable)
        if result.player.dbID in g_badges:
            self.badge = g_badges[result.player.dbID]['lobby']
            self.badgeIcon = style.makeBadgeIcon(self.badge)


    @overrideClassMethod(RES_ICONS, 'getBadgeIcon')
    def new_getBadgeIcon(base, _, size, value):
        if isinstance(value, int):
            return base(size, value)
        return getBadgePath(value)


    @overrideClassMethod(RES_ICONS, 'getBadgeIconBySize')
    def new_getBadgeIconBySize(base, _, w, h, value):
        if isinstance(value, int):
            return base(w, h, value)
        return getBadgePath(value)


    def getBadgePath(value):
        outcome = '../AppreciationBadges/{}.png'.format(value)
        normOutcome = os.path.normpath('gui/flash/' + outcome).replace(os.sep, '/')
        if ResMgr.openSection(normOutcome) is None:
            print 'WARNING: not found icon:', normOutcome
            return ''
        return outcome
else:
    message = 'folder not found!'
    badges = []
print 'AppreciationBadges v.1.0.0 by Polyacov_Yury:', message
analytics = Analytics('AppreciationBadges', 'v.1.0.0', 'UA-76792179-17', badges)
