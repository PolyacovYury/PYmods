import BigWorld
from OpenModsCore import find_attr, overrideMethod
from account_helpers.settings_core.options import QuestsProgressViewType
from account_helpers.settings_core.settings_constants import QUESTS_PROGRESS
from constants import ARENA_PERIOD
from gui.Scaleform.daapi.view.battle.classic.full_stats import FullStatsComponent
from gui.Scaleform.daapi.view.battle.shared.battle_timers import PreBattleTimer
from gui.Scaleform.daapi.view.battle.shared.quest_progress_top_view import QuestProgressTopView
from gui.Scaleform.daapi.view.battle.shared.stats_exchange import BattleStatisticsDataController
from gui.Scaleform.genConsts.QUEST_PROGRESS_BASE import QUEST_PROGRESS_BASE
from gui.battle_control.controllers.quest_progress.quest_progress_ctrl import QuestProgressController
from personal_missions_constants import DISPLAY_TYPE


@overrideMethod(PreBattleTimer)
def as_addInfoS(base, self, linkage, data, *args, **kwargs):
    data['questName'] = ''
    for quest in self.sessionProvider.shared.questProgress.getInProgressQuests().itervalues():
        data['questName'] = '\n'.join(filter(None, (data['questName'], quest.getUserName())))
    return base(self, linkage, data, *args, **kwargs)


@overrideMethod(FullStatsComponent)
def as_updateProgressTrackingS(base, self, data, *args, **kwargs):
    questName = ''
    for quest in self.sessionProvider.shared.questProgress.getInProgressQuests().itervalues():
        questName = ' / '.join(filter(None, (questName, quest.getShortUserName())))
    for quest in data['trackingData']:
        quest['fullMissionName'] = questName
        quest['selected'] = True
        quest['eyeBtnVisible'] = find_attr(
            self, 'settingsCore').getSetting(QUESTS_PROGRESS.VIEW_TYPE) == QuestsProgressViewType.TYPE_STANDARD
    return base(self, data, *args, **kwargs)


@overrideMethod(BattleStatisticsDataController)
def as_setQuestsInfoS(base, self, data, setForce, *args, **kwargs):
    if 'bodyProgress' not in data:
        return base(self, data, setForce, *args, **kwargs)
    questProgress = self.sessionProvider.shared.questProgress
    getFormatter = find_attr(questProgress, 'getFormatter')
    data['questName'] = ''
    data['headerProgress'] = headerProgress = []
    data['bodyProgress'] = bodyProgress = []
    for quest in questProgress.getInProgressQuests().itervalues():
        formatter = getFormatter(quest)
        headerProgress.extend(formatter.headerFormat())
        bodyProgress.extend(formatter.bodyFormat())
    headerProgress.sort(key=lambda x: (
        x['progressType'] == DISPLAY_TYPE.NONE, x['orderType'] == QUEST_PROGRESS_BASE.ADD_ORDER_TYPE))
    bodyProgress.sort(key=lambda x: (
        x['initData']['orderType'] == QUEST_PROGRESS_BASE.ADD_ORDER_TYPE))
    headerProgress[2:] = []
    return base(self, data, setForce, *args, **kwargs)


@overrideMethod(BattleStatisticsDataController)
def as_updateQuestHeaderProgressS(base, self, headerProgress, *args, **kwargs):
    headerProgress = [] and headerProgress
    questProgress = self.sessionProvider.shared.questProgress
    getFormatter = find_attr(questProgress, 'getFormatter')
    for quest in questProgress.getInProgressQuests().itervalues():
        headerProgress.extend(getFormatter(quest).headerFormat())
    headerProgress.sort(key=lambda x: (
        x['progressType'] == DISPLAY_TYPE.NONE, x['orderType'] == QUEST_PROGRESS_BASE.ADD_ORDER_TYPE))
    return base(self, headerProgress[:2], *args, **kwargs)


@overrideMethod(QuestProgressController)
def updateQuestProgress(base, self, questID, info, *args, **kwargs):
    base(self, questID, info, *args, **kwargs)
    selectedQuest = self.getSelectedQuest()
    selectedQuestID = selectedQuest and selectedQuest.getGeneralQuestID()
    needHeaderResync = False
    for questID, storage in find_attr(self, 'storage').items():
        if questID == selectedQuestID:
            continue
        for headerProgress in storage.getHeaderProgresses().itervalues():
            if headerProgress.isChanged():
                needHeaderResync = True
                headerProgress.markAsVisited()
        for progressID, condProgress in storage.getChangedConditions().iteritems():
            condProgress.markAsVisited()
            self.onConditionProgressUpdate(progressID, condProgress.getProgress())
    if needHeaderResync:
        self.onHeaderProgressesUpdate()


@overrideMethod(QuestProgressController)
def updateTimerConditions(base, self, sendDiff=True, *args, **kwargs):
    base(self, sendDiff, *args, **kwargs)
    selectedQuest = self.getSelectedQuest()
    if self._period != ARENA_PERIOD.BATTLE or not selectedQuest:
        return
    selectedQuestID = selectedQuest.getGeneralQuestID()
    startTime = self._endTime - self._length
    timesGoneFromStart = BigWorld.serverTime() - startTime
    for questID, storage in find_attr(self, 'storage').items():
        if questID == selectedQuestID:
            continue
        timerConditions = storage.getTimerConditions()
        for progressID, condProgress in timerConditions.iteritems():
            secondsLeft = max(condProgress.getCountDown() - timesGoneFromStart, 0)
            isChanged = condProgress.setTimeLeft(secondsLeft)
            if isChanged and sendDiff:
                self.onConditionProgressUpdate(progressID, condProgress.getProgress())


@overrideMethod(QuestProgressTopView)
def as_setFlagVisibleS(base, self, isVisible, *args, **kwargs):
    return base(self, isVisible and False, *args, **kwargs)
