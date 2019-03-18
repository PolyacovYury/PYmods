from Event import SafeEvent, EventManager

_manager = EventManager()


class _EventWrapper(object):
    def __init__(self):
        self.event = SafeEvent(_manager)

    def __call__(self, handler):
        self.event += handler
        return handler


class ModEvent(object):
    def __init__(self):
        self.before = _EventWrapper()
        self.after = _EventWrapper()

    def __call__(self, base, *args, **kwargs):
        self.before.event(*args, **kwargs)
        result = base(*args, **kwargs)
        self.after.event(*args, **kwargs)
        return result


from . import game, PlayerAvatar, LobbyView, LoginView


@game.fini.after
def fini(*_, **__):
    _manager.clear()
