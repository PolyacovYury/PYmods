from PYmodsCore import Analytics
from gui.Scaleform.daapi.view.battle.shared.damage_log_panel import DamageLogPanel

DamageLogPanel._updateTopLog, DamageLogPanel._updateBottomLog = DamageLogPanel._updateBottomLog, DamageLogPanel._updateTopLog
DamageLogPanel._addToTopLog, DamageLogPanel._addToBottomLog = DamageLogPanel._addToBottomLog, DamageLogPanel._addToTopLog
analytics = Analytics('%(mod_ID)s', 'v.1.0.0 (%(file_compile_date)s)', 'UA-76792179-19')
print '%(mod_ID)s v.1.0.0 (%(file_compile_date)s) by Polyacov_Yury (thx to Armagomen): initialised.'
