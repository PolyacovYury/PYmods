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
        self._final = _EventWrapper()

    def __call__(self, base, *args, **kwargs):
        self.before.event(*args, **kwargs)
        result = base(*args, **kwargs)
        self.after.event(*args, **kwargs)
        self._final.event(*args, **kwargs)
        return result


from . import game, PlayerAvatar, LobbyView, LoginView  # noqa: E402


@game.fini._final
def fini(*_, **__):
    _manager.clear()
