from vehicle_systems.CompoundAppearance import CompoundAppearance


def new_activate(self):
    old_activate(self)
    self.compoundModel.isHighPriorityReflection = False


old_activate = CompoundAppearance.activate
CompoundAppearance.activate = new_activate
print 'VehicleModelTransparencyFix v.1.0.0 by Polyacov_Yury: initialised.'
