""" XFW Library (c) www.modxvm.com 2013-2017 """
# forked by Polyacov_Yury
import traceback
from functools import partial

__all__ = ['registerEvent', 'overrideMethod', 'overrideClassMethod', 'overrideStaticMethod']


class EventHook(object):
    def __init__(self):
        self.__handlers = []

    def __iadd__(self, handler):
        self.__handlers.append(handler)
        return self

    def __isub__(self, handler):
        if handler in self.__handlers:
            self.__handlers.remove(handler)
        return self

    def fire(self, *args, **kwargs):
        for handler in self.__handlers:
            handler(*args, **kwargs)

    # noinspection PyMethodFirstArgAssignment
    def clearObjectHandlers(self, inObject):
        for theHandler in self.__handlers:
            if theHandler.im_self == inObject:
                self -= theHandler


def _RegisterEvent(handler, cls, method, prepend=False):
    evt = '__event_%i_%s' % ((1 if prepend else 0), method)
    if hasattr(cls, evt):
        e = getattr(cls, evt)
    else:
        newm = '__orig_%i_%s' % ((1 if prepend else 0), method)
        setattr(cls, evt, EventHook())
        setattr(cls, newm, getattr(cls, method))
        e = getattr(cls, evt)
        m = getattr(cls, newm)
        setattr(cls, method, lambda *a, **k: __event_handler(prepend, e, m, *a, **k))
    e += handler


def __event_handler(prepend, e, m, *a, **k):
    try:
        if prepend:
            e.fire(*a, **k)
            r = m(*a, **k)
        else:
            r = m(*a, **k)
            e.fire(*a, **k)
        return r
    except StandardError:
        traceback.print_exc()


def _override(cls, method, newm):
    orig = getattr(cls, method)
    if type(orig) is not property:
        setattr(cls, method, newm)
    else:
        setattr(cls, method, property(newm))


def _OverrideMethod(handler, cls, method, decorator=None):
    orig = getattr(cls, method)
    newm = lambda *a, **k: handler(orig, *a, **k)
    if decorator is not None:
        newm = decorator(newm)
    _override(cls, method, newm)


def _hook_decorator(func):
    def decorator1(*a, **k):
        def decorator2(handler):
            func(handler, *a, **k)

        return decorator2

    return decorator1


registerEvent = _hook_decorator(_RegisterEvent)
overrideMethod = _hook_decorator(_OverrideMethod)
overrideStaticMethod = _hook_decorator(partial(_OverrideMethod, decorator=staticmethod))
overrideClassMethod = _hook_decorator(partial(_OverrideMethod, decorator=classmethod))
