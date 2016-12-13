import cProfile

profile = cProfile.Profile()
profile.enable()


def fini():
    profile.disable()
    profile.dump_stats('./LampLights.prof')
