from functools import partial

__all__ = ['doOverrideMethod', 'doOverrideClassMethod', 'doOverrideStaticMethod', 'overrideMethod', 'overrideClassMethod',
           'overrideStaticMethod']


def doOverrideMethod(cls, method, handler, decorator=None):
    orig = getattr(cls, method)
    newm = lambda *a, **k: handler(orig, *a, **k)
    if decorator is not None:
        newm = decorator(newm)
    setattr(cls, method, newm)


doOverrideStaticMethod = partial(doOverrideMethod, decorator=staticmethod)
doOverrideClassMethod = partial(doOverrideMethod, decorator=classmethod)
overrideMethod = partial(partial, doOverrideMethod, decorator=None)
overrideStaticMethod = partial(partial, doOverrideMethod, decorator=staticmethod)
overrideClassMethod = partial(partial, doOverrideMethod, decorator=classmethod)
