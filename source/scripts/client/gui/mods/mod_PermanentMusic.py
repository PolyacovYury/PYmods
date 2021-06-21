from gui.Scaleform.daapi.view.battle.shared.drone_music_player import _TimeRemainedCondition, _Severity


def new_init(self, criticalValue, severity=_Severity.MEDIUM):
    return old_init(self, (
        900
        if not isinstance(criticalValue, tuple) and criticalValue else
        (900, criticalValue[1])
        if isinstance(criticalValue, tuple) and criticalValue[0] else
        criticalValue
    ), severity)


old_init = _TimeRemainedCondition.__init__
_TimeRemainedCondition.__init__ = new_init
print 'PermanentMusic v.1.0.0 by Polyacov_Yury: initialised.'
