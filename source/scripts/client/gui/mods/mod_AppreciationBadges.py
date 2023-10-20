import ResMgr
import os
import traceback
from OpenModsCore import overrideMethod, remDups, Analytics
from gui.Scaleform.locale.RES_ICONS import RES_ICONS
from gui.battle_control.arena_info.arena_vos import VehicleArenaInfoVO
from gui.battle_results.reusable.avatars import AvatarsInfo
from gui.doc_loaders.badges_loader import getSelectedByLayout, getAvailableBadges
from gui.prb_control.items import PlayerPrbInfo, PlayerUnitInfo
from gui.prb_control.items.prb_seqs import PrbListItem
from gui.shared.gui_items.badge import Badge, BadgeLayouts

badges_dir = ResMgr.openSection('gui/AppreciationBadges/')
if badges_dir is None:
    message = 'folder not found!'
    badges = []
else:
    g_badges = {}
    badges_data = getAvailableBadges()
    message = 'initialised.'
    badges = remDups(os.path.splitext(x)[0] for x in badges_dir.keys())
    for badge_name in badges:
        if not badge_name.startswith('a_badge_'):
            print 'AppreciationBadges: wrong badge format:', badge_name
            continue
        _, strAccID = badge_name.rsplit('_', 1)
        try:
            accID = int(strAccID)
        except ValueError:
            print 'AppreciationBadges: incorrect account ID:', strAccID
            continue
        badges_data[badge_name] = {
            'id': badge_name, 'name': badge_name, 'weight': -1.0, 'type': 0, 'layout': BadgeLayouts.PREFIX}
        g_badges[accID] = badge_name


    @overrideMethod(PrbListItem, '__init__')
    @overrideMethod(PlayerPrbInfo, '__init__')
    @overrideMethod(PlayerUnitInfo, '__init__')
    def new_PPUI_init(base, self, *a, **kw):
        base(self, *a, **kw)
        dbID = getattr(self, 'creatorDbId', getattr(self, 'dbID', None))
        if dbID in g_badges:
            old_badges = self.badges._BadgesHelper__badgesRawData
            if old_badges:
                old_badges[0].append(g_badges[dbID])
            else:
                self.badges._BadgesHelper__badgesRawData = ([g_badges[dbID]], [0])
            self.badges._BadgesHelper__prefixBadgeID = None


    @overrideMethod(VehicleArenaInfoVO, '__init__')
    def new_VAIVO_init(base, self, *a, **kw):
        base(self, *a, **kw)
        if self.player.accountDBID in g_badges:
            self.badges = (list(self.badges[0]) + [g_badges[self.player.accountDBID]], self.badges[1])
            self._VehicleArenaInfoVO__prefixBadge, self._VehicleArenaInfoVO__suffixBadge = getSelectedByLayout(self.badges[0])


    @overrideMethod(AvatarsInfo, 'getAvatarInfo')
    def new_AI_getAvatarInfo(base, self, dbID, *args, **kwargs):
        result = base(self, dbID, *args, **kwargs)
        if dbID in g_badges:
            result._AvatarInfo__badge = g_badges[dbID]
        return result


    @overrideMethod(Badge, 'getBadgeVO')
    def new_getBadgeVO(base, self, size, extraData=None, shortIconName=False, *args, **kwargs):
        if self.getIconPostfix().startswith('a_badge_'):
            shortIconName = False
            if extraData is not None and 'isAtlasSource' in extraData:
                extraData['isAtlasSource'] = False
        return base(self, size, extraData, shortIconName, *args, **kwargs)


    @overrideMethod(RES_ICONS, 'getBadgeIcon')
    def new_getBadgeIcon(base, _, size, value, *args, **kwargs):
        if isinstance(value, int) or not value.startswith('a_badge_'):
            return base(size, value, *args, **kwargs)
        outcome = '../AppreciationBadges/%s.png' % value
        normOutcome = os.path.normpath('gui/flash/' + outcome).replace(os.sep, '/')
        if ResMgr.openSection(normOutcome) is None:
            print 'WARNING: not found icon:', normOutcome
            traceback.print_stack()
            return ''
        return outcome
print 'AppreciationBadges v.1.0.4 by Polyacov_Yury:', message
analytics = Analytics('AppreciationBadges', 'v.1.0.4', 'UA-76792179-17', badges)
