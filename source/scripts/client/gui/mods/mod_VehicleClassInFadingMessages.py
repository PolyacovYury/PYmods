from gui.Scaleform.daapi.view.battle.shared.messages.fading_messages import FadingMessages


def new_formatEntities(self, args, extra=None):
    old_formatEntities(self, args, extra)
    if extra is None:
        extra = ()
    battleCtx = self.sessionProvider.getCtx()
    isAlly = battleCtx.isAlly
    getVehicleClass = lambda vehID: battleCtx.getVehicleInfo(vehID).vehicleType.classTag
    for argName, vID in extra:
        if argName in ('attacker', 'target', 'entity'):
            arg = args.get(argName)
            if arg:
                colour = 'green' if isAlly(vID) else 'red'
                args[argName] = arg.replace(
                    '(', "(<img src='img://gui/maps/icons/vehicleTypes/%s/%s.png' width='17' height='21' vspace='-5'/>" % (
                        colour, getVehicleClass(vID)))


old_formatEntities = FadingMessages._FadingMessages__formatEntitiesEx
FadingMessages._FadingMessages__formatEntitiesEx = new_formatEntities
print 'VehicleClassInFadingMessages v.1.0.0 by Polyacov_Yury: initialised.'
